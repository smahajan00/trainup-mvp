from __future__ import annotations

import io
import logging
import re
import time
from dataclasses import dataclass, field
from threading import Lock
from typing import Any


KOKORO_MODEL_NAME = "hexgrad/Kokoro-82M"
KOKORO_DEFAULT_VOICE = "am_michael"
KOKORO_SAMPLE_RATE = 24000
KOKORO_DEFAULT_SEGMENT_PAUSE_MS = 400
logger = logging.getLogger("uvicorn.error")

_RAW_DIAGNOSTIC_RE = re.compile(
    r"\b(?:"
    r"MISSING_[A-Z0-9_]+|"
    r"LLM_[A-Z0-9_]+|"
    r"EVALUATION_STATUS:[A-Z0-9_]+|"
    r"[A-Z][A-Z0-9_]+_STATUS:[A-Z0-9_]+"
    r")\b"
)
_TECHNICAL_PHRASE_RE = re.compile(
    r"\b(?:"
    r"Priority\s+\d+\s+item selected[^.]*\.?|"
    r"strongly\s+off\s+deviation[^.]*\.?|"
    r"confidence\s+supports[^.]*\.?"
    r")",
    re.IGNORECASE,
)
_ALL_CAPS_PHRASE_RE = re.compile(r"\b[A-Z]{2,}(?:\s+[A-Z]{2,})*\b")


class FeedbackTTSUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True)
class KokoroFeedbackTTSService:
    model_name: str = KOKORO_MODEL_NAME
    voice: str = KOKORO_DEFAULT_VOICE
    pause_ms: int = KOKORO_DEFAULT_SEGMENT_PAUSE_MS
    _lock: Lock = field(default_factory=Lock, init=False, repr=False, compare=False)
    _pipeline: Any | None = field(default=None, init=False, repr=False, compare=False)

    def ensure_loaded(self) -> None:
        self._get_pipeline()

    def _get_pipeline(self):
        if self._pipeline is not None:
            return self._pipeline

        with self._lock:
            if self._pipeline is not None:
                return self._pipeline

            try:
                from kokoro import KPipeline
            except Exception as exc:  # pragma: no cover - optional runtime package.
                raise FeedbackTTSUnavailableError(
                    "Kokoro TTS runtime is not installed or could not be imported."
                ) from exc

            load_started_at = time.perf_counter()
            try:
                pipeline = KPipeline(lang_code="a", repo_id=self.model_name)
            except TypeError:
                pipeline = KPipeline(lang_code="a")
            except Exception as exc:  # pragma: no cover - model/runtime dependent.
                raise FeedbackTTSUnavailableError(
                    "Kokoro TTS model could not be loaded."
                ) from exc

            object.__setattr__(self, "_pipeline", pipeline)
            logger.info(
                "Kokoro TTS model loaded",
                extra={
                    "model": self.model_name,
                    "voice": self.voice,
                    "load_time_ms": round(
                        (time.perf_counter() - load_started_at) * 1000,
                        3,
                    ),
                },
            )
            return pipeline

    def synthesize(self, *, segments: list[str]) -> bytes:
        synthesis_started_at = time.perf_counter()
        normalized_segments = [
            normalized
            for normalized in (
                self.normalize_text_segment(segment) for segment in segments
            )
            if normalized
        ]
        if not normalized_segments:
            raise FeedbackTTSUnavailableError("No coaching text was provided for TTS.")

        try:
            import numpy as np
            import soundfile as sf
        except Exception as exc:  # pragma: no cover - depends on optional runtime package.
            raise FeedbackTTSUnavailableError(
                "Audio encoding dependencies are not installed or could not be imported."
            ) from exc

        try:
            pipeline = self._get_pipeline()
            audio_chunks: list[Any] = []
            silence = self._build_silence(np=np, pause_ms=self.pause_ms)
            for index, segment in enumerate(normalized_segments):
                segment_chunks = [
                    np.asarray(audio, dtype=np.float32)
                    for _, _, audio in pipeline(segment, voice=self.voice)
                ]
                if segment_chunks:
                    audio_chunks.extend(segment_chunks)
                    if silence.size and index < len(normalized_segments) - 1:
                        audio_chunks.append(silence)
        except Exception as exc:  # pragma: no cover - model/runtime dependent.
            raise FeedbackTTSUnavailableError("Kokoro TTS generation failed.") from exc

        if not audio_chunks:
            raise FeedbackTTSUnavailableError("Kokoro TTS returned no audio.")

        audio = (
            audio_chunks[0]
            if len(audio_chunks) == 1
            else np.concatenate(audio_chunks)
        )
        output = io.BytesIO()
        sf.write(output, audio, KOKORO_SAMPLE_RATE, format="WAV")
        logger.info(
            "Kokoro TTS audio generated",
            extra={
                "model": self.model_name,
                "voice": self.voice,
                "segments": len(normalized_segments),
                "pause_ms": self.pause_ms,
                "duration_ms": round((time.perf_counter() - synthesis_started_at) * 1000, 3),
            },
        )
        return output.getvalue()

    @staticmethod
    def normalize_text_segment(value: str) -> str:
        cleaned = _RAW_DIAGNOSTIC_RE.sub(" ", value)
        cleaned = _TECHNICAL_PHRASE_RE.sub(" ", cleaned)
        cleaned = cleaned.replace("_", " ")
        cleaned = _ALL_CAPS_PHRASE_RE.sub(lambda match: match.group(0).lower(), cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned)
        cleaned = re.sub(r"\s+([,.;:!?])", r"\1", cleaned)
        return cleaned.strip(" -:;,")

    @staticmethod
    def _build_silence(*, np: Any, pause_ms: int):
        pause_ms = max(0, pause_ms)
        sample_count = int(KOKORO_SAMPLE_RATE * pause_ms / 1000)
        return np.zeros(sample_count, dtype=np.float32)
