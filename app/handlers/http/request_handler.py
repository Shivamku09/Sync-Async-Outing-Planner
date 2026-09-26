from uuid import UUID

from app.api.schemas import AsyncPlanningRequest, PlanningRequest
from app.common.entities import PlanningInput, RequestRecord
from app.common.enums import RequestMode
from app.services.interfaces.request_service import RequestService


def to_planning_input(body: PlanningRequest) -> PlanningInput:
    return PlanningInput(
        location=body.location, outing_date=body.outing_date, group_size=body.group_size,
        age_min=body.age_min, age_max=body.age_max, budget_inr=body.budget_inr,
        preferences=tuple(body.preferences),
    )


class RequestHandler:
    def __init__(self, service: RequestService) -> None:
        self._service = service

    async def handle_sync(self, body: PlanningRequest) -> RequestRecord:
        return await self._service.create_sync(to_planning_input(body))

    async def handle_async(self, body: AsyncPlanningRequest) -> RequestRecord:
        return await self._service.create_async(to_planning_input(body), str(body.callback_url))

    async def get(self, request_id: UUID) -> RequestRecord:
        return await self._service.get(request_id)

    async def list(self, mode: RequestMode, limit: int, cursor: str | None):
        return await self._service.list(mode, limit, cursor)
