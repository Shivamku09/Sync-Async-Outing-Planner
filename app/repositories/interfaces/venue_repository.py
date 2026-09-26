from abc import ABC, abstractmethod

from app.common.entities import Venue


class VenueRepository(ABC):
    @abstractmethod
    async def list_active(self) -> list[Venue]: ...
