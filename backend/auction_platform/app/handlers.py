from __future__ import annotations

import logging

from sqlalchemy.dialects.postgresql import insert

from backend.auction_platform.app.models import AuctionListing
from backend.gateway.app.db import SessionLocal
from backend.gateway.app.models import Vehicle
from backend.shared.events import VehicleProcessingCompletedEvent
from backend.shared.schemas import AuctionListingStatus

logger = logging.getLogger(__name__)


def create_listing_from_event(event: VehicleProcessingCompletedEvent) -> AuctionListing:
    """Insert or update the auction listing for a vehicle that finished processing."""
    db = SessionLocal()
    try:
        vehicle = db.get(Vehicle, event.vehicle_id)
        if vehicle is None:
            raise ValueError(f"Vehicle {event.vehicle_id} not found")

        stmt = (
            insert(AuctionListing)
            .values(
                vehicle_id=vehicle.id,
                brand=vehicle.brand,
                model=vehicle.model,
                year=vehicle.year,
                mileage=vehicle.mileage,
                color=vehicle.color,
                body_type=vehicle.body_type,
                predicted_price=event.predicted_price,
                confidence=event.confidence,
                status=AuctionListingStatus.READY_FOR_SALE,
            )
            .on_conflict_do_update(
                index_elements=["vehicle_id"],
                set_={
                    "brand": vehicle.brand,
                    "model": vehicle.model,
                    "year": vehicle.year,
                    "mileage": vehicle.mileage,
                    "color": vehicle.color,
                    "body_type": vehicle.body_type,
                    "predicted_price": event.predicted_price,
                    "confidence": event.confidence,
                    "status": AuctionListingStatus.READY_FOR_SALE,
                },
            )
            .returning(AuctionListing.id)
        )
        result = db.execute(stmt)
        listing_id = result.scalar_one()
        db.commit()
        logger.info(
            "auction listing ready vehicle_id=%s listing_id=%s price=%s",
            event.vehicle_id,
            listing_id,
            event.predicted_price,
        )
        listing = db.get(AuctionListing, listing_id)
        assert listing is not None
        return listing
    finally:
        db.close()


async def process_processing_completed(event: VehicleProcessingCompletedEvent) -> None:
    """Handle vehicle.processing.completed by creating the auction listing."""
    logger.info(
        "auction received processing.completed vehicle_id=%s price=%s",
        event.vehicle_id,
        event.predicted_price,
    )
    create_listing_from_event(event)
