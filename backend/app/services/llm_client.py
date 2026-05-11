from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import httpx

from app.core.config import Settings


LOCAL_LLM_PROVIDERS = frozenset(
    {
        "llama_cpp",
        "llama.cpp",
        "local_llama_cpp",
        "local",
        "qwen_gguf",
    }
)


def is_local_llm_provider(provider: str | None) -> bool:
    return (provider or "").strip().lower() in LOCAL_LLM_PROVIDERS


def llm_enhancement_enabled(settings: Settings) -> bool:
    return (
        settings.llm_enabled
        if settings.llm_enabled is not None
        else settings.llm_enable_enhancement
    )


@dataclass(frozen=True)
class LLMProviderConfig:
    provider: str
    model: str
    api_key: str | None
    base_url: str | None
    timeout_seconds: float
    temperature: float
    max_tokens: int
    enhancement_enabled: bool

    @classmethod
    def from_settings(cls, settings: Settings) -> "LLMProviderConfig":
        return cls(
            provider=settings.llm_provider,
            model=settings.llm_model,
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            timeout_seconds=settings.llm_timeout_seconds,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
            enhancement_enabled=llm_enhancement_enabled(settings),
        )


@dataclass(frozen=True)
class LLMMessage:
    role: str
    content: str


class LLMClientError(RuntimeError):
    pass


class LLMClient(Protocol):
    def generate_text(
        self,
        *,
        messages: list[LLMMessage],
        config: LLMProviderConfig,
    ) -> str:
        ...


class OpenAICompatibleLLMClient:
    def generate_text(
        self,
        *,
        messages: list[LLMMessage],
        config: LLMProviderConfig,
    ) -> str:
        endpoint = self._chat_completions_endpoint(config)
        headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": config.model,
            "messages": [
                {"role": message.role, "content": message.content}
                for message in messages
            ],
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
        }

        try:
            with httpx.Client(timeout=config.timeout_seconds) as client:
                response = client.post(endpoint, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
        except Exception as exc:
            raise LLMClientError("LLM provider request failed.") from exc

        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMClientError("LLM provider response was malformed.") from exc

        if not isinstance(content, str) or not content.strip():
            raise LLMClientError("LLM provider returned an empty response.")
        return content.strip()

    @staticmethod
    def _chat_completions_endpoint(config: LLMProviderConfig) -> str:
        base_url = (config.base_url or "https://api.openai.com/v1").rstrip("/")
        return f"{base_url}/chat/completions"
