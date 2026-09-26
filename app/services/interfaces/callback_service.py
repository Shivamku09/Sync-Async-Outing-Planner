from abc import ABC, abstractmethod
from enum import StrEnum
from uuid import UUID


class CallbackDeliveryAction(StrEnum):
    COMPLETE = "complete"
    RETRY = "retry"
    DEAD_LETTER = "dead_letter"


class CallbackDeliveryDecision:
    def __init__(self, action: CallbackDeliveryAction, attempt: int) -> None:
        self.action = action
        self.attempt = attempt


class CallbackService(ABC):
    @abstractmethod
    async def deliver(self, request_id: UUID) -> CallbackDeliveryDecision: ...
