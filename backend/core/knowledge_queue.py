import json
from typing import Protocol

import aio_pika

from settings.config import get_settings


class KnowledgeTaskPublisher(Protocol):
    async def publish(self, task_id: int) -> None: ...


class RabbitKnowledgeTaskPublisher:
    async def publish(self, task_id: int) -> None:
        connection = await aio_pika.connect_robust(get_settings().rabbitmq_url)
        async with connection:
            channel = await connection.channel()
            queue = await channel.declare_queue("petmall.knowledge", durable=True)
            await channel.default_exchange.publish(
                aio_pika.Message(
                    body=json.dumps({"task_id": task_id}).encode(),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                ),
                routing_key=queue.name,
            )


def get_knowledge_task_publisher() -> KnowledgeTaskPublisher:
    return RabbitKnowledgeTaskPublisher()
