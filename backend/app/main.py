import logging
import threading

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import settings
from app.services.llm_client import is_local_llm_provider, llm_enhancement_enabled

logger = logging.getLogger(__name__)


def _build_validation_detail(errors: list[dict[str, object]]) -> str:
    if not errors:
        return "Invalid request input."

    first_error = errors[0]
    location = " → ".join(str(item) for item in first_error.get("loc", [])[1:])
    message = str(first_error.get("msg", "Invalid request input."))
    if location:
        return f"{location}: {message}"
    return message


def create_application() -> FastAPI:
    application = FastAPI(title=settings.app_name, version="0.1.0")

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.backend_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(api_router, prefix=settings.api_prefix)

    @application.on_event("startup")
    async def warmup_optional_ai_services() -> None:
        if (
            settings.llm_warmup_on_startup
            and llm_enhancement_enabled(settings)
            and is_local_llm_provider(settings.llm_provider)
        ):
            def _warmup_llm() -> None:
                try:
                    from app.core.dependencies import get_local_llm_client

                    get_local_llm_client().warmup()
                except Exception as exc:
                    logger.warning("Local LLM warmup failed", extra={"error": str(exc)})

            threading.Thread(target=_warmup_llm, daemon=True).start()

        if not settings.tts_warmup_on_startup or not settings.tts_enabled:
            return

        def _warmup_tts() -> None:
            try:
                from app.core.dependencies import get_feedback_tts_service

                get_feedback_tts_service().ensure_loaded()
            except Exception as exc:
                logger.warning("Kokoro TTS warmup failed", extra={"error": str(exc)})

        threading.Thread(target=_warmup_tts, daemon=True).start()

    @application.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        _request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        errors = exc.errors()
        logger.warning("Request validation failed", extra={"errors": errors})
        return JSONResponse(
            status_code=422,
            content={
                "detail": _build_validation_detail(errors),
                "errors": errors,
            },
        )

    return application


app = create_application()
