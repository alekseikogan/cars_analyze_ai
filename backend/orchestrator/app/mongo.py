from __future__ import annotations

import logging
import os

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


async def connect_mongo() -> AsyncIOMotorDatabase:
    global _client, _db

    url = os.getenv("MONGO_URL")
    if not url:
        raise RuntimeError("MONGO_URL is not set")

    db_name = os.getenv("MONGO_DB", "car_auction")
    _client = AsyncIOMotorClient(url)
    _db = _client[db_name]
    await _client.admin.command("ping")
    logger.info("MongoDB connected db=%s", db_name)
    return _db


async def close_mongo() -> None:
    global _client, _db
    if _client is not None:
        _client.close()
        logger.info("MongoDB connection closed")
    _client = None
    _db = None


def get_db() -> AsyncIOMotorDatabase:
    if _db is None:
        raise RuntimeError("MongoDB is not connected. Call connect_mongo() first.")
    return _db
