from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Any

from app.services.llm_client import LLMClientError, LLMMessage, LLMProviderConfig

logger = logging.getLogger(__name__)

DEFAULT_QWEN_REPO_ID = "bartowski/Qwen2.5-7B-Instruct-GGUF"
DEFAULT_QWEN_FILENAME = "Qwen2.5-7B-Instruct-Q4_K_M.gguf"


class LocalLlamaCppLLMClient:
    """Local llama.cpp GGUF client used for coaching wording refinement only."""

    def __init__(
        self,
        *,
        model_path: str,
        repo_id: str = DEFAULT_QWEN_REPO_ID,
        filename: str = DEFAULT_QWEN_FILENAME,
        context_size: int = 4096,
        gpu_layers: int = 0,
        batch_size: int = 128,
        verbose: bool = False,
    ) -> None:
        self.model_path = self._resolve_model_path(model_path)
        self.repo_id = repo_id
        self.filename = filename
        self.context_size = context_size
        self.gpu_layers = gpu_layers
        self.batch_size = batch_size
        self.verbose = verbose
        self._llama: Any | None = None
        self._load_lock = threading.Lock()
        self._generation_lock = threading.Lock()

    def generate_text(
        self,
        *,
        messages: list[LLMMessage],
        config: LLMProviderConfig,
    ) -> str:
        llama = self._get_llama()
        chat_messages = [
            {"role": message.role, "content": message.content}
            for message in messages
        ]

        try:
            with self._generation_lock:
                response = llama.create_chat_completion(
                    messages=chat_messages,
                    temperature=config.temperature,
                    max_tokens=config.max_tokens,
                )
        except Exception as exc:
            raise LLMClientError("Local llama.cpp generation failed.") from exc

        content = self._extract_chat_content(response)
        return self._clean_model_output(content)

    def warmup(self) -> None:
        llama = self._get_llama()
        try:
            with self._generation_lock:
                llama.create_chat_completion(
                    messages=[
                        {
                            "role": "system",
                            "content": "You return short JSON only.",
                        },
                        {
                            "role": "user",
                            "content": 'Return {"ok": true}.',
                        },
                    ],
                    temperature=0.0,
                    max_tokens=8,
                )
        except Exception as exc:
            logger.warning("Local LLM warmup generation failed", extra={"error": str(exc)})

    def _get_llama(self) -> Any:
        if self._llama is not None:
            return self._llama

        with self._load_lock:
            if self._llama is not None:
                return self._llama
            model_path = self._ensure_model_file()
            try:
                from llama_cpp import Llama
            except Exception as exc:
                raise LLMClientError(
                    "llama-cpp-python is not installed or could not be imported."
                ) from exc

            try:
                self._llama = Llama(
                    model_path=str(model_path),
                    n_ctx=self.context_size,
                    n_gpu_layers=self.gpu_layers,
                    n_batch=self.batch_size,
                    n_ubatch=self.batch_size,
                    offload_kqv=False,
                    verbose=self.verbose,
                )
            except Exception as exc:
                raise LLMClientError("Local GGUF model could not be loaded.") from exc

            logger.info("Local LLM model loaded", extra={"model_path": str(model_path)})
            return self._llama

    def _ensure_model_file(self) -> Path:
        if self.model_path.exists():
            return self.model_path

        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            from huggingface_hub import hf_hub_download
        except Exception as exc:
            raise LLMClientError(
                "huggingface_hub is required to download the local GGUF model."
            ) from exc

        try:
            downloaded_path = hf_hub_download(
                repo_id=self.repo_id,
                filename=self.filename,
                local_dir=str(self.model_path.parent),
                local_dir_use_symlinks=False,
            )
        except Exception as exc:
            raise LLMClientError("Local GGUF model download failed.") from exc

        resolved_download = Path(downloaded_path)
        if resolved_download.exists():
            return resolved_download
        if self.model_path.exists():
            return self.model_path
        raise LLMClientError("Local GGUF model download did not create a model file.")

    @staticmethod
    def _extract_chat_content(response: Any) -> str:
        try:
            content = response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMClientError("Local llama.cpp response was malformed.") from exc
        if not isinstance(content, str) or not content.strip():
            raise LLMClientError("Local llama.cpp returned an empty response.")
        return content.strip()

    @staticmethod
    def _clean_model_output(content: str) -> str:
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`").strip()
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:].strip()

        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            return cleaned[start : end + 1]
        return cleaned

    @staticmethod
    def _resolve_model_path(model_path: str) -> Path:
        path = Path(model_path).expanduser()
        if path.is_absolute():
            return path
        backend_root = Path(__file__).resolve().parents[2]
        return backend_root / path
