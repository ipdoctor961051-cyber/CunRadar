"""Shared AI provider contracts and errors."""

from abc import ABC, abstractmethod


class AIProviderError(RuntimeError):
    """Base class for AI provider failures."""


class AIConfigurationError(AIProviderError):
    """Raised when AI configuration is missing or invalid."""


class AIRequestError(AIProviderError):
    """Raised when a configured provider cannot complete a request."""


class AIProvider(ABC):
    """Minimal interface implemented by every AI provider."""

    name: str
    model: str

    @abstractmethod
    def complete(self, messages: list[dict[str, str]], timeout: int) -> str:
        """Return the assistant text for an OpenAI-compatible message list."""
