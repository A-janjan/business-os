"""LLM provider abstraction.

A provider is anything that can turn a (system, user) prompt into a text
completion. The core app only depends on this interface; business logic never
touches a concrete provider.

- `OpenAICompatibleProvider`: any OpenAI-compatible chat-completions endpoint
  (OpenAI, Groq, Mistral, Ollama, vLLM, LM Studio, ...).
- `NotConfiguredProvider`: explicit, loud failure when no provider is set.

No fake responses are generated when no provider is configured.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx


class NotConfiguredError(RuntimeError):
    """Raised when an AI feature is used without a configured provider."""


class ProviderError(RuntimeError):
    pass


@dataclass
class LLMResult:
    text: str
    tokens_in: int = 0
    tokens_out: int = 0
    provider: str = ""
    model: str = ""
    raw: dict = field(default_factory=dict)


class LLMProvider(Protocol):
    name: str
    model: str

    @property
    def is_configured(self) -> bool: ...

    async def complete(
        self,
        system: str,
        user: str,
        *,
        temperature: float = 0.4,
        max_tokens: int = 4096,
        json_mode: bool = False,
    ) -> LLMResult: ...


class NotConfiguredProvider:
    name = "not-configured"
    model = ""

    @property
    def is_configured(self) -> bool:
        return False

    async def complete(self, system: str, user: str, **_kwargs) -> LLMResult:
        raise NotConfiguredError(
            "AI provider is not configured. Set AI_BASE_URL, AI_API_KEY and AI_MODEL in .env to enable AI features."
        )


class OpenAICompatibleProvider:
    name = "openai-compatible"

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout: float = 120.0,
        max_retries: int = 2,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries

    @property
    def is_configured(self) -> bool:
        return bool(self.base_url and self.model)

    def _endpoint(self) -> str:
        if self.base_url.endswith("/chat/completions"):
            return self.base_url
        return f"{self.base_url}/chat/completions"

    async def complete(
        self,
        system: str,
        user: str,
        *,
        temperature: float = 0.4,
        max_tokens: int = 4096,
        json_mode: bool = False,
    ) -> LLMResult:
        if not self.is_configured:
            raise NotConfiguredError("AI provider is not configured.")

        payload: dict[str, Any] = {
            "model": self.model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.post(self._endpoint(), json=payload, headers=headers)
                    resp.raise_for_status()
                    data = resp.json()
                    message = data.get("choices", [{}])[0].get("message", {}) or {}
                    text = message.get("content") or ""
                    usage = data.get("usage") or {}
                    return LLMResult(
                        text=str(text),
                        tokens_in=int(usage.get("prompt_tokens") or 0),
                        tokens_out=int(usage.get("completion_tokens") or 0),
                        provider=self.name,
                        model=self.model,
                        raw={"id": data.get("id"), "finish_reason": (data.get("choices") or [{}])[0].get("finish_reason")},
                    )
            except (httpx.HTTPError, ValueError, KeyError, json.JSONDecodeError) as exc:
                last_error = exc
                if attempt < self.max_retries:
                    await asyncio.sleep(min(2.0, 0.5 * (attempt + 1)))
                    continue
                break
        raise ProviderError(f"LLM request failed: {last_error}")


def get_provider() -> LLMProvider:
    """Build the configured provider from settings."""
    from ..config import get_settings

    settings = get_settings()
    if not settings.ai_enabled:
        return NotConfiguredProvider()
    if settings.ai_provider == "openai-compatible" and settings.is_ai_configured:
        return OpenAICompatibleProvider(
            base_url=settings.ai_base_url,
            api_key=settings.ai_api_key,
            model=settings.ai_model,
            timeout=settings.ai_timeout_seconds,
            max_retries=settings.ai_max_retries,
        )
    return NotConfiguredProvider()
