from __future__ import annotations

import logging
import os

import aio_pika
from aio_pika.abc import AbstractIncomingMessage

from backend.orchestrator.app.handlers import process_vehicle_created
from backend.shared.events import (
    VEHICLE_CREATED,
    VEHICLE_CREATED_QUEUE,
    VEHICLE_EXCHANGE,
    VehicleCreatedEvent,
)

logger = logging.getLogger(__name__)


async def _on_message(message: AbstractIncomingMessage) -> None:
    async with message.process(requeue=False):
        try:
            event = VehicleCreatedEvent.model_validate_json(message.body)
        except Exception:
            logger.exception("skip invalid message: %r", message.body[:200])
            return
        process_vehicle_created(event)


async def start_consumer() -> aio_pika.RobustConnection:
    url = os.getenv("RABBITMQ_URL")
    if not url:
        raise RuntimeError("RABBITMQ_URL is not set")

    connection = await aio_pika.connect_robust(url)
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=1)

    exchange = await channel.declare_exchange(
        name=VEHICLE_EXCHANGE,
        type=aio_pika.ExchangeType.TOPIC,
    )
    queue = await channel.declare_queue(name=VEHICLE_CREATED_QUEUE)
    await queue.bind(exchange, routing_key=VEHICLE_CREATED)

    await queue.consume(_on_message)
    logger.info(
        "consuming queue=%s exchange=%s routing_key=%s",
        VEHICLE_CREATED_QUEUE,
        VEHICLE_EXCHANGE,
        VEHICLE_CREATED,
    )
    return connection
