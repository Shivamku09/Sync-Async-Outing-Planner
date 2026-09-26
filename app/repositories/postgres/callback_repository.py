from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.common.enums import CallbackStatus
from app.repositories.interfaces.callback_repository import CallbackAttemptResult, CallbackRepository
from app.repositories.postgres.mappers import request_entity
from app.repositories.postgres.models import CallbackAttemptRow, RequestRow


class PostgresCallbackRepository(CallbackRepository):
    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._session_factory = session_factory

    async def claim(self, request_id: UUID):
        now = datetime.now(UTC)
        async with self._session_factory() as session, session.begin():
            row = await session.get(RequestRow, request_id, with_for_update=True)
            if row is None or row.callback_status in {CallbackStatus.DELIVERED, CallbackStatus.FAILED, CallbackStatus.DEAD_LETTERED}:
                return None
            if row.callback_lease_until and row.callback_lease_until > now:
                return None
            row.callback_attempts += 1
            row.callback_status = CallbackStatus.DELIVERING
            row.callback_lease_until = now + timedelta(minutes=1)
            await session.flush()
            await session.refresh(row)
            return request_entity(row), row.callback_attempts

    async def save_result(self, request_id: UUID, attempt: int, result: CallbackAttemptResult) -> None:
        now = datetime.now(UTC)
        async with self._session_factory() as session, session.begin():
            row = await session.get(RequestRow, request_id, with_for_update=True)
            if row is None:
                return
            if result.delivered:
                row.callback_status = CallbackStatus.DELIVERED
                outcome = "delivered"
            elif result.retryable:
                row.callback_status = CallbackStatus.PENDING
                outcome = "retry_scheduled"
            else:
                row.callback_status = CallbackStatus.FAILED
                outcome = "permanent_failure"
            row.callback_lease_until = None
            session.add(CallbackAttemptRow(
                request_id=request_id, attempt_number=attempt,
                started_at=now - timedelta(milliseconds=result.duration_ms), completed_at=now,
                duration_ms=result.duration_ms, http_status=result.http_status,
                error_category=result.error_category, outcome=outcome,
            ))

    async def mark_dead_lettered(self, request_id: UUID) -> None:
        async with self._session_factory() as session, session.begin():
            row = await session.get(RequestRow, request_id, with_for_update=True)
            if row:
                row.callback_status = CallbackStatus.DEAD_LETTERED
                row.callback_lease_until = None
