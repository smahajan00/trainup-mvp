import logging

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import settings

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
