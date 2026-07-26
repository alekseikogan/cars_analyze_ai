from __future__ import annotations

import logging
import os

import aio_pika
from aio_pika.abc import AbstractIncomingMessage

from backend.market_price.app.handlers import process_price_requested
from backend.shared.events import (
    VEHICLE_EXCHANGE,
    VEHICLE_PRICE_REQUESTED,
    VEHICLE_PRICE_REQUESTED_QUEUE,
    VehiclePriceRequestedEvent,
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
    queue = await channel.declare_queue(name=VEHICLE_PRICE_REQUESTED_QUEUE)
    await queue.bind(exchange, routing_key=VEHICLE_PRICE_REQUESTED)

    async def _on_message(message: AbstractIncomingMessage) -> None:
        async with message.process(requeue=False):
            try:
                event = VehiclePriceRequestedEvent.model_validate_json(message.body)
            except Exception:
                logger.exception("skip invalid message: %r", message.body[:200])
                return
            try:
                await process_price_requested(event, exchange)
            except Exception:
                logger.exception(
                    "market-price failed vehicle_id=%s",
                    getattr(event, "vehicle_id", "?"),
                )
                raise

    await queue.consume(_on_message)
    logger.info(
        "consuming queue=%s routing_key=%s",
        VEHICLE_PRICE_REQUESTED_QUEUE,
        VEHICLE_PRICE_REQUESTED,
    )
    return connection
