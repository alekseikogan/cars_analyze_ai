from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

# Project root .env (cars_analyze_ai/.env)
load_dotenv(Path(__file__).resolve().parents[3] / ".env")

from backend.orchestrator.app.consumer import start_consumer  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("orchestrator")


async def main() -> None:
    logger.info("Orchestrator starting...")
    connection = await start_consumer()
    logger.info(
        "Orchestrator running. Listening for vehicle.created and vehicle.price.completed..."
    )
    try:
        await asyncio.Future()
    finally:
        await connection.close()
        logger.info("Orchestrator stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted")
