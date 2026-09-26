from dataclasses import dataclass

from app.broker.interface import MessageBroker
from app.broker.rabbitmq.connection import RabbitMQBroker
from app.config.settings import Settings
from app.handlers.http.health_handler import HealthHandler
from app.handlers.http.request_handler import RequestHandler
from app.handlers.workers.callback_handler import CallbackHandler
from app.handlers.workers.outbox_handler import OutboxHandler
from app.handlers.workers.planner_handler import PlannerHandler
from app.repositories.postgres.callback_repository import PostgresCallbackRepository
from app.repositories.postgres.database import Database
from app.repositories.postgres.outbox_repository import PostgresOutboxRepository
from app.repositories.postgres.request_repository import PostgresRequestRepository
from app.repositories.postgres.venue_repository import PostgresVenueRepository
from app.services.implementations.callback_security_service import DefaultCallbackSecurityService
from app.services.implementations.callback_service import DefaultCallbackService
from app.services.implementations.outbox_service import DefaultOutboxService
from app.services.implementations.planner_service import DefaultPlannerService
from app.services.implementations.request_service import DefaultRequestService
from app.utils.http_api_client import HTTPAPIClient, HttpxAPIClient


@dataclass(slots=True)
class ApplicationContainer:
    settings: Settings
    database: Database
    broker: MessageBroker
    http_api_client: HTTPAPIClient
    request_handler: RequestHandler
    health_handler: HealthHandler
    planner_handler: PlannerHandler
    callback_handler: CallbackHandler
    outbox_handler: OutboxHandler

    async def close(self) -> None:
        await self.http_api_client.close()
        await self.broker.close()
        await self.database.close()


def create_container(settings: Settings) -> ApplicationContainer:
    database = Database(settings.database)
    broker = RabbitMQBroker(settings.rabbitmq)
    http_api_client = HttpxAPIClient(settings.callback)

    request_repository = PostgresRequestRepository(database.session_factory)
    venue_repository = PostgresVenueRepository(database.session_factory)
    callback_repository = PostgresCallbackRepository(database.session_factory)
    outbox_repository = PostgresOutboxRepository(database.session_factory)

    callback_security = DefaultCallbackSecurityService(settings.callback.allow_localhost)
    planner_service = DefaultPlannerService(venue_repository, request_repository)
    request_service = DefaultRequestService(
        request_repository, planner_service, callback_security, settings.api.async_backlog_limit,
    )
    callback_service = DefaultCallbackService(callback_repository, callback_security, http_api_client)
    outbox_service = DefaultOutboxService(outbox_repository, broker, settings.outbox.batch_size)

    return ApplicationContainer(
        settings=settings,
        database=database,
        broker=broker,
        http_api_client=http_api_client,
        request_handler=RequestHandler(request_service),
        health_handler=HealthHandler(database, broker),
        planner_handler=PlannerHandler(planner_service),
        callback_handler=CallbackHandler(callback_service),
        outbox_handler=OutboxHandler(outbox_service, settings.outbox.poll_interval_seconds),
    )
