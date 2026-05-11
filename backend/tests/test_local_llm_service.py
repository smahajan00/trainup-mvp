from __future__ import annotations

from app.services.local_llm_service import LocalLlamaCppLLMClient


def test_local_llm_extracts_json_from_fenced_output() -> None:
    content = """
    ```json
    {"coaching_cue": "Keep the rep controlled."}
    ```
    """

    assert LocalLlamaCppLLMClient._clean_model_output(content) == (
        '{"coaching_cue": "Keep the rep controlled."}'
    )


def test_local_llm_relative_model_path_resolves_under_backend_root() -> None:
    client = LocalLlamaCppLLMClient(
        model_path="models/Qwen2.5-7B-Instruct-Q4_K_M.gguf",
    )

    assert client.model_path.name == "Qwen2.5-7B-Instruct-Q4_K_M.gguf"
    assert client.model_path.parent.name == "models"
    assert client.model_path.parent.parent.name == "backend"


def test_local_llm_defaults_to_cpu_demo_settings() -> None:
    client = LocalLlamaCppLLMClient(
        model_path="models/Qwen2.5-7B-Instruct-Q4_K_M.gguf",
    )

    assert client.gpu_layers == 0
    assert client.batch_size == 128
