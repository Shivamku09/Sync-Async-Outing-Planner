from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, Enum, ForeignKey, Index, Integer, SmallInteger, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.common.enums import CallbackStatus, OutboxEventType, OutboxStatus, PlanningStatus, RequestMode


class Base(DeclarativeBase):
    pass


class VenueRow(Base):
    __tablename__ = "venues"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    area: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String(50)), nullable=False, default=list)
    estimated_cost_inr: Mapped[int] = mapped_column(Integer, nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    min_age: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    max_age: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    open_days: Mapped[list[str]] = mapped_column(ARRAY(String(20)), nullable=False, default=list)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("estimated_cost_inr > 0"), CheckConstraint("capacity > 0"),
        CheckConstraint("min_age >= 1 AND min_age <= max_age"),
    )


class RequestRow(Base):
    __tablename__ = "requests"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    mode: Mapped[RequestMode] = mapped_column(Enum(RequestMode, native_enum=False), nullable=False)
    status: Mapped[PlanningStatus] = mapped_column(Enum(PlanningStatus, native_enum=False), nullable=False)
    location_area: Mapped[str] = mapped_column(String(100), nullable=False)
    outing_date: Mapped[date] = mapped_column(Date, nullable=False)
    group_size: Mapped[int] = mapped_column(Integer, nullable=False)
    age_min: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    age_max: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    budget_inr: Mapped[int] = mapped_column(Integer, nullable=False)
    preferences: Mapped[list[str]] = mapped_column(ARRAY(String(50)), nullable=False, default=list)
    callback_url: Mapped[str | None] = mapped_column(Text)
    callback_status: Mapped[CallbackStatus] = mapped_column(Enum(CallbackStatus, native_enum=False), nullable=False)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    failed_constraint: Mapped[str | None] = mapped_column(String(30))
    error_code: Mapped[str | None] = mapped_column(String(100))
    planner_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    callback_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    processing_lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    callback_lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("group_size > 0"), CheckConstraint("age_min >= 1 AND age_min <= age_max"),
        CheckConstraint("budget_inr > 0"), Index("ix_requests_mode_created_id", "mode", created_at.desc(), id.desc()),
    )


class CallbackAttemptRow(Base):
    __tablename__ = "callback_attempts"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    request_id: Mapped[UUID] = mapped_column(ForeignKey("requests.id", ondelete="CASCADE"), nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    http_status: Mapped[int | None] = mapped_column(SmallInteger)
    error_category: Mapped[str | None] = mapped_column(String(100))
    outcome: Mapped[str] = mapped_column(String(40), nullable=False)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (UniqueConstraint("request_id", "attempt_number"),)


class OutboxEventRow(Base):
    __tablename__ = "outbox_events"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    request_id: Mapped[UUID] = mapped_column(ForeignKey("requests.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[OutboxEventType] = mapped_column(Enum(OutboxEventType, native_enum=False), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[OutboxStatus] = mapped_column(Enum(OutboxStatus, native_enum=False), nullable=False, default=OutboxStatus.PENDING)
    publish_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (Index("ix_outbox_available", "status", "available_at", "created_at"),)
