from __future__ import annotations

import json
import sys
import time
from dataclasses import replace
from pathlib import Path

from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import Settings
from app.services.llm_client import (
    GEMINI_FALLBACK_MODEL,
    GeminiLLMClient,
    LLMMessage,
    LLMProviderConfig,
)
from app.services.llm_feedback_service import LLMFeedbackService


def _provider_config(settings: Settings) -> LLMProviderConfig:
    return LLMProviderConfig.from_settings(settings)


def _smoke_messages() -> list[LLMMessage]:
    return [
        LLMMessage(
            role="system",
            content=(
                "Return exactly three short plain-text lines. "
                "Do not include markdown, JSON, explanations, or code fences."
            ),
        ),
        LLMMessage(
            role="user",
            content=(
                "Return these exact three lines with the same wording:\n"
                "Main cue: Keep the knees steady.\n"
                "Fix: Slow the descent and hold the knee line.\n"
                "Next session cue: Repeat the same tempo on the next set."
            ),
        ),
    ]


def _summary_messages() -> list[LLMMessage]:
    return [
        LLMMessage(
            role="system",
            content=(
                "Return exactly one plain-text sentence. "
                "Do not include markdown, JSON, explanations, or code fences."
            ),
        ),
        LLMMessage(
            role="user",
            content=(
                "Return exactly this sentence with no extra text: "
                "Your main focus is steadier knee tracking on the next set."
            ),
        ),
    ]


def _valid_item_text(response_text: str) -> bool:
    labels = LLMFeedbackService._extract_labeled_lines(
        LLMFeedbackService._normalize_llm_response_text(response_text)
    )
    return all(labels.get(key) for key in ("main_coaching_cue", "what_to_fix", "next_session_cue"))


def _valid_summary_text(response_text: str) -> bool:
    summary = LLMFeedbackService._validated_text(
        LLMFeedbackService._normalize_llm_response_text(response_text),
        max_length=700,
    )
    return bool(summary)


def main() -> int:
    load_dotenv(BACKEND_ROOT / ".env", override=False)
    settings = Settings()
    config = _provider_config(settings)
    client = GeminiLLMClient()
    messages = _smoke_messages()

    configured_model_ok = False
    fallback_model_ok = False
    success = False
    error: str | None = None
    started_at = time.perf_counter()

    try:
        response_text = client._generate_with_config(messages=messages, config=config)
        configured_model_ok = True
        success = _valid_item_text(response_text)
        if success:
            summary_response_text = client._generate_with_config(
                messages=_summary_messages(),
                config=config,
            )
            success = _valid_summary_text(summary_response_text)
    except Exception as exc:
        error = f"{exc.__class__.__name__}: {str(exc)[:240]}"
        fallback_config = replace(config, model=GEMINI_FALLBACK_MODEL)
        try:
            response_text = client._generate_with_config(
                messages=messages,
                config=fallback_config,
            )
            fallback_model_ok = True
            success = _valid_item_text(response_text)
            if success:
                summary_response_text = client._generate_with_config(
                    messages=_summary_messages(),
                    config=fallback_config,
                )
                success = _valid_summary_text(summary_response_text)
        except Exception as fallback_exc:
            error = f"{fallback_exc.__class__.__name__}: {str(fallback_exc)[:240]}"

    duration_ms = int((time.perf_counter() - started_at) * 1000)
    result = {
        "provider": config.provider,
        "model": config.model if configured_model_ok or not fallback_model_ok else GEMINI_FALLBACK_MODEL,
        "success": success,
        "duration_ms": duration_ms,
    }
    print(json.dumps(result, sort_keys=True))
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
