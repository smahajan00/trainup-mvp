from __future__ import annotations

import json
import os

import pytest

from app.core.config import Settings
from app.services.llm_client import GeminiLLMClient, LLMMessage, LLMProviderConfig
from app.services.llm_feedback_service import LLMFeedbackService


@pytest.mark.skipif(
    os.getenv("TRAINUP_RUN_GEMINI_SMOKE") != "1",
    reason="Set TRAINUP_RUN_GEMINI_SMOKE=1 to call Gemini API.",
)
def test_gemini_api_smoke_from_env() -> None:
    settings = Settings()
    config = LLMProviderConfig.from_settings(settings)
    if not config.api_key:
        pytest.skip("GEMINI_API_KEY is not configured.")

    response_text = GeminiLLMClient().generate_text(
        messages=[
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
                    "Return exactly these lines with the same wording:\n"
                    "Main cue: Keep the knees steady.\n"
                    "Fix: Slow the descent and hold the knee line.\n"
                    "Next session cue: Repeat the same tempo on the next set."
                ),
            ),
        ],
        config=config,
    )

    labels = LLMFeedbackService._extract_labeled_lines(
        LLMFeedbackService._normalize_llm_response_text(response_text)
    )
    assert labels["main_coaching_cue"]
    assert labels["what_to_fix"]
    assert labels["next_session_cue"]
