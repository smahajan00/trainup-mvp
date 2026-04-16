from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from app.models.enums import InputType, SessionStatus
from app.schemas.base import APIBaseModel


class SessionCreateRequest(APIBaseModel):
    drill_id: UUID
    input_type: InputType


class SessionResponse(APIBaseModel):
    id: UUID
    user_id: UUID
    drill_id: UUID
    sport_id: UUID
    input_type: InputType
    status: SessionStatus
    start_time: datetime
    end_time: datetime | None
    drill_name: str
    sport_name: str


class UploadValidationResult(APIBaseModel):
    is_valid: bool
    content_type: str | None = None
    file_size_bytes: int = Field(ge=0)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class UploadValidationResponse(APIBaseModel):
    session_id: UUID
    status: SessionStatus
    upload_received: bool
    validation: UploadValidationResult
    next_step: str


class LiveReadinessRequest(APIBaseModel):
    camera_permission_granted: bool = False
    lighting_ready: bool = False
    framing_ready: bool = False
    space_ready: bool = False
    client_ready: bool = False


class LiveReadinessResponse(APIBaseModel):
    camera_ready: bool
    lighting_ready: bool
    framing_ready: bool
    space_ready: bool
    warnings: list[str] = Field(default_factory=list)


class LiveStartResponse(APIBaseModel):
    session_id: UUID
    status: SessionStatus
    started: bool
    message: str
    readiness: LiveReadinessResponse


class FrameBatchRequest(APIBaseModel):
    frame_count: int = Field(gt=0, le=600)
    timestamps: list[float] = Field(default_factory=list)
    client_ready: bool

    @model_validator(mode="after")
    def validate_timestamp_count(self) -> "FrameBatchRequest":
        if self.timestamps and len(self.timestamps) != self.frame_count:
            raise ValueError("timestamps must contain one entry per frame.")
        return self


class FrameBatchAcceptanceResult(APIBaseModel):
    accepted: bool
    frame_count: int
    message: str


class FrameBatchResponse(APIBaseModel):
    session_id: UUID
    accepted: bool
    frame_count: int
    message: str


class LiveEndRequest(APIBaseModel):
    final_status: SessionStatus

    @field_validator("final_status")
    @classmethod
    def validate_final_status(cls, value: SessionStatus) -> SessionStatus:
        if value not in {SessionStatus.COMPLETED, SessionStatus.ABORTED}:
            raise ValueError("final_status must be COMPLETED or ABORTED.")
        return value
