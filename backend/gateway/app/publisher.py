import aio_pika
from fastapi import HTTPException, Request

from backend.shared.events import VEHICLE_CREATED, VehicleCreatedEvent


async def publish_vehicle_created(event: VehicleCreatedEvent, request: Request) -> None:
    try:
        exchange = request.app.state.exchange
        message = aio_pika.Message(
            body=event.model_dump_json().encode("utf-8"),
            content_type="application/json",
        )
        await exchange.publish(message, routing_key=VEHICLE_CREATED)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to publish vehicle created event: {e}",
        ) from e
