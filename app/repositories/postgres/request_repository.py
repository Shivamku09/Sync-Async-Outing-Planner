from __future__ import annotations

import base64
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.common.entities import PlanningInput, PlanningOutcome, RequestRecord
from app.common.enums import CallbackStatus, OutboxEventType, PlanningStatus, RequestMode
from app.repositories.interfaces.request_repository import RequestRepository
from app.repositories.postgres.mappers import plan_to_json, request_entity
from app.repositories.postgres.models import OutboxEventRow, RequestRow


def _cursor_encode(created_at: datetime, request_id: UUID) -> str:
    raw = f"{created_at.isoformat()}|{request_id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def _cursor_decode(value: str) -> tuple[datetime, UUID]:
    raw = base64.urlsafe_b64decode(value.encode()).decode()
    timestamp, request_id = raw.split("|", 1)
    return datetime.fromisoformat(timestamp), UUID(request_id)


class PostgresRequestRepository(RequestRepository):
    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._session_factory = session_factory

    @staticmethod
    def _new_row(planning_input: PlanningInput, mode: RequestMode, callback_url: str | None = None) -> RequestRow:
        return RequestRow(
            mode=mode,
            status=PlanningStatus.PROCESSING if mode == RequestMode.SYNC else PlanningStatus.PENDING,
            location_area=planning_input.location.lower(), outing_date=planning_input.outing_date,
            group_size=planning_input.group_size, age_min=planning_input.age_min,
            age_max=planning_input.age_max, budget_inr=planning_input.budget_inr,
            preferences=list(planning_input.preferences), callback_url=callback_url,
            callback_status=CallbackStatus.NOT_APPLICABLE if mode == RequestMode.SYNC else CallbackStatus.PENDING,
            started_at=datetime.now(UTC) if mode == RequestMode.SYNC else None,
        )

    async def create_sync(self, planning_input: PlanningInput) -> RequestRecord:
        async with self._session_factory() as session, session.begin():
            row = self._new_row(planning_input, RequestMode.SYNC)
            session.add(row)
            await session.flush()
            return request_entity(row)

    async def create_async(self, planning_input: PlanningInput, callback_url: str) -> RequestRecord:
        async with self._session_factory() as session, session.begin():
            row = self._new_row(planning_input, RequestMode.ASYNC, callback_url)
            session.add(row)
            await session.flush()
            session.add(OutboxEventRow(
                request_id=row.id, event_type=OutboxEventType.PLAN_REQUESTED,
                payload={"schema_version": 1, "request_id": str(row.id)},
            ))
            await session.flush()
            return request_entity(row)

    async def get(self, request_id: UUID) -> RequestRecord | None:
        async with self._session_factory() as session:
            row = await session.get(RequestRow, request_id)
            return request_entity(row) if row else None

    async def list(self, mode: RequestMode, limit: int, cursor: str | None) -> tuple[list[RequestRecord], str | None]:
        statement = select(RequestRow).where(RequestRow.mode == mode)
        if cursor:
            created_at, request_id = _cursor_decode(cursor)
            statement = statement.where(or_(
                RequestRow.created_at < created_at,
                and_(RequestRow.created_at == created_at, RequestRow.id < request_id),
            ))
        statement = statement.order_by(RequestRow.created_at.desc(), RequestRow.id.desc()).limit(limit + 1)
        async with self._session_factory() as session:
            rows = list((await session.scalars(statement)).all())
        has_more = len(rows) > limit
        rows = rows[:limit]
        next_cursor = _cursor_encode(rows[-1].created_at, rows[-1].id) if has_more and rows else None
        return [request_entity(row) for row in rows], next_cursor

    async def complete(self, request_id: UUID, outcome: PlanningOutcome, create_callback_event: bool) -> RequestRecord:
        async with self._session_factory() as session, session.begin():
            row = await session.get(RequestRow, request_id, with_for_update=True)
            if row is None:
                raise LookupError(str(request_id))
            row.status = PlanningStatus.SUCCEEDED if outcome.plan else PlanningStatus.FAILED
            row.result = plan_to_json(outcome.plan) if outcome.plan else None
            row.failed_constraint = outcome.failed_constraint.value if outcome.failed_constraint else None
            row.completed_at = datetime.now(UTC)
            row.processing_lease_until = None
            if create_callback_event:
                session.add(OutboxEventRow(
                    request_id=row.id, event_type=OutboxEventType.CALLBACK_REQUESTED,
                    payload={"schema_version": 1, "request_id": str(row.id)},
                ))
            await session.flush()
            await session.refresh(row)
            return request_entity(row)

    async def claim_for_planning(self, request_id: UUID) -> RequestRecord | None:
        now = datetime.now(UTC)
        async with self._session_factory() as session, session.begin():
            row = await session.get(RequestRow, request_id, with_for_update=True)
            if row is None or row.status in {PlanningStatus.SUCCEEDED, PlanningStatus.FAILED}:
                return None
            if row.processing_lease_until and row.processing_lease_until > now:
                return None
            row.status = PlanningStatus.PROCESSING
            row.started_at = row.started_at or now
            row.processing_lease_until = now + timedelta(minutes=2)
            row.planner_attempts += 1
            await session.flush()
            await session.refresh(row)
            return request_entity(row)

    async def mark_planner_failed(self, request_id: UUID, error_code: str) -> None:
        async with self._session_factory() as session, session.begin():
            row = await session.get(RequestRow, request_id, with_for_update=True)
            if row:
                row.status = PlanningStatus.FAILED
                row.error_code = error_code
                row.completed_at = datetime.now(UTC)
                row.processing_lease_until = None

    async def count_async_backlog(self) -> int:
        async with self._session_factory() as session:
            return int(await session.scalar(select(func.count()).select_from(RequestRow).where(
                RequestRow.mode == RequestMode.ASYNC,
                RequestRow.status.in_([PlanningStatus.PENDING, PlanningStatus.PROCESSING]),
            )) or 0)
