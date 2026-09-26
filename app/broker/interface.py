from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable

MessageHandler = Callable[[dict[str, object]], Awaitable[None]]


class MessageBroker(ABC):
    @abstractmethod
    async def connect(self) -> None: ...

    @abstractmethod
    async def close(self) -> None: ...

    @abstractmethod
    async def ping(self) -> bool: ...

    @abstractmethod
    async def publish(self, routing_key: str, message_id: str, payload: dict[str, object]) -> None: ...

    @abstractmethod
    async def consume(self, queue_name: str, handler: MessageHandler) -> None: ...
