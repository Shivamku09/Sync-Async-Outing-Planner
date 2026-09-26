from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator, model_validator

from app.common.enums import CallbackStatus, FailedConstraint, PlanningStatus, RequestMode


class PlanningRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    location: Annotated[str, Field(min_length=1, max_length=100)]
    outing_date: date
    group_size: Annotated[int, Field(ge=1, le=100)]
    age_min: Annotated[int, Field(ge=1, le=120)]
    age_max: Annotated[int, Field(ge=1, le=120)]
    budget_inr: Annotated[int, Field(gt=0, le=10_000_000)]
    preferences: Annotated[list[str], Field(default_factory=list, max_length=10)]

    @field_validator("location")
    @classmethod
    def normalize_location(cls, value: str) -> str:
        return " ".join(value.strip().split())

    @field_validator("preferences")
    @classmethod
    def normalize_preferences(cls, values: list[str]) -> list[str]:
        normalized = [" ".join(value.strip().lower().split()) for value in values]
        if any(not value for value in normalized):
            raise ValueError("preference tags cannot be empty")
        if len(set(normalized)) != len(normalized):
            raise ValueError("preference tags must be unique")
        return normalized

    @model_validator(mode="after")
    def validate_age_range(self) -> "PlanningRequest":
        if self.age_min > self.age_max:
            raise ValueError("age_min must be less than or equal to age_max")
        return self


class AsyncPlanningRequest(PlanningRequest):
    callback_url: AnyHttpUrl


class PlanStopResponse(BaseModel):
    position: int
    venue_id: UUID
    name: str
    area: str
    estimated_cost_inr: int


class PlanResponse(BaseModel):
    stops: list[PlanStopResponse]
    total_cost_inr: int
    leftover_budget_inr: int


class RequestResponse(BaseModel):
    id: UUID
    mode: RequestMode
    status: PlanningStatus
    callback_status: CallbackStatus
    plan: PlanResponse | None = None
    failed_constraint: FailedConstraint | None = None
    error_code: str | None = None
    created_at: datetime | None = None
    completed_at: datetime | None = None


class AsyncAcceptedResponse(BaseModel):
    id: UUID
    mode: Literal[RequestMode.ASYNC] = RequestMode.ASYNC
    status: Literal[PlanningStatus.PENDING] = PlanningStatus.PENDING
    status_url: str
    created_at: datetime


class RequestListResponse(BaseModel):
    items: list[RequestResponse]
    next_cursor: str | None = None


class HealthResponse(BaseModel):
    status: str
    postgresql: str
    rabbitmq: str
