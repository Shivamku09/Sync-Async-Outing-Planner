import argparse
import asyncio

from app.broker.rabbitmq.connection import RabbitMQBroker
from app.config.settings import load_settings
from app.container import create_container


async def run(worker: str) -> None:
    container = create_container(load_settings())
    await container.broker.connect()
    try:
        if worker == "all":
            await container.broker.consume(RabbitMQBroker.PLANNER_QUEUE, container.planner_handler.handle)
            await container.broker.consume(RabbitMQBroker.CALLBACK_QUEUE, container.callback_handler.handle)
            await container.outbox_handler.run()
        elif worker == "planner":
            await container.broker.consume(RabbitMQBroker.PLANNER_QUEUE, container.planner_handler.handle)
        elif worker == "callback":
            await container.broker.consume(RabbitMQBroker.CALLBACK_QUEUE, container.callback_handler.handle)
        else:
            await container.outbox_handler.run()
        await asyncio.Future()
    finally:
        await container.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("worker", choices=["all", "planner", "callback", "outbox"])
    arguments = parser.parse_args()
    asyncio.run(run(arguments.worker))
