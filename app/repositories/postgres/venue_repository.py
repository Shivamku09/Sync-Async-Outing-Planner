from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.common.entities import Venue
from app.repositories.interfaces.venue_repository import VenueRepository
from app.repositories.postgres.mappers import venue_entity
from app.repositories.postgres.models import VenueRow


class PostgresVenueRepository(VenueRepository):
    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._session_factory = session_factory

    async def list_active(self) -> list[Venue]:
        async with self._session_factory() as session:
            rows = (await session.scalars(select(VenueRow).where(VenueRow.active.is_(True)))).all()
            return [venue_entity(row) for row in rows]
