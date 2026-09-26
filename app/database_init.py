import asyncio
from pathlib import Path
from uuid import UUID

import yaml
from sqlalchemy.dialects.postgresql import insert

from app.config.settings import load_settings
from app.repositories.postgres.database import Database
from app.repositories.postgres.models import Base, VenueRow


SEED_FILE = Path(__file__).parent / "config" / "venues.yaml"


async def initialize() -> None:
    database = Database(load_settings().database)
    try:
        async with database.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        venues = yaml.safe_load(SEED_FILE.read_text(encoding="utf-8"))["venues"]
        rows = [{**venue, "id": UUID(venue["id"])} for venue in venues]
        async with database.session_factory() as session, session.begin():
            await session.execute(insert(VenueRow).values(rows).on_conflict_do_nothing(index_elements=["id"]))
    finally:
        await database.close()


if __name__ == "__main__":
    asyncio.run(initialize())
