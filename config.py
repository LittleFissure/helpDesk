"""Configuration loading for the Discord personal rooms bot."""

from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


def _parse_int_set(raw: str) -> set[int]:
    """Parse a comma-separated list of integer IDs."""
    values: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        values.add(int(part))
    return values


@dataclass(frozen=True)
class Settings:
    """Simple immutable settings container."""

    bot_token: str
    bot_admin_ids: set[int]


settings = Settings(
    bot_token=os.getenv("DISCORD_BOT_TOKEN", "").strip(),
    bot_admin_ids=_parse_int_set(os.getenv("BOT_ADMIN_IDS", "")),
)

if not settings.bot_token:
    raise RuntimeError("DISCORD_BOT_TOKEN is missing from the environment.")