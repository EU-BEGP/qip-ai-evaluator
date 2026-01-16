# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

from .base import BaseLLMWrapper
from .models.ollama_wrapper import OllamaWrapper
from .models.gemini_wrapper import GeminiWrapper
from .models.groq_wrapper import GroqWrapper
from typing import Dict

def get_llm_wrapper(cfg: Dict) -> BaseLLMWrapper:
    """
    Factory function to read the config and return the correct LLM wrapper instance.
    """
    llm_cfg = cfg.get("llm_settings", {})
    wrapper_name = llm_cfg.get("wrapper")

    if wrapper_name == "ollama":
        print("-> Loading Ollama Wrapper")
        return OllamaWrapper(cfg)
        
    elif wrapper_name == "gemini":
        print("-> Loading Gemini Wrapper")
        return GeminiWrapper(cfg)

    elif wrapper_name == "groq":
        print("-> Loading Groq Wrapper")
        return GroqWrapper(cfg)
        
    else:
        # Default or error
        raise ValueError(f"Unknown LLM wrapper specified in config: '{wrapper_name}'")

__all__ = ["get_llm_wrapper", "BaseLLMWrapper"]