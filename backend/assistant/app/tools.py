from __future__ import annotations

import json
import os

from langchain_core.tools import tool
from sqlalchemy import select

from backend.auction_platform.app.models import AuctionListing
from backend.gateway.app.db import SessionLocal
from backend.gateway.app.models import Vehicle
from backend.ml_service.app.predictor import predict
from backend.shared.schemas import AuctionListingStatus, PricePredictRequest


def _dumps(payload: object) -> str:
    """Сериализует ответ инструмента в JSON с русскими буквами."""
    return json.dumps(payload, ensure_ascii=False)


def _status_label(status: AuctionListingStatus | str) -> str:
    """Переводит статус лота в «доступно» или «забронировано»."""
    value = status.value if isinstance(status, AuctionListingStatus) else str(status)
    if value == AuctionListingStatus.LISTED.value:
        return "забронировано"
    if value == AuctionListingStatus.READY_FOR_SALE.value:
        return "доступно"
    return value


def _listing_payload(row: AuctionListing) -> dict:
    """Собирает поля лота, которые модель может процитировать."""
    return {
        "listing_id": row.id,
        "vehicle_id": row.vehicle_id,
        "brand": row.brand,
        "model": row.model,
        "year": row.year,
        "mileage": row.mileage,
        "color": row.color,
        "body_type": row.body_type,
        "predicted_price_eur": row.predicted_price,
        "confidence": row.confidence,
        "status": _status_label(row.status),
    }


@tool
def search_listings(
    brand: str = "",
    model: str = "",
    year: int = 0,
    body_type: str = "",
    status: str = "",
    limit: int = 8,
) -> str:
    """Ищет лоты по марке, модели, году, кузову и статусу.

    Неизвестный фильтр передавай пустой строкой, год — нулём.
    status: «доступно», «забронировано» или пустая строка, если статус не важен.
    """
    take = min(max(limit, 1), 10)
    db = SessionLocal()
    try:
        stmt = select(AuctionListing).order_by(AuctionListing.created_at.desc())
        if brand.strip():
            stmt = stmt.where(AuctionListing.brand.ilike(f"%{brand.strip()}%"))
        if model.strip():
            stmt = stmt.where(AuctionListing.model.ilike(f"%{model.strip()}%"))
        if year:
            stmt = stmt.where(AuctionListing.year == year)
        if body_type.strip():
            stmt = stmt.where(AuctionListing.body_type.ilike(f"%{body_type.strip()}%"))
        if status.strip() in {"доступно", "available", "ready"}:
            stmt = stmt.where(AuctionListing.status == AuctionListingStatus.READY_FOR_SALE)
        elif status.strip() in {"забронировано", "reserved", "listed"}:
            stmt = stmt.where(AuctionListing.status == AuctionListingStatus.LISTED)
        rows = list(db.scalars(stmt.limit(take)))
        return _dumps({"count": len(rows), "listings": [_listing_payload(row) for row in rows]})
    finally:
        db.close()


@tool
def get_listing(listing_id: int) -> str:
    """Возвращает один лот по listing_id: цена, пробег и статус."""
    db = SessionLocal()
    try:
        row = db.get(AuctionListing, listing_id)
        if row is None:
            return _dumps({"error": f"Лот {listing_id} не найден"})
        return _dumps(_listing_payload(row))
    finally:
        db.close()


@tool
def get_vehicle(vehicle_id: int) -> str:
    """Возвращает карточку машины по vehicle_id: марка, модель, год, пробег и статус."""
    db = SessionLocal()
    try:
        row = db.get(Vehicle, vehicle_id)
        if row is None:
            return _dumps({"error": f"Авто {vehicle_id} не найдено"})
        status = row.status.value if hasattr(row.status, "value") else str(row.status)
        return _dumps(
            {
                "vehicle_id": row.id,
                "brand": row.brand,
                "model": row.model,
                "year": row.year,
                "mileage": row.mileage,
                "color": row.color,
                "body_type": row.body_type,
                "status": status,
            }
        )
    finally:
        db.close()


@tool
def estimate_price(
    brand: str,
    model: str,
    year: int,
    mileage: int,
    body_type: str,
    color: str = "",
) -> str:
    """Считает цену в евро той же формулой, что и ML-сервис.

    Вызывай, когда машины ещё нет в каталоге аукциона.
    """
    result = predict(
        PricePredictRequest(
            vehicle_id=0,
            brand=brand,
            model=model,
            year=year,
            mileage=mileage,
            color=color or None,
            body_type=body_type,
        )
    )
    return _dumps(
        {
            "brand": brand,
            "model": model,
            "year": year,
            "mileage": mileage,
            "body_type": body_type,
            "predicted_price_eur": result.predicted_price,
            "confidence": result.confidence,
        }
    )


@tool
def reserve_listing(listing_id: int) -> str:
    """Бронирует доступный лот. Вызывай только если менеджер явно просит забронировать этот listing_id."""
    db = SessionLocal()
    try:
        row = db.get(AuctionListing, listing_id)
        if row is None:
            return _dumps({"error": f"Лот {listing_id} не найден"})
        if row.status != AuctionListingStatus.READY_FOR_SALE:
            return _dumps(
                {
                    "error": "Лот уже нельзя забронировать",
                    "listing": _listing_payload(row),
                }
            )
        row.status = AuctionListingStatus.LISTED
        db.commit()
        db.refresh(row)
        return _dumps({"message": "Лот забронирован", "listing": _listing_payload(row)})
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@tool
def get_enrichment(vehicle_id: int) -> str:
    """Читает сохранённое описание машины: комплектация, опции, сегмент и краткий текст."""
    url = os.getenv("MONGO_URL", "").strip()
    if not url:
        return _dumps({"vehicle_id": vehicle_id, "enrichment": None, "note": "Mongo is not configured"})
    try:
        from pymongo import MongoClient

        client = MongoClient(url, serverSelectionTimeoutMS=1500)
        try:
            database = client[os.getenv("MONGO_DB", "car_auction")]
            doc = database["saga_history"].find_one(
                {"vehicle_id": vehicle_id},
                sort=[("archived_at", -1)],
            )
        finally:
            client.close()
    except Exception as exc:
        return _dumps({"vehicle_id": vehicle_id, "enrichment": None, "note": str(exc)})

    enrichment = (doc or {}).get("enrichment") or None
    if not enrichment:
        return _dumps(
            {
                "vehicle_id": vehicle_id,
                "enrichment": None,
                "note": "Описание для этой машины ещё не сохранено",
            }
        )
    return _dumps(
        {
            "vehicle_id": vehicle_id,
            "likely_trim": enrichment.get("likely_trim"),
            "likely_options": enrichment.get("likely_options"),
            "condition_notes": enrichment.get("condition_notes"),
            "market_segment": enrichment.get("market_segment"),
            "summary": enrichment.get("summary"),
        }
    )


READ_TOOLS = [search_listings, get_listing, get_vehicle, estimate_price, get_enrichment]
MANAGER_TOOLS = [*READ_TOOLS, reserve_listing]
