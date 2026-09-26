from app.broker.interface import MessageBroker
from app.repositories.postgres.database import Database


class HealthHandler:
    def __init__(self, database: Database, broker: MessageBroker) -> None:
        self._database = database
        self._broker = broker

    async def check(self) -> dict[str, str]:
        await self._database.ping()
        rabbitmq = "up" if await self._broker.ping() else "down"
        return {"status": "healthy", "postgresql": "up", "rabbitmq": rabbitmq}
