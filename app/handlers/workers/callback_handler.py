from app.broker.errors import DeadLetterMessageError, RetryMessageError
from app.broker.rabbitmq.messages import CommandMessage
from app.services.interfaces.callback_service import CallbackDeliveryAction, CallbackService


class CallbackHandler:
    def __init__(self, service: CallbackService) -> None:
        self._service = service

    async def handle(self, payload: dict[str, object]) -> None:
        message = CommandMessage.model_validate(payload)
        decision = await self._service.deliver(message.request_id)
        if decision.action == CallbackDeliveryAction.RETRY:
            raise RetryMessageError(decision.attempt)
        if decision.action == CallbackDeliveryAction.DEAD_LETTER:
            raise DeadLetterMessageError(str(message.request_id))
