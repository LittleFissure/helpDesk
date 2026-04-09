from __future__ import annotations

"""Helpers for validating and sanitising user-provided names."""

import re

HEX_PATTERN = re.compile(r"^#?[0-9a-fA-F]{6}$")
CHANNEL_INVALID_PATTERN = re.compile(r"[^a-z0-9-]+")
ROLE_SPACE_PATTERN = re.compile(r"\s+")


def normalise_hex_colour(value: str) -> str:
    """Validate a hex colour string and return it in #rrggbb form."""
    candidate = value.strip()
    if not HEX_PATTERN.fullmatch(candidate):
        raise ValueError("Please provide a valid 6-digit hex colour, for example `#ff66aa`.")

    if not candidate.startswith("#"):
        candidate = f"#{candidate}"

    return candidate.lower()


def sanitise_channel_name(value: str) -> str:
    """Convert user input into a Discord-safe channel name."""
    candidate = value.strip().lower().replace(" ", "-")
    candidate = CHANNEL_INVALID_PATTERN.sub("", candidate)
    candidate = re.sub(r"-{2,}", "-", candidate).strip("-")

    if not candidate:
        raise ValueError("That channel name is empty after cleanup.")
    if len(candidate) > 100:
        raise ValueError("Channel names must be 100 characters or fewer.")

    return candidate


def sanitise_role_name(value: str) -> str:
    """Clean a user-entered role name while preserving normal title-style text."""
    candidate = ROLE_SPACE_PATTERN.sub(" ", value.strip())

    if not candidate:
        raise ValueError("That role name is empty.")
    if len(candidate) > 100:
        raise ValueError("Role names must be 100 characters or fewer.")

    return candidate
