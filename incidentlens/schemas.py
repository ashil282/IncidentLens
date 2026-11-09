from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EventIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    service: str = Field(min_length=1, max_length=120, pattern=r"^[A-Za-z0-9_.:-]+$")
    environment: str = Field(default="local", min_length=1, max_length=80)
    event_type: Literal["http_request", "log", "deployment", "alert", "metric"]
    severity: Literal["debug", "info", "warning", "error", "critical"] = "info"
    message: str = Field(min_length=1, max_length=4000)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    attributes: dict[str, Any] = Field(default_factory=dict)

    @field_validator("timestamp")
    @classmethod
    def timestamp_must_be_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must include timezone information")
        return value.astimezone(UTC)


class EventRecord(EventIn):
    id: str = Field(default_factory=lambda: str(uuid4()))
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class EventBatch(BaseModel):
    events: list[EventIn] = Field(min_length=1)


class IngestResult(BaseModel):
    accepted: int
    event_ids: list[str]


class IncidentReport(BaseModel):
    id: str
    service: str
    environment: str
    title: str
    severity: str
    started_at: datetime
    event_count: int
    detector: str
    evidence: list[EventRecord]
    findings: list[str]
    limitations: list[str]
