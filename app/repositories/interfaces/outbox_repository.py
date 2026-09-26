from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import UUID

from app.common.enums import OutboxEventType


@dataclass(frozen=True, slots=True)
class OutboxEvent:
    id: UUID
    request_id: UUID
    event_type: OutboxEventType
    payload: dict[str, object]
    publish_attempts: int


class OutboxRepository(ABC):
    @abstractmethod
    async def claim_available(self, limit: int) -> list[OutboxEvent]: ...

    @abstractmethod
    async def mark_published(self, event_id: UUID) -> None: ...

    @abstractmethod
    async def release_failed(self, event_id: UUID, error_category: str) -> None: ...
