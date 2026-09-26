from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from uuid import UUID

from app.common.enums import CallbackStatus, FailedConstraint, PlanningStatus, RequestMode


@dataclass(frozen=True, slots=True)
class PlanningInput:
    location: str
    outing_date: date
    group_size: int
    age_min: int
    age_max: int
    budget_inr: int
    preferences: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Venue:
    id: UUID
    name: str
    area: str
    tags: frozenset[str]
    estimated_cost_inr: int
    capacity: int
    min_age: int
    max_age: int
    open_days: frozenset[str]


@dataclass(frozen=True, slots=True)
class PlanStop:
    position: int
    venue_id: UUID
    name: str
    area: str
    estimated_cost_inr: int


@dataclass(frozen=True, slots=True)
class Plan:
    stops: tuple[PlanStop, ...]
    total_cost_inr: int
    leftover_budget_inr: int


@dataclass(frozen=True, slots=True)
class PlanningOutcome:
    plan: Plan | None = None
    failed_constraint: FailedConstraint | None = None


@dataclass(slots=True)
class RequestRecord:
    id: UUID
    mode: RequestMode
    status: PlanningStatus
    planning_input: PlanningInput
    callback_status: CallbackStatus
    callback_url: str | None = None
    plan: Plan | None = None
    failed_constraint: FailedConstraint | None = None
    error_code: str | None = None
    created_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    updated_at: datetime | None = None
