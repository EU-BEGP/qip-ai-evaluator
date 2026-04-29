# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import logging
from typing import Dict

from .base import BaseLLMWrapper
from .models.gemini_wrapper import GeminiWrapper
from .models.groq_wrapper import GroqWrapper
from .models.ollama_wrapper import OllamaWrapper

logger = logging.getLogger(__name__)


def get_llm_wrapper(cfg: Dict) -> BaseLLMWrapper:
    """Factory: read config and return the correct LLM wrapper instance."""
    llm_cfg = cfg.get("llm_settings", {})
    wrapper_name = llm_cfg.get("wrapper")

    if wrapper_name == "ollama":
        logger.info("Loading Ollama wrapper")
        return OllamaWrapper(cfg)

    elif wrapper_name == "gemini":
        logger.info("Loading Gemini wrapper")
        return GeminiWrapper(cfg)

    elif wrapper_name == "groq":
        logger.info("Loading Groq wrapper")
        return GroqWrapper(cfg)

    raise ValueError(f"Unknown LLM wrapper in config: '{wrapper_name}'")

__all__ = ["get_llm_wrapper", "BaseLLMWrapper"]
