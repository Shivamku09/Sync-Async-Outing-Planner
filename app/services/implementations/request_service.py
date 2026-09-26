from uuid import UUID

from app.common.entities import PlanningInput, RequestRecord
from app.common.enums import RequestMode
from app.common.exceptions import AsyncBacklogExceededError, RequestNotFoundError
from app.repositories.interfaces.request_repository import RequestRepository
from app.services.interfaces.callback_security_service import CallbackSecurityService
from app.services.interfaces.planner_service import PlannerService
from app.services.interfaces.request_service import RequestService


class DefaultRequestService(RequestService):
    def __init__(
        self,
        request_repository: RequestRepository,
        planner_service: PlannerService,
        callback_security_service: CallbackSecurityService,
        async_backlog_limit: int,
    ) -> None:
        self._requests = request_repository
        self._planner = planner_service
        self._callback_security = callback_security_service
        self._async_backlog_limit = async_backlog_limit

    async def create_sync(self, planning_input: PlanningInput) -> RequestRecord:
        request = await self._requests.create_sync(planning_input)
        outcome = await self._planner.plan(planning_input)
        return await self._requests.complete(request.id, outcome, create_callback_event=False)

    async def create_async(self, planning_input: PlanningInput, callback_url: str) -> RequestRecord:
        await self._callback_security.validate_destination(callback_url)
        if await self._requests.count_async_backlog() >= self._async_backlog_limit:
            raise AsyncBacklogExceededError()
        return await self._requests.create_async(planning_input, callback_url)

    async def get(self, request_id: UUID) -> RequestRecord:
        request = await self._requests.get(request_id)
        if request is None:
            raise RequestNotFoundError()
        return request

    async def list(self, mode: RequestMode, limit: int, cursor: str | None) -> tuple[list[RequestRecord], str | None]:
        return await self._requests.list(mode, limit, cursor)
