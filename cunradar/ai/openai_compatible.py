"""OpenAI-compatible HTTP provider implementation."""

import requests

from .base import AIProvider, AIRequestError


class OpenAICompatibleProvider(AIProvider):
    """Call an OpenAI-compatible chat completions endpoint."""

    def __init__(self, *, name: str, model: str, api_key: str, endpoint: str) -> None:
        self.name = name
        self.model = model
        self._api_key = api_key
        self._endpoint = endpoint

    def complete(self, messages: list[dict[str, str]], timeout: int) -> str:
        try:
            response = requests.post(
                self._endpoint,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 1024,
                },
                timeout=timeout,
            )
            response.raise_for_status()
            payload = response.json()
            content = payload["choices"][0]["message"]["content"]
        except requests.RequestException as exc:
            status = getattr(exc.response, "status_code", None)
            detail = f"HTTP {status}" if status is not None else exc.__class__.__name__
            raise AIRequestError(f"{self.name} request failed: {detail}") from exc
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise AIRequestError(f"{self.name} returned an invalid response") from exc

        if not isinstance(content, str) or not content.strip():
            raise AIRequestError(f"{self.name} returned empty content")
        return content.strip()
