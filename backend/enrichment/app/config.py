import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[3] / ".env")


def get_openai_api_key() -> str:
    """Read OPENAI_API_KEY from the environment."""
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Add it to the project root .env file."
        )
    return key


def get_openai_model() -> str:
    """Read OPENAI_MODEL, defaulting to gpt-4o-mini."""
    return os.getenv("OPENAI_MODEL", "gpt-4o-mini")
