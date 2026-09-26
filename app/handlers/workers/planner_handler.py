from app.broker.rabbitmq.messages import CommandMessage
from app.services.interfaces.planner_service import PlannerService


class PlannerHandler:
    def __init__(self, service: PlannerService) -> None:
        self._service = service

    async def handle(self, payload: dict[str, object]) -> None:
        message = CommandMessage.model_validate(payload)
        await self._service.process_async_request(message.request_id)
