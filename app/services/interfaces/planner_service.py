from abc import ABC, abstractmethod
from uuid import UUID

from app.common.entities import PlanningInput, PlanningOutcome, RequestRecord


class PlannerService(ABC):
    @abstractmethod
    async def plan(self, planning_input: PlanningInput) -> PlanningOutcome: ...

    @abstractmethod
    async def process_async_request(self, request_id: UUID) -> RequestRecord | None: ...
