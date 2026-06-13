# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import logging
from typing import Dict

from .base import BaseLLMWrapper

logger = logging.getLogger(__name__)


def get_llm_wrapper(cfg: Dict) -> BaseLLMWrapper:
    """Factory: read config and return the correct LLM wrapper instance.

    Provider imports are deferred so installing only one SDK doesn't break the
    other wrapper's module import path.
    """

    llm_cfg = cfg.get("llm_settings", {})
    wrapper_name = llm_cfg.get("wrapper")

    if wrapper_name == "groq":
        from .models.groq_wrapper import GroqWrapper
        logger.info("Loading Groq wrapper")
        return GroqWrapper(cfg)

    if wrapper_name == "openai":
        from .models.openai_wrapper import OpenAIWrapper
        logger.info("Loading OpenAI wrapper")
        return OpenAIWrapper(cfg)

    raise ValueError(f"Unknown LLM wrapper in config: '{wrapper_name}'")
