from abc import ABC, abstractmethod
from uuid import UUID

from app.common.entities import PlanningInput, PlanningOutcome, RequestRecord
from app.common.enums import RequestMode


class RequestRepository(ABC):
    @abstractmethod
    async def create_sync(self, planning_input: PlanningInput) -> RequestRecord: ...

    @abstractmethod
    async def create_async(self, planning_input: PlanningInput, callback_url: str) -> RequestRecord: ...

    @abstractmethod
    async def get(self, request_id: UUID) -> RequestRecord | None: ...

    @abstractmethod
    async def list(self, mode: RequestMode, limit: int, cursor: str | None) -> tuple[list[RequestRecord], str | None]: ...

    @abstractmethod
    async def complete(self, request_id: UUID, outcome: PlanningOutcome, create_callback_event: bool) -> RequestRecord: ...

    @abstractmethod
    async def claim_for_planning(self, request_id: UUID) -> RequestRecord | None: ...

    @abstractmethod
    async def mark_planner_failed(self, request_id: UUID, error_code: str) -> None: ...

    @abstractmethod
    async def count_async_backlog(self) -> int: ...
