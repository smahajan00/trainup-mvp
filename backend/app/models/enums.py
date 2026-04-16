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


class SessionStatus(str, Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    ABORTED = "ABORTED"


class SeverityLevel(str, Enum):
    MINOR = "MINOR"
    MODERATE = "MODERATE"
    SEVERE = "SEVERE"


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

