from __future__ import annotations

import json
import logging
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Any, Protocol

import httpx

from app.core.config import Settings


GEMINI_PROVIDERS = frozenset({"gemini", "google_gemini"})
GEMINI_FALLBACK_MODEL = "gemini-2.5-flash"
logger = logging.getLogger("uvicorn.error")


def is_gemini_provider(provider: str | None) -> bool:
    return (provider or "").strip().lower() in GEMINI_PROVIDERS


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
    debug_response_shape: bool = False

    @classmethod
    def from_settings(cls, settings: Settings) -> "LLMProviderConfig":
        return cls(
            provider=settings.llm_provider,
            model=settings.llm_model,
            api_key=settings.gemini_api_key or settings.llm_api_key,
            base_url=settings.llm_base_url,
            timeout_seconds=settings.llm_timeout_seconds,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
            enhancement_enabled=llm_enhancement_enabled(settings),
            debug_response_shape=settings.llm_debug_response_shape,
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


class GeminiLLMClient:
    def generate_text(
        self,
        *,
        messages: list[LLMMessage],
        config: LLMProviderConfig,
    ) -> str:
        if not config.api_key:
            raise LLMClientError("Gemini API key is not configured.")

        try:
            return self._generate_with_config(messages=messages, config=config)
        except Exception as exc:
            if not self._should_try_fallback_model(exc=exc, config=config):
                raise LLMClientError(self._safe_failure_message(exc=exc, model=config.model)) from exc

            fallback_config = replace(config, model=GEMINI_FALLBACK_MODEL)
            logger.warning(
                "Gemini configured model failed; trying fallback model "
                "configured_model=%s fallback_model=%s exception_class=%s "
                "http_status=%s error_message=%s",
                config.model,
                fallback_config.model,
                exc.__class__.__name__,
                self._http_status(exc),
                self._http_error_message(exc),
            )

        try:
            return self._generate_with_config(messages=messages, config=fallback_config)
        except Exception as exc:
            raise LLMClientError(
                self._safe_failure_message(exc=exc, model=fallback_config.model)
            ) from exc

    def _generate_with_config(
        self,
        *,
        messages: list[LLMMessage],
        config: LLMProviderConfig,
    ) -> str:
        started_at = time.perf_counter()
        endpoint = self._generate_content_endpoint(config)
        payload = {
            "contents": self._contents(messages),
            "generationConfig": {
                "temperature": config.temperature,
                "maxOutputTokens": config.max_tokens,
                "responseMimeType": "text/plain",
            },
        }
        system_instruction = self._system_instruction(messages)
        if system_instruction:
            payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

        try:
            with httpx.Client(timeout=config.timeout_seconds) as client:
                response = client.post(endpoint, json=payload)
                response.raise_for_status()
                data = response.json()
        except Exception as exc:
            self._log_provider_error(exc=exc, model=config.model)
            raise

        try:
            content = self.extract_gemini_text(data, debug=config.debug_response_shape)
        except Exception as exc:
            self._log_provider_error(exc=exc, model=config.model)
            if isinstance(exc, LLMClientError):
                raise
            raise LLMClientError("Gemini provider response was malformed.") from exc
        duration_ms = int((time.perf_counter() - started_at) * 1000)
        logger.info(
            "Gemini provider request succeeded model=%s duration_ms=%s",
            config.model,
            duration_ms,
        )
        logger.info(
            "Gemini text extracted length=%s model=%s",
            len(content),
            config.model,
        )
        return content

    @classmethod
    def extract_gemini_text(cls, response: Any, *, debug: bool = False) -> str:
        texts: list[str] = []
        part_types: list[str] = []
        part_text_lengths: list[int] = []

        candidates = cls._get_candidates(response)
        if candidates:
            first_candidate = candidates[0]
            parts = cls._get_parts(first_candidate)
            for part in parts:
                part_types.append(cls._describe_part(part))
                text = cls._get_part_text(part)
                if text:
                    cleaned = text.strip()
                    if cleaned:
                        texts.append(cleaned)
                        part_text_lengths.append(len(cleaned))
            combined_text = "\n".join(texts)
            cls._debug_response_shape(
                response=response,
                candidate_count=len(candidates),
                part_count=len(parts),
                part_types=part_types,
                part_text_lengths=part_text_lengths,
                combined_text=combined_text,
                enabled=debug,
            )
            if combined_text:
                return combined_text
        else:
            cls._debug_response_shape(
                response=response,
                candidate_count=0,
                part_count=0,
                part_types=[],
                part_text_lengths=[],
                combined_text="",
                enabled=debug,
            )

        text_attr = cls._get_response_text_attr(response)
        if text_attr:
            combined_text = text_attr.strip()
            if combined_text:
                cls._debug_response_shape(
                    response=response,
                    candidate_count=0,
                    part_count=0,
                    part_types=[],
                    part_text_lengths=[len(combined_text)],
                    combined_text=combined_text,
                    enabled=debug,
                )
                return combined_text

        raise LLMClientError("Gemini provider response did not contain extractable text.")

    @classmethod
    def _get_candidates(cls, response: Any) -> list[Any]:
        candidates = cls._mapping_or_attr(response, "candidates")
        if isinstance(candidates, Sequence) and not isinstance(candidates, (str, bytes, bytearray)):
            return list(candidates)
        return []

    @classmethod
    def _get_parts(cls, candidate: Any) -> list[Any]:
        content = cls._mapping_or_attr(candidate, "content")
        parts = cls._mapping_or_attr(content, "parts")
        if isinstance(parts, Sequence) and not isinstance(parts, (str, bytes, bytearray)):
            return list(parts)
        return []

    @classmethod
    def _get_part_text(cls, part: Any) -> str | None:
        if cls._mapping_or_attr(part, "inline_data") is not None:
            return None
        text = cls._mapping_or_attr(part, "text")
        if isinstance(text, str):
            return text
        return None

    @staticmethod
    def _get_response_text_attr(response: Any) -> str | None:
        text = getattr(response, "text", None)
        if isinstance(text, str):
            return text
        if isinstance(response, Mapping):
            mapped = response.get("text")
            if isinstance(mapped, str):
                return mapped
        return None

    @staticmethod
    def _mapping_or_attr(value: Any, key: str) -> Any:
        if value is None:
            return None
        if isinstance(value, Mapping):
            return value.get(key)
        return getattr(value, key, None)

    @staticmethod
    def _describe_part(part: Any) -> str:
        if isinstance(part, Mapping):
            if "text" in part:
                return "dict:text"
            if "inline_data" in part:
                return "dict:inline_data"
            return f"dict:{','.join(sorted(str(key) for key in part.keys())[:4])}"
        return part.__class__.__name__

    @classmethod
    def _debug_response_shape(
        cls,
        *,
        response: Any,
        candidate_count: int,
        part_count: int,
        part_types: list[str],
        part_text_lengths: list[int],
        combined_text: str,
        enabled: bool,
    ) -> None:
        if not enabled:
            return
        logger.info(
            "Gemini response shape response_type=%s response_text_exists=%s "
            "candidates_count=%s content_parts_count=%s part_types=%s "
            "part_text_lengths=%s combined_text_length=%s combined_text_preview=%s",
            response.__class__.__name__,
            bool(cls._get_response_text_attr(response)),
            candidate_count,
            part_count,
            part_types,
            part_text_lengths,
            len(combined_text),
            cls._truncate(combined_text, limit=500),
        )

    @staticmethod
    def _generate_content_endpoint(config: LLMProviderConfig) -> str:
        base_url = (config.base_url or "https://generativelanguage.googleapis.com/v1beta").rstrip("/")
        return f"{base_url}/models/{config.model}:generateContent?key={config.api_key}"

    @staticmethod
    def _system_instruction(messages: list[LLMMessage]) -> str:
        return "\n".join(
            message.content.strip()
            for message in messages
            if message.role == "system" and message.content.strip()
        )

    @staticmethod
    def _contents(messages: list[LLMMessage]) -> list[dict[str, object]]:
        user_text = "\n\n".join(
            message.content.strip()
            for message in messages
            if message.role != "system" and message.content.strip()
        )
        if not user_text:
            user_text = "Return deterministic coaching feedback JSON from the supplied context."
        return [{"role": "user", "parts": [{"text": user_text}]}]

    @classmethod
    def _should_try_fallback_model(
        cls,
        *,
        exc: Exception,
        config: LLMProviderConfig,
    ) -> bool:
        if config.model == GEMINI_FALLBACK_MODEL:
            return False
        status_code = cls._http_status(exc)
        if status_code == 503:
            return True
        if status_code not in {400, 404}:
            return False
        message = (cls._http_error_message(exc) or "").lower()
        return any(
            token in message
            for token in (
                "model",
                "not found",
                "not supported",
                "unavailable",
                "does not exist",
            )
        )

    @classmethod
    def _safe_failure_message(cls, *, exc: Exception, model: str) -> str:
        status_code = cls._http_status(exc)
        message = cls._http_error_message(exc)
        if status_code is not None and message:
            return f"Gemini provider request failed for model {model} (HTTP {status_code}: {message})."
        if status_code is not None:
            return f"Gemini provider request failed for model {model} (HTTP {status_code})."
        return f"Gemini provider request failed for model {model} ({exc.__class__.__name__})."

    @classmethod
    def _log_provider_error(cls, *, exc: Exception, model: str) -> None:
        logger.warning(
            "Gemini provider request failed model=%s exception_class=%s "
            "http_status=%s error_message=%s",
            model,
            exc.__class__.__name__,
            cls._http_status(exc),
            cls._http_error_message(exc),
        )

    @staticmethod
    def _http_status(exc: Exception) -> int | None:
        if isinstance(exc, httpx.HTTPStatusError):
            return exc.response.status_code
        return None

    @classmethod
    def _http_error_message(cls, exc: Exception) -> str | None:
        if not isinstance(exc, httpx.HTTPStatusError):
            return None
        try:
            payload = exc.response.json()
        except ValueError:
            return cls._truncate(exc.response.text)
        message: object = None
        if isinstance(payload, dict):
            error = payload.get("error")
            if isinstance(error, dict):
                message = error.get("message")
            else:
                message = payload.get("message")
        if not isinstance(message, str):
            return None
        return cls._truncate(message)

    @staticmethod
    def _truncate(value: str, *, limit: int = 320) -> str:
        sanitized = " ".join(value.split())
        return sanitized[:limit]
