import asyncio
import json

import aio_pika

from core.rag_service import get_vector_service
from models.database import AsyncSessionLocal
from services.knowledge_service import process_knowledge_task
from settings.config import get_settings


async def main() -> None:
    connection = await aio_pika.connect_robust(get_settings().rabbitmq_url)
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=1)
    queue = await channel.declare_queue("petmall.knowledge", durable=True)
    vectors = get_vector_service()

    async with queue.iterator() as messages:
        async for message in messages:
            async with message.process(requeue=True):
                task_id = int(json.loads(message.body)["task_id"])
                async with AsyncSessionLocal() as db:
                    await process_knowledge_task(db, task_id, vectors)


if __name__ == "__main__":
    asyncio.run(main())
