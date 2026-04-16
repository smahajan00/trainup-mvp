from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class APIBaseModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        from_attributes=True,
        str_strip_whitespace=True,
    )
