from abc import ABC, abstractmethod
from uuid import UUID

from app.common.entities import PlanningInput, RequestRecord
from app.common.enums import RequestMode


class RequestService(ABC):
    @abstractmethod
    async def create_sync(self, planning_input: PlanningInput) -> RequestRecord: ...

    @abstractmethod
    async def create_async(self, planning_input: PlanningInput, callback_url: str) -> RequestRecord: ...

    @abstractmethod
    async def get(self, request_id: UUID) -> RequestRecord: ...

    @abstractmethod
    async def list(self, mode: RequestMode, limit: int, cursor: str | None) -> tuple[list[RequestRecord], str | None]: ...
