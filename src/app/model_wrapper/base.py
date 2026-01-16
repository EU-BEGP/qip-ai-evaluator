# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

from abc import ABC, abstractmethod

class BaseLLMWrapper(ABC):
    """Abstract base class for any LLM."""

    @abstractmethod
    def run_prompt(self, prompt: str):
        """Send prompt to the LLM and return text response."""
        pass
