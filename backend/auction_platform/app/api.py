from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.auction_platform.app.models import AuctionListing
from backend.assistant.app.seed import seed_demo_data
from backend.gateway.app.db import Base, engine, get_db
from backend.shared.security import decode_token
from backend.shared.schemas import (
    AuctionListingRead,
    AuctionListingStatus,
    ReserveListingResponse,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Создаёт таблицы аукциона и авто до приёма запросов."""
    from backend.auction_platform.app import models as auction_models  # noqa: F401
    from backend.gateway.app import models as gateway_models  # noqa: F401
    from backend.assistant.app import models as assistant_models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    seed_demo_data()
    yield


app = FastAPI(title="Auction Platform API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost",
        "http://127.0.0.1",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/listings", response_model=list[AuctionListingRead])
def list_listings(db: Session = Depends(get_db)):
    """Возвращает карточки, готовые к продаже или уже зарезервированные, сначала новые."""
    result = db.execute(
        select(AuctionListing)
        .where(
            AuctionListing.status.in_(
                [
                    AuctionListingStatus.READY_FOR_SALE,
                    AuctionListingStatus.LISTED,
                ]
            )
        )
        .order_by(AuctionListing.created_at.desc())
    )
    return list(result.scalars().all())


@app.get("/listings/by-vehicle/{vehicle_id}", response_model=AuctionListingRead)
def get_listing_by_vehicle(vehicle_id: int, db: Session = Depends(get_db)):
    """Возвращает карточку аукциона по авто или 404, если её ещё нет."""
    result = db.execute(
        select(AuctionListing).where(AuctionListing.vehicle_id == vehicle_id)
    )
    listing = result.scalar_one_or_none()
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found for vehicle")
    return listing


@app.get("/listings/{listing_id}", response_model=AuctionListingRead)
def get_listing(listing_id: int, db: Session = Depends(get_db)):
    """Возвращает одну карточку аукциона по id."""
    listing = db.get(AuctionListing, listing_id)
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing


def _require_auction_manager(authorization: str | None = Header(default=None)) -> dict:
    """Пускает к брони только менеджера аукциона."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Войдите как менеджер аукциона")
    payload = decode_token(authorization.split(" ", 1)[1].strip())
    if payload.get("role") != "auction_manager":
        raise HTTPException(status_code=403, detail="Бронировать может только менеджер аукциона")
    return payload


@app.post("/listings/{listing_id}/reserve", response_model=ReserveListingResponse)
def reserve_listing(
    listing_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(_require_auction_manager),
):
    """Резервирует готовую карточку, переводя её в статус listed."""
    listing = db.get(AuctionListing, listing_id)
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.status != AuctionListingStatus.READY_FOR_SALE:
        raise HTTPException(
            status_code=400,
            detail="Listing is not available for reservation",
        )

    listing.status = AuctionListingStatus.LISTED
    db.commit()
    db.refresh(listing)

    return ReserveListingResponse(
        message="Вы успешно забронировали авто",
        listing=listing,
    )
