from abc import ABC, abstractmethod


class OutboxService(ABC):
    @abstractmethod
    async def publish_available_batch(self) -> int: ...
