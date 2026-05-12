from __future__ import annotations

import logging
from dataclasses import replace

import httpx
import pytest

import app.services.llm_client as llm_client_module
from app.services.llm_client import (
    GEMINI_FALLBACK_MODEL,
    GeminiLLMClient,
    LLMClientError,
    LLMMessage,
    LLMProviderConfig,
)


def _config() -> LLMProviderConfig:
    return LLMProviderConfig(
        provider="gemini",
        model="gemini-2.5-flash",
        api_key="test-gemini-key",
        base_url=None,
        timeout_seconds=20.0,
        temperature=0.2,
        max_tokens=220,
        enhancement_enabled=True,
        debug_response_shape=False,
    )


class _TextOnlyResponse:
    def __init__(self, text: str) -> None:
        self.text = text


def test_gemini_client_extracts_text_from_response_text() -> None:
    response = _TextOnlyResponse('{"summary":"steady rep","grounding_fields_used":["deterministic_feedback"]}')

    text = GeminiLLMClient.extract_gemini_text(response)

    assert text.startswith('{"summary"')


def test_gemini_client_extracts_text_from_multi_part_dict_response() -> None:
    response = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {"text": "Here is the JSON requested:"},
                        {
                            "text": '{"main_coaching_cue":"Stay steady.","what_happened":"The rep drifted.","why_it_matters":"Stable reps repeat better.","what_to_fix":"Slow the descent.","next_session_cue":"Repeat the same tempo."}'
                        },
                        {"inline_data": {"mime_type": "application/octet-stream", "data": "ignored"}},
                    ]
                }
            }
        ]
    }

    text = GeminiLLMClient.extract_gemini_text(response)

    assert "Here is the JSON requested:" in text
    assert '"main_coaching_cue":"Stay steady."' in text


def test_gemini_client_extracts_text_from_object_candidate_parts() -> None:
    class Part:
        def __init__(self, *, text: str | None = None) -> None:
            self.text = text
            self.inline_data = None

    class Content:
        def __init__(self, parts) -> None:
            self.parts = parts

    class Candidate:
        def __init__(self, parts) -> None:
            self.content = Content(parts)

    class Response:
        def __init__(self) -> None:
            self.text = ""
            self.candidates = [
                Candidate(
                    [
                        Part(text="Here is the JSON requested:"),
                        Part(
                            text='{"summary":"Keep the next rep steady.","grounding_fields_used":["top_issue"]}'
                        ),
                    ]
                )
            ]

    text = GeminiLLMClient.extract_gemini_text(Response())

    assert text.startswith("Here is the JSON requested:")
    assert '"summary":"Keep the next rep steady."' in text


def test_gemini_client_debug_shape_logs_safe_preview(caplog) -> None:
    response = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {"text": "Here is the JSON requested:"},
                        {"text": '{"summary":"steady rep","grounding_fields_used":["top_issue"]}'},
                    ]
                }
            }
        ]
    }
    caplog.set_level(logging.INFO)

    GeminiLLMClient.extract_gemini_text(response, debug=True)

    assert "Gemini response shape" in caplog.text
    assert "candidates_count=1" in caplog.text
    assert "content_parts_count=2" in caplog.text
    assert "combined_text_length=" in caplog.text


def test_gemini_client_raises_controlled_error_when_text_missing() -> None:
    with pytest.raises(LLMClientError, match="did not contain extractable text"):
        GeminiLLMClient.extract_gemini_text({"candidates": [{"content": {"parts": [{"inline_data": {"mime_type": "image/png"}}]}}]})


def test_gemini_client_uses_generate_content_api(monkeypatch, caplog) -> None:
    calls: list[dict[str, object]] = []

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": "Main cue: Keep the knees stable.\nFix: Slow the next rep.\nNext session cue: Repeat the same tempo."
                                }
                            ]
                        }
                    }
                ]
            }

    class FakeClient:
        def __init__(self, *, timeout: float) -> None:
            self.timeout = timeout

        def __enter__(self) -> "FakeClient":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def post(self, url: str, json: dict[str, object]) -> FakeResponse:
            calls.append({"url": url, "json": json, "timeout": self.timeout})
            return FakeResponse()

    monkeypatch.setattr(llm_client_module.httpx, "Client", FakeClient)
    caplog.set_level(logging.INFO)

    result = GeminiLLMClient().generate_text(
        messages=[
            LLMMessage(role="system", content="System instruction."),
            LLMMessage(
                role="user",
                content='Context: {"deterministic_feedback": {"coaching_cue": "Keep knees stable."}}',
            ),
        ],
        config=_config(),
    )

    assert "Keep the knees stable" in result
    assert calls[0]["timeout"] == 20.0
    assert (
        calls[0]["url"]
        == "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=test-gemini-key"
    )
    payload = calls[0]["json"]
    assert payload["generationConfig"] == {
        "temperature": 0.2,
        "maxOutputTokens": 220,
        "responseMimeType": "text/plain",
    }
    assert payload["systemInstruction"] == {"parts": [{"text": "System instruction."}]}
    assert "pose_sequence" not in str(payload)
    assert "Gemini provider request succeeded model=gemini-2.5-flash" in caplog.text
    assert "test-gemini-key" not in caplog.text
    assert "Keep knees stable" not in caplog.text


def test_gemini_client_falls_back_to_25_flash_without_logging_key(
    monkeypatch,
    caplog,
) -> None:
    calls: list[dict[str, object]] = []

    class FakeResponse:
        def __init__(self, *, url: str, status_code: int, payload: dict[str, object]) -> None:
            self._response = httpx.Response(
                status_code=status_code,
                json=payload,
                request=httpx.Request("POST", url),
            )
            self._payload = payload

        def raise_for_status(self) -> None:
            self._response.raise_for_status()

        def json(self) -> dict[str, object]:
            return self._payload

    class FakeClient:
        def __init__(self, *, timeout: float) -> None:
            self.timeout = timeout

        def __enter__(self) -> "FakeClient":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def post(self, url: str, json: dict[str, object]) -> FakeResponse:
            calls.append({"url": url, "json": json})
            if "gemini-3-flash-preview" in url:
                return FakeResponse(
                    url=url,
                    status_code=404,
                    payload={
                        "error": {
                            "message": "Model gemini-3-flash-preview is not found for generateContent."
                        }
                    },
                )
            return FakeResponse(
                url=url,
                status_code=200,
                payload={
                    "candidates": [
                        {
                            "content": {
                                "parts": [
                                    {
                                        "text": "Main cue: Use one stable knee cue.\nFix: Slow the rep.\nNext session cue: Repeat the same shape."
                                    }
                                ]
                            }
                        }
                    ]
                },
            )

    monkeypatch.setattr(llm_client_module.httpx, "Client", FakeClient)
    caplog.set_level(logging.WARNING)

    result = GeminiLLMClient().generate_text(
        messages=[
            LLMMessage(role="system", content="System instruction."),
            LLMMessage(role="user", content="Compact context only."),
        ],
        config=replace(_config(), model="gemini-3-flash-preview"),
    )

    assert "stable knee cue" in result
    assert len(calls) == 2
    assert "gemini-3-flash-preview" in str(calls[0]["url"])
    assert GEMINI_FALLBACK_MODEL in str(calls[1]["url"])
    assert "http_status=404" in caplog.text
    assert "configured_model=gemini-3-flash-preview" in caplog.text
    assert "fallback_model=gemini-2.5-flash" in caplog.text
    assert "Model gemini-3-flash-preview is not found" in caplog.text
    assert "test-gemini-key" not in caplog.text
    assert "Compact context only" not in caplog.text
