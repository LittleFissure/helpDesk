from __future__ import annotations

"""Configuration loading for the multi-server Discord personal rooms bot."""

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


def _get_optional_int(name):
    value = os.getenv(name, "").strip()
    return int(value) if value else None


@dataclass(frozen=True)
class Settings:
    """Simple immutable settings container."""

    bot_token: str
    log_channel_id: Optional[int]


settings = Settings(
    bot_token=os.getenv("DISCORD_BOT_TOKEN", "").strip(),
    log_channel_id=_get_optional_int("LOG_CHANNEL_ID"),
)

if not settings.bot_token:
    raise RuntimeError("DISCORD_BOT_TOKEN is missing from the environment.")
