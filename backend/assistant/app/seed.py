from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, text

from backend.assistant.app.models import User
from backend.auction_platform.app.models import AuctionListing
from backend.gateway.app.db import SessionLocal
from backend.gateway.app.models import Vehicle
from backend.ml_service.app.predictor import predict
from backend.shared.schemas import AuctionListingStatus, PricePredictRequest, VehicleStatus
from backend.shared.security import hash_password

# 50 разных машин. Год, пробег и цвет считаются от номера, чтобы набор не повторялся.
CATALOG: list[tuple[str, str, str]] = [
    ("Toyota", "Camry", "Sedan"),
    ("Toyota", "Corolla", "Hatchback"),
    ("Toyota", "RAV4", "SUV"),
    ("Toyota", "Yaris", "Hatchback"),
    ("Toyota", "Hilux", "Pickup"),
    ("Toyota", "Land Cruiser", "SUV"),
    ("BMW", "3 Series", "Sedan"),
    ("BMW", "5 Series", "Sedan"),
    ("BMW", "X3", "SUV"),
    ("BMW", "X5", "SUV"),
    ("BMW", "1 Series", "Hatchback"),
    ("Mercedes", "C-Class", "Sedan"),
    ("Mercedes", "E-Class", "Sedan"),
    ("Mercedes", "A-Class", "Hatchback"),
    ("Mercedes", "GLC", "SUV"),
    ("Mercedes", "GLE", "SUV"),
    ("Audi", "A3", "Hatchback"),
    ("Audi", "A4", "Sedan"),
    ("Audi", "A6", "Sedan"),
    ("Audi", "Q3", "SUV"),
    ("Audi", "Q5", "SUV"),
    ("Volkswagen", "Golf", "Hatchback"),
    ("Volkswagen", "Passat", "Wagon"),
    ("Volkswagen", "Tiguan", "SUV"),
    ("Volkswagen", "Polo", "Hatchback"),
    ("Volkswagen", "Touareg", "SUV"),
    ("Ford", "Focus", "Hatchback"),
    ("Ford", "Fiesta", "Hatchback"),
    ("Ford", "Mondeo", "Sedan"),
    ("Ford", "Kuga", "SUV"),
    ("Ford", "Mustang", "Coupe"),
    ("Renault", "Clio", "Hatchback"),
    ("Renault", "Megane", "Hatchback"),
    ("Renault", "Captur", "SUV"),
    ("Renault", "Kadjar", "SUV"),
    ("Renault", "Scenic", "Van"),
    ("Peugeot", "208", "Hatchback"),
    ("Peugeot", "308", "Hatchback"),
    ("Peugeot", "3008", "SUV"),
    ("Peugeot", "5008", "SUV"),
    ("Peugeot", "2008", "SUV"),
    ("Volvo", "XC40", "SUV"),
    ("Volvo", "XC60", "SUV"),
    ("Volvo", "XC90", "SUV"),
    ("Volvo", "V60", "Wagon"),
    ("Volvo", "S60", "Sedan"),
    ("Hyundai", "Tucson", "SUV"),
    ("Hyundai", "Santa Fe", "SUV"),
    ("Kia", "Sportage", "SUV"),
    ("Mazda", "MX-5", "Convertible"),
]

COLORS = ["Black", "White", "Silver", "Gray", "Blue", "Red", "Green", "Beige"]

DEMO_USERS = (
    ("support", "support123", "support"),
    ("manager", "manager123", "auction_manager"),
)


def _specs() -> list[dict]:
    rows = []
    for index, (brand, model, body) in enumerate(CATALOG):
        rows.append(
            {
                "brand": brand,
                "model": model,
                "body_type": body,
                "year": 2015 + (index % 10),
                "mileage": 22000 + (index * 6150) % 140000,
                "color": COLORS[index % len(COLORS)],
                "listed": index % 9 == 0,
            }
        )
    return rows


def seed_demo_data() -> None:
    """Создаёт двух сотрудников и доводит auction_listings до 50 разных машин."""
    db = SessionLocal()
    try:
        db.execute(text("SELECT pg_advisory_xact_lock(845221)"))

        for login, password, role in DEMO_USERS:
            exists = db.scalar(select(User.id).where(User.login == login))
            if exists is None:
                db.add(
                    User(
                        login=login,
                        password_hash=hash_password(password),
                        role=role,
                    )
                )

        count = db.scalar(select(func.count()).select_from(AuctionListing)) or 0
        now = datetime.now(timezone.utc)
        for index, spec in enumerate(_specs()):
            if count >= 50:
                break
            already = db.scalar(
                select(AuctionListing.id).where(
                    AuctionListing.brand == spec["brand"],
                    AuctionListing.model == spec["model"],
                    AuctionListing.year == spec["year"],
                    AuctionListing.mileage == spec["mileage"],
                )
            )
            if already is not None:
                continue

            vehicle = Vehicle(
                brand=spec["brand"],
                model=spec["model"],
                year=spec["year"],
                mileage=spec["mileage"],
                color=spec["color"],
                body_type=spec["body_type"],
                status=VehicleStatus.READY,
                created_at=now - timedelta(days=50 - index),
            )
            db.add(vehicle)
            db.flush()

            price = predict(
                PricePredictRequest(
                    vehicle_id=vehicle.id,
                    brand=spec["brand"],
                    model=spec["model"],
                    year=spec["year"],
                    mileage=spec["mileage"],
                    color=spec["color"],
                    body_type=spec["body_type"],
                )
            )
            db.add(
                AuctionListing(
                    vehicle_id=vehicle.id,
                    brand=spec["brand"],
                    model=spec["model"],
                    year=spec["year"],
                    mileage=spec["mileage"],
                    color=spec["color"],
                    body_type=spec["body_type"],
                    predicted_price=price.predicted_price,
                    confidence=price.confidence,
                    status=(
                        AuctionListingStatus.LISTED
                        if spec["listed"]
                        else AuctionListingStatus.READY_FOR_SALE
                    ),
                    created_at=vehicle.created_at,
                )
            )
            count += 1

        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
