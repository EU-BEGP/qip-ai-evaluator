from abc import ABC, abstractmethod

class BaseLLMWrapper(ABC):
    """Abstract base class for any LLM."""

    @abstractmethod
    def run_prompt(self, prompt: str):
        """Send prompt to the LLM and return text response."""
        pass
