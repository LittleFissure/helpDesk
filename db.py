"""SQLite persistence helpers for guild settings and ownership mappings."""

from __future__ import annotations

import sqlite3
from pathlib import Path

# Store the database on the Railway volume.
# The volume is mounted at /data, so this file will survive redeploys and restarts.
DB_PATH = Path("/data/bot.db")

print(f"Using database at: {DB_PATH.resolve()}")


def get_connection() -> sqlite3.Connection:
    """Return a SQLite connection with row access by column name."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    """Create database tables if they do not already exist."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS guild_settings (
                guild_id INTEGER PRIMARY KEY,
                room_category_id INTEGER,
                archive_category_id INTEGER,
                staff_role_id INTEGER,
                log_channel_id INTEGER
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS personal_roles (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                role_id INTEGER NOT NULL,
                PRIMARY KEY (guild_id, user_id)
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS personal_channels (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                PRIMARY KEY (guild_id, user_id)
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS room_locks (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                locked_by_staff INTEGER NOT NULL DEFAULT 0,
                lock_actor_id INTEGER,
                PRIMARY KEY (guild_id, user_id)
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS user_blocks (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                color_blocked INTEGER NOT NULL DEFAULT 0,
                color_block_actor_id INTEGER,
                room_blocked INTEGER NOT NULL DEFAULT 0,
                room_block_actor_id INTEGER,
                PRIMARY KEY (guild_id, user_id)
            )
            """
        )

        connection.commit()