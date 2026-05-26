from typing import Any

import httpx

from app.core.config import Settings, get_settings
from app.core.errors import ConfigurationError


class OpenRouterError(Exception):
    """Raised when OpenRouter returns an invalid or failed response."""


class OpenRouterClient:
    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str,
        timeout_seconds: int,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "OpenRouterClient":
        settings = settings or get_settings()
        api_key = (
            settings.openrouter_api_key.get_secret_value().strip()
            if settings.openrouter_api_key is not None
            else ""
        )
        if not api_key:
            raise ConfigurationError("OPENROUTER_API_KEY is not configured.")
        if not settings.openrouter_model or not settings.openrouter_model.strip():
            raise ConfigurationError("OPENROUTER_MODEL is not configured.")

        return cls(
            api_key=api_key,
            model=settings.openrouter_model.strip(),
            base_url=settings.openrouter_base_url,
            timeout_seconds=settings.openrouter_timeout_seconds,
        )

    def create_chat_completion(self, messages: list[dict[str, str]]) -> str:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise OpenRouterError(f"OpenRouter request failed: {exc}") from exc

        data = response.json()
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise OpenRouterError("OpenRouter response did not contain message content.") from exc

        if not isinstance(content, str) or not content.strip():
            raise OpenRouterError("OpenRouter response content was empty.")

        return content
