# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import logging
import os
import random
import threading
from typing import Any, Dict, List, Optional, Type

from groq import Groq
from pydantic import BaseModel

from ..base import BaseLLMWrapper
from ..utils import CallConfig, parse_task_configs

logger = logging.getLogger(__name__)

# Module-level key pool
_shared_keys: List[str] = []
_shared_clients: Dict[str, Groq] = {}
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
        _shared_clients = {k: Groq(api_key=k) for k in shuffled}
        _shared_index = 0
        logger.info(f"Groq key pool initialized with {len(_shared_keys)} key(s).")


def _next_key_rotation() -> List[str]:
    """Return all keys in round-robin order starting from the next position."""

    global _shared_index
    with _shared_lock:
        idx = _shared_index % len(_shared_keys)
        _shared_index += 1
    return _shared_keys[idx:] + _shared_keys[:idx]


class GroqWrapper(BaseLLMWrapper):
    """Groq client with multi-key round-robin pool and JSON object mode."""

    def _init_provider(self, cfg: Dict) -> None:
        llm_cfg = cfg.get("llm_settings") or {}

        keys_str = os.environ.get("GROQ_API_KEYS") or os.environ.get("API_KEYS")
        if keys_str:
            api_keys = [k.strip() for k in keys_str.split(",") if k.strip()]
        else:
            single_key = os.environ.get("GROQ_API_KEY") or llm_cfg.get("api_key")
            api_keys = [single_key] if single_key else []

        if not api_keys:
            raise ValueError(
                "Groq API keys not found. Set 'GROQ_API_KEY' (single), "
                "'GROQ_API_KEYS' (comma-separated), or legacy 'API_KEYS' env var."
            )

        _register_keys(api_keys)
        self._configs = parse_task_configs(llm_cfg)

    def _response_format(self, output_model: Optional[Type[BaseModel]]) -> Optional[Dict[str, Any]]:
        return {"type": "json_object"} if output_model else None

    def _call_api(self, messages: List[Dict[str, str]], call_config: CallConfig,
                  output_model: Optional[Type[BaseModel]],
                  prompt_cache_key: Optional[str] = None) -> str:
        del prompt_cache_key
        kwargs: Dict[str, Any] = {
            "model": call_config.model,
            "messages": messages,
            "temperature": call_config.temperature,
            "top_p": call_config.top_p,
        }
        if call_config.max_completion_tokens is not None:
            kwargs["max_tokens"] = call_config.max_completion_tokens
        if call_config.reasoning_effort is not None:
            kwargs["reasoning_effort"] = call_config.reasoning_effort
        response_format = self._response_format(output_model)
        if response_format:
            kwargs["response_format"] = response_format

        last_error: Optional[Exception] = None
        for api_key in _next_key_rotation():
            try:
                response = _shared_clients[api_key].chat.completions.create(**kwargs)
                return response.choices[0].message.content
            except Exception as e:
                last_error = e
                logger.warning(f"Groq key {api_key[:8]}... failed: {e}")
                continue

        raise ValueError(f"All Groq API keys failed. Last error: {last_error}")
