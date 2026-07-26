from __future__ import annotations

import logging
import os

import aio_pika
from aio_pika.abc import AbstractIncomingMessage

from backend.orchestrator.app.handlers import (
    process_price_completed,
    process_vehicle_created,
)
from backend.shared.events import (
    VEHICLE_CREATED,
    VEHICLE_CREATED_QUEUE,
    VEHICLE_EXCHANGE,
    VEHICLE_PRICE_COMPLETED,
    VEHICLE_PRICE_COMPLETED_QUEUE,
    VehicleCreatedEvent,
    VehiclePriceCompletedEvent,
)

logger = logging.getLogger(__name__)


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

    created_queue = await channel.declare_queue(name=VEHICLE_CREATED_QUEUE)
    await created_queue.bind(exchange, routing_key=VEHICLE_CREATED)

    price_done_queue = await channel.declare_queue(name=VEHICLE_PRICE_COMPLETED_QUEUE)
    await price_done_queue.bind(exchange, routing_key=VEHICLE_PRICE_COMPLETED)

    async def _on_created(message: AbstractIncomingMessage) -> None:
        async with message.process(requeue=False):
            try:
                event = VehicleCreatedEvent.model_validate_json(message.body)
            except Exception:
                logger.exception("skip invalid created message: %r", message.body[:200])
                return
            await process_vehicle_created(event, exchange)

    async def _on_price_completed(message: AbstractIncomingMessage) -> None:
        async with message.process(requeue=False):
            try:
                event = VehiclePriceCompletedEvent.model_validate_json(message.body)
            except Exception:
                logger.exception("skip invalid price.completed: %r", message.body[:200])
                return
            await process_price_completed(event, exchange)

    await created_queue.consume(_on_created)
    await price_done_queue.consume(_on_price_completed)

    logger.info(
        "consuming queues=%s,%s",
        VEHICLE_CREATED_QUEUE,
        VEHICLE_PRICE_COMPLETED_QUEUE,
    )
    return connection
