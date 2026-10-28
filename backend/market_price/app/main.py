from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[3] / ".env")

from backend.market_price.app.consumer import start_consumer  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("market-price")


async def main() -> None:
    """Listen for price requests until shutdown."""
    logger.info("MarketPrice starting...")
    connection = await start_consumer()
    logger.info("Waiting for vehicle.price.requested...")
    try:
        await asyncio.Future()
    finally:
        await connection.close()
        logger.info("MarketPrice stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted")
