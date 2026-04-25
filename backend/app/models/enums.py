from __future__ import annotations

from enum import Enum

from sqlalchemy import Enum as SQLAlchemyEnum


class SkillLevel(str, Enum):
    BEGINNER = "BEGINNER"
    INTERMEDIATE = "INTERMEDIATE"
    ADVANCED = "ADVANCED"


class InputType(str, Enum):
    UPLOAD = "UPLOAD"
    LIVE = "LIVE"


class CameraView(str, Enum):
    FRONTAL = "FRONTAL"
    LEFT_SAGITTAL = "LEFT_SAGITTAL"
    RIGHT_SAGITTAL = "RIGHT_SAGITTAL"


class DominantSide(str, Enum):
    LEFT = "LEFT"
    RIGHT = "RIGHT"


class SessionStatus(str, Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    ABORTED = "ABORTED"


class SeverityLevel(str, Enum):
    MINOR = "MINOR"
    MODERATE = "MODERATE"
    SEVERE = "SEVERE"


class ComputationStatus(str, Enum):
    COMPUTED = "COMPUTED"
    NOT_COMPUTABLE = "NOT_COMPUTABLE"


skill_level_enum = SQLAlchemyEnum(
    SkillLevel,
    name="skill_level_enum",
    native_enum=True,
)

input_type_enum = SQLAlchemyEnum(
    InputType,
    name="input_type_enum",
    native_enum=True,
)

camera_view_enum = SQLAlchemyEnum(
    CameraView,
    name="camera_view_enum",
    native_enum=True,
)

dominant_side_enum = SQLAlchemyEnum(
    DominantSide,
    name="dominant_side_enum",
    native_enum=True,
)

session_status_enum = SQLAlchemyEnum(
    SessionStatus,
    name="session_status_enum",
    native_enum=True,
)

severity_level_enum = SQLAlchemyEnum(
    SeverityLevel,
    name="severity_level_enum",
    native_enum=True,
)

computation_status_enum = SQLAlchemyEnum(
    ComputationStatus,
    name="computation_status_enum",
    native_enum=True,
)
