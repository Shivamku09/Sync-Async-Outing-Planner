from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.common.enums import OutboxStatus
from app.repositories.interfaces.outbox_repository import OutboxEvent, OutboxRepository
from app.repositories.postgres.models import OutboxEventRow


class PostgresOutboxRepository(OutboxRepository):
    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._session_factory = session_factory

    async def claim_available(self, limit: int) -> list[OutboxEvent]:
        async with self._session_factory() as session, session.begin():
            statement = (
                select(OutboxEventRow)
                .where(OutboxEventRow.status == OutboxStatus.PENDING, OutboxEventRow.available_at <= datetime.now(UTC))
                .order_by(OutboxEventRow.created_at)
                .limit(limit).with_for_update(skip_locked=True)
            )
            rows = list((await session.scalars(statement)).all())
            for row in rows:
                row.status = OutboxStatus.PUBLISHING
                row.claimed_at = datetime.now(UTC)
                row.publish_attempts += 1
            return [OutboxEvent(row.id, row.request_id, row.event_type, row.payload, row.publish_attempts) for row in rows]

    async def mark_published(self, event_id: UUID) -> None:
        async with self._session_factory() as session, session.begin():
            row = await session.get(OutboxEventRow, event_id, with_for_update=True)
            if row:
                row.status = OutboxStatus.PUBLISHED
                row.published_at = datetime.now(UTC)

    async def release_failed(self, event_id: UUID, error_category: str) -> None:
        async with self._session_factory() as session, session.begin():
            row = await session.get(OutboxEventRow, event_id, with_for_update=True)
            if row:
                row.status = OutboxStatus.PENDING
                row.claimed_at = None
                row.last_error = error_category[:100]
