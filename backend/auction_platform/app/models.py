from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.gateway.app.db import Base
from backend.shared.schemas import AuctionListingStatus


class AuctionListing(Base):
    """Vehicles ready to be published for sale on the auction platform."""

    __tablename__ = "auction_listings"
    __table_args__ = (UniqueConstraint("vehicle_id", name="uq_auction_listings_vehicle_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vehicle_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    brand: Mapped[str] = mapped_column(String(100), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    mileage: Mapped[int] = mapped_column(Integer, nullable=False)
    color: Mapped[str | None] = mapped_column(String(50), nullable=True)
    body_type: Mapped[str] = mapped_column(String(50), nullable=False)
    predicted_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[AuctionListingStatus] = mapped_column(
        Enum(AuctionListingStatus, name="auction_listing_status", native_enum=False),
        nullable=False,
        default=AuctionListingStatus.READY_FOR_SALE,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
