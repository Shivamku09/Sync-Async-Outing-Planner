from abc import ABC, abstractmethod
from uuid import UUID


class CallbackService(ABC):
    @abstractmethod
    async def deliver(self, request_id: UUID) -> bool: ...
