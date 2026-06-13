# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import logging
import os
import random
import threading
from typing import Any, Dict, List, Optional, Type

from openai import OpenAI
from pydantic import BaseModel

from ..base import BaseLLMWrapper
from ..utils import CallConfig, parse_task_configs, to_strict_json_schema

logger = logging.getLogger(__name__)

# Module-level key pool
_shared_keys: List[str] = []
_shared_clients: Dict[str, OpenAI] = {}
_shared_index: int = 0
_shared_lock = threading.Lock()


def _register_keys(keys: List[str]) -> None:
    """Initialize the module-level key pool on first call; no-op afterwards."""

    global _shared_keys, _shared_clients, _shared_index
    with _shared_lock:
        if _shared_keys:
            return
        shuffled = keys[:]
        random.shuffle(shuffled)
        _shared_keys = shuffled
        _shared_clients = {k: OpenAI(api_key=k) for k in shuffled}
        _shared_index = 0
        logger.info(f"OpenAI key pool initialized with {len(_shared_keys)} key(s).")


def _next_key_rotation() -> List[str]:
    """Return all keys in round-robin order starting from the next position."""

    global _shared_index
    with _shared_lock:
        idx = _shared_index % len(_shared_keys)
        _shared_index += 1
    return _shared_keys[idx:] + _shared_keys[:idx]


class OpenAIWrapper(BaseLLMWrapper):
    """OpenAI client with strict json_schema structured outputs and key rotation."""

    def _init_provider(self, cfg: Dict) -> None:
        llm_cfg = cfg.get("llm_settings") or {}

        keys_str = os.environ.get("OPENAI_API_KEYS")
        if keys_str:
            api_keys = [k.strip() for k in keys_str.split(",") if k.strip()]
        else:
            single_key = os.environ.get("OPENAI_API_KEY") or llm_cfg.get("api_key")
            api_keys = [single_key] if single_key else []

        if not api_keys:
            raise ValueError(
                "OpenAI API keys not found. Set 'OPENAI_API_KEY' (single) or "
                "'OPENAI_API_KEYS' (comma-separated) env var."
            )

        _register_keys(api_keys)
        self._configs = parse_task_configs(llm_cfg)

    def _response_format(self, output_model: Optional[Type[BaseModel]]) -> Optional[Dict[str, Any]]:
        if not output_model:
            return None
        return {
            "type": "json_schema",
            "json_schema": {
                "name": output_model.__name__,
                "strict": True,
                "schema": to_strict_json_schema(output_model),
            },
        }

    def _call_api(self, messages: List[Dict[str, str]], call_config: CallConfig,
                  output_model: Optional[Type[BaseModel]],
                  prompt_cache_key: Optional[str] = None) -> str:
        kwargs: Dict[str, Any] = {
            "model": call_config.model,
            "messages": messages,
        }
        is_reasoning = call_config.reasoning_effort is not None
        if not is_reasoning:
            kwargs["temperature"] = call_config.temperature
            kwargs["top_p"] = call_config.top_p
        else:
            kwargs["reasoning_effort"] = call_config.reasoning_effort
        if call_config.max_completion_tokens is not None:
            kwargs["max_completion_tokens"] = call_config.max_completion_tokens
        if prompt_cache_key:
            kwargs["prompt_cache_key"] = prompt_cache_key
        response_format = self._response_format(output_model)
        if response_format:
            kwargs["response_format"] = response_format

        last_error: Optional[Exception] = None
        for api_key in _next_key_rotation():
            try:
                response = _shared_clients[api_key].chat.completions.create(**kwargs)
            except Exception as e:
                last_error = e
                logger.warning(f"OpenAI key {api_key[:8]}... failed: {e}")
                continue

            choice = response.choices[0]
            finish_reason = getattr(choice, "finish_reason", None)
            message = choice.message

            refusal = getattr(message, "refusal", None)
            if refusal:
                raise ValueError(f"OpenAI refused the request: {refusal}")

            if finish_reason == "length":
                raise ValueError(
                    "OpenAI output truncated by max_completion_tokens (finish_reason=length). "
                    "Increase max_completion_tokens or reduce batch size."
                )
            if finish_reason == "content_filter":
                raise ValueError("OpenAI content filter blocked the response.")

            return message.content or ""

        raise ValueError(f"All OpenAI API keys failed. Last error: {last_error}")
