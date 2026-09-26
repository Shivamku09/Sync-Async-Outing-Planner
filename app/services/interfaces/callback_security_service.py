from abc import ABC, abstractmethod


class CallbackSecurityService(ABC):
    @abstractmethod
    async def validate_destination(self, url: str) -> None: ...
