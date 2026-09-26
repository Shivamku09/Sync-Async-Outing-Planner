from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import UUID

from app.common.entities import RequestRecord


@dataclass(frozen=True, slots=True)
class CallbackAttemptResult:
    delivered: bool
    retryable: bool
    http_status: int | None
    error_category: str | None
    duration_ms: int
    exhausted: bool = False
    next_retry_delay_seconds: int | None = None


class CallbackRepository(ABC):
    @abstractmethod
    async def claim(self, request_id: UUID) -> tuple[RequestRecord, int] | None: ...

    @abstractmethod
    async def save_result(self, request_id: UUID, attempt: int, result: CallbackAttemptResult) -> None: ...

    @abstractmethod
    async def mark_dead_lettered(self, request_id: UUID) -> None: ...
