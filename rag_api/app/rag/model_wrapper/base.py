# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import replace
from typing import Any, Dict, List, Optional, Type, Union
from pydantic import BaseModel, ValidationError

from .utils import (
    CallConfig,
    MODE_TO_TASK,
    build_feedback_msg,
    resolve_output_model,
    sanitize_response,
    temp_for_attempt,
)

logger = logging.getLogger(__name__)


class BaseLLMWrapper(ABC):
    """Abstract base for any LLM. Subclasses implement three provider hooks."""

    MAX_VALIDATION_ATTEMPTS = 3

    def __init__(self, cfg: Dict):
        self.session_messages: List[Dict[str, str]] = []
        self._configs: Dict[str, CallConfig] = {}
        self._init_provider(cfg)
        if "default" not in self._configs:
            raise ValueError(
                f"{type(self).__name__}._init_provider must register at least a 'default' config in self._configs"
            )

    @abstractmethod
    def _init_provider(self, cfg: Dict) -> None:
        """Configure provider-specific state (client, keys) and populate
        self._configs with at least a 'default' entry."""

    @abstractmethod
    def _call_api(self, messages: List[Dict[str, str]], call_config: CallConfig,
                  output_model: Optional[Type[BaseModel]],
                  prompt_cache_key: Optional[str] = None) -> str:
        """Make the API call. Return raw text content from the response."""

    @abstractmethod
    def _response_format(self, output_model: Optional[Type[BaseModel]]) -> Optional[Dict[str, Any]]:
        """Provider-specific response_format dict, or None for free-form text."""

    def reset_session(self) -> None:
        self.session_messages = []

    def run_prompt(self, prompt: str, mode: Optional[str] = None,
                   task: Optional[str] = None, remember: bool = True,
                   prompt_cache_key: Optional[str] = None) -> Union[str, BaseModel]:
        """Send prompt to the LLM. mode selects structured output schema;
        task selects which per-task config to use (falls back to default derived from mode - MODE_TO_TASK). 
        prompt_cache_key is forwarded to providers that support prompt caching (e.g. OpenAI) for cache-hit routing."""

        output_model = resolve_output_model(mode)
        call_config = self._resolve_call_config(mode, task)
        messages = self._build_messages(prompt, output_model)

        if not output_model:
            text_result = self._call_api(messages, call_config, None, prompt_cache_key)
            if remember:
                self._remember(prompt, text_result)
            return text_result

        return self._call_with_retries(
            messages, output_model, mode, call_config, remember, prompt, prompt_cache_key
        )

    def _resolve_call_config(self, mode: Optional[str], task: Optional[str]) -> CallConfig:
        """Pick the call config for this invocation. Explicit `task` wins;
        else derive task from `mode` via MODE_TO_TASK; finally fall back to
        the 'default' config if the resolved task has no override."""

        resolved_task = task or MODE_TO_TASK.get(mode, "default")
        return self._configs.get(resolved_task, self._configs["default"])

    def _build_messages(self, prompt: str,
                        output_model: Optional[Type[BaseModel]]) -> List[Dict[str, str]]:
        """Copy session history + inject schema system message (if structured) + user prompt."""

        messages = [
            {"role": m["role"], "content": m["content"]} for m in self.session_messages
        ]
        if output_model:
            schema_json = json.dumps(output_model.model_json_schema(), indent=2)
            system_msg = (
                f"You are a helpful assistant. Output a JSON object strictly following this schema:\n"
                f"{schema_json}"
            )
            if messages and messages[0]["role"] == "system":
                messages[0]["content"] += f"\n\n{system_msg}"
            else:
                messages.insert(0, {"role": "system", "content": system_msg})

        messages.append({"role": "user", "content": prompt})
        return messages

    def _remember(self, prompt: str, text_result: str) -> None:
        self.session_messages.append({"role": "user", "content": prompt})
        self.session_messages.append({"role": "assistant", "content": text_result})

    def _call_with_retries(self, messages: List[Dict[str, str]],
                           output_model: Type[BaseModel], mode: Optional[str],
                           call_config: CallConfig, remember: bool,
                           prompt: str, prompt_cache_key: Optional[str] = None
                           ) -> Union[str, BaseModel]:
        """Call API with stratified temperature; on validation failure, append
        the bad response + targeted feedback to messages and retry."""

        last_error: Optional[Exception] = None
        text_result = ""

        for attempt in range(1, self.MAX_VALIDATION_ATTEMPTS + 1):
            attempt_config = replace(
                call_config,
                temperature=temp_for_attempt(call_config.temperature, attempt),
            )
            text_result = self._call_api(messages, attempt_config, output_model, prompt_cache_key)

            try:
                clean_text = sanitize_response(text_result)
                validated = output_model.model_validate_json(clean_text)
                if remember:
                    self._remember(prompt, text_result)
                if mode == "snapshot":
                    return validated.model_dump_json(indent=2)
                return validated
            except (ValidationError, json.JSONDecodeError) as e:
                last_error = e
                logger.warning(
                    f"Pydantic validation failed (mode={mode}) attempt "
                    f"{attempt}/{self.MAX_VALIDATION_ATTEMPTS}: {e}"
                )
                logger.debug(f"Raw LLM output: {text_result}")
                if attempt < self.MAX_VALIDATION_ATTEMPTS:
                    feedback = (
                        build_feedback_msg(e) if isinstance(e, ValidationError)
                        else "Your previous response was not valid JSON. Return a corrected JSON object matching the schema."
                    )
                    messages.append({"role": "assistant", "content": text_result})
                    messages.append({"role": "user", "content": feedback})

        logger.error(f"Pydantic validation failed all attempts (mode={mode}): {last_error}")
        raise ValueError(f"Invalid JSON (mode={mode}): {last_error}")
