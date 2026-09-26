from app.broker.interface import MessageBroker
from app.common.enums import OutboxEventType
from app.repositories.interfaces.outbox_repository import OutboxRepository
from app.services.interfaces.outbox_service import OutboxService


class DefaultOutboxService(OutboxService):
    def __init__(self, repository: OutboxRepository, broker: MessageBroker, batch_size: int) -> None:
        self._repository = repository
        self._broker = broker
        self._batch_size = batch_size

    async def publish_available_batch(self) -> int:
        events = await self._repository.claim_available(self._batch_size)
        published = 0
        for event in events:
            routing_key = "planner.requested" if event.event_type == OutboxEventType.PLAN_REQUESTED else "callback.requested"
            payload = {
                **event.payload,
                "event_id": str(event.id),
                "event_type": event.event_type.value,
                "attempt": event.publish_attempts,
            }
            try:
                await self._broker.publish(routing_key, str(event.id), payload)
                await self._repository.mark_published(event.id)
                published += 1
            except Exception as exc:
                await self._repository.release_failed(event.id, type(exc).__name__)
        return published
