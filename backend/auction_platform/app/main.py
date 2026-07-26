from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[3] / ".env")

from backend.auction_platform.app.consumer import start_consumer  # noqa: E402
from backend.gateway.app.db import Base, engine  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("auction-platform")


def init_tables() -> None:
    from backend.auction_platform.app import models  # noqa: F401
    from backend.gateway.app import models as gateway_models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    logger.info("auction_listings table ready")


async def main() -> None:
    logger.info("Auction platform starting...")
    init_tables()
    connection = await start_consumer()
    logger.info("Waiting for vehicle.processing.completed...")
    try:
        await asyncio.Future()
    finally:
        await connection.close()
        logger.info("Auction platform stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted")
