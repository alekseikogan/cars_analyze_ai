from __future__ import annotations

import logging

import aio_pika
from aio_pika.abc import AbstractExchange
from pydantic import BaseModel

logger = logging.getLogger(__name__)


async def publish_event(
    exchange: AbstractExchange,
    routing_key: str,
    event: BaseModel,
) -> None:
    """Publish a JSON event to the vehicle exchange."""
    message = aio_pika.Message(
        body=event.model_dump_json().encode("utf-8"),
        content_type="application/json",
    )
    await exchange.publish(message, routing_key=routing_key)
    logger.info("published %s payload=%s", routing_key, event.model_dump())
