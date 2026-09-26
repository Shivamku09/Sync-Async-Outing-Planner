import json

import aio_pika
from aio_pika import DeliveryMode, ExchangeType, Message

from app.broker.interface import MessageBroker, MessageHandler
from app.config.settings import RabbitMQSettings


class RabbitMQBroker(MessageBroker):
    EXCHANGE = "outing.commands"
    PLANNER_QUEUE = "planner.jobs"
    CALLBACK_QUEUE = "callback.jobs"

    def __init__(self, settings: RabbitMQSettings) -> None:
        self._settings = settings
        self._connection: aio_pika.abc.AbstractRobustConnection | None = None
        self._channel: aio_pika.abc.AbstractRobustChannel | None = None
        self._exchange: aio_pika.abc.AbstractExchange | None = None

    async def connect(self) -> None:
        self._connection = await aio_pika.connect_robust(self._settings.url)
        self._channel = await self._connection.channel(publisher_confirms=True)
        self._exchange = await self._channel.declare_exchange(self.EXCHANGE, ExchangeType.DIRECT, durable=True)
        planner = await self._channel.declare_queue(self.PLANNER_QUEUE, durable=True)
        callback = await self._channel.declare_queue(self.CALLBACK_QUEUE, durable=True)
        await planner.bind(self._exchange, "planner.requested")
        await callback.bind(self._exchange, "callback.requested")
        await self._channel.declare_queue("planner.dlq", durable=True)
        await self._channel.declare_queue("callback.dlq", durable=True)

    async def close(self) -> None:
        if self._connection:
            await self._connection.close()

    async def ping(self) -> bool:
        return bool(self._connection and not self._connection.is_closed)

    async def publish(self, routing_key: str, message_id: str, payload: dict[str, object]) -> None:
        if self._exchange is None:
            raise RuntimeError("RabbitMQ is not connected")
        message = Message(
            json.dumps(payload).encode(), content_type="application/json",
            delivery_mode=DeliveryMode.PERSISTENT, message_id=message_id,
        )
        await self._exchange.publish(message, routing_key=routing_key, mandatory=True)

    async def consume(self, queue_name: str, handler: MessageHandler) -> None:
        if self._channel is None:
            raise RuntimeError("RabbitMQ is not connected")
        prefetch = self._settings.planner_prefetch if queue_name == self.PLANNER_QUEUE else self._settings.callback_prefetch
        await self._channel.set_qos(prefetch_count=prefetch)
        queue = await self._channel.get_queue(queue_name)

        async def consume_message(message: aio_pika.abc.AbstractIncomingMessage) -> None:
            async with message.process(requeue=False):
                await handler(json.loads(message.body))

        await queue.consume(consume_message)
