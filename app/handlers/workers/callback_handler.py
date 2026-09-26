from app.broker.rabbitmq.messages import CommandMessage
from app.services.interfaces.callback_service import CallbackService


class CallbackHandler:
    def __init__(self, service: CallbackService) -> None:
        self._service = service

    async def handle(self, payload: dict[str, object]) -> None:
        message = CommandMessage.model_validate(payload)
        completed = await self._service.deliver(message.request_id)
        if not completed:
            raise RuntimeError("callback requires retry")
