import asyncio

from app.services.interfaces.outbox_service import OutboxService


class OutboxHandler:
    def __init__(self, service: OutboxService, poll_interval_seconds: float) -> None:
        self._service = service
        self._poll_interval = poll_interval_seconds

    async def run(self) -> None:
        while True:
            count = await self._service.publish_available_batch()
            if count == 0:
                await asyncio.sleep(self._poll_interval)
