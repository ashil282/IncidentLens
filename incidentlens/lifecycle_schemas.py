from typing import Literal

from pydantic import BaseModel, Field


class OpenIncidentRequest(BaseModel):
    detector_id: str = Field(min_length=1, max_length=120)
    service: str = Field(min_length=1, max_length=120)
    environment: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=240)
    severity: Literal["low", "medium", "high", "critical"]
    summary: str = Field(min_length=1, max_length=4000)
    actor: str = Field(default="system", min_length=1, max_length=120)


class IncidentUpdateRequest(BaseModel):
    status: Literal["OPEN", "ACKNOWLEDGED", "RESOLVED"] | None = None
    severity: Literal["low", "medium", "high", "critical"] | None = None
    assignee: str | None = Field(default=None, max_length=120)
    resolution_note: str | None = Field(default=None, max_length=4000)
    actor: str = Field(default="operator", min_length=1, max_length=120)
