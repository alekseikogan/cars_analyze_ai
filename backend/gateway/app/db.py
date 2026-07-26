import os
from collections.abc import Generator
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# Project root: cars_analyze_ai/.env
load_dotenv(Path(__file__).resolve().parents[3] / ".env")

DATABASE_URL = os.getenv(
    "POSTGRES_URL",
    "postgresql+psycopg2://admin:secret@localhost:5433/car_auction",
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    # Import models so they register on Base.metadata
    from backend.gateway.app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
