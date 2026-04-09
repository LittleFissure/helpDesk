from __future__ import annotations

"""SQLite persistence helpers for guild settings and ownership mappings."""

import sqlite3
from pathlib import Path

DB_PATH = Path("data/bot.db")


def get_connection():
    """Return a SQLite connection with row access by column name."""
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    """Create database tables if they do not already exist."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS guild_settings (
                guild_id INTEGER PRIMARY KEY,
                room_category_id INTEGER,
                staff_role_id INTEGER,
                archive_category_id INTEGER,
                log_channel_id INTEGER
            )
            """
        )
        existing_columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(guild_settings)").fetchall()
        }
        if "archive_category_id" not in existing_columns:
            connection.execute("ALTER TABLE guild_settings ADD COLUMN archive_category_id INTEGER")
        if "log_channel_id" not in existing_columns:
            connection.execute("ALTER TABLE guild_settings ADD COLUMN log_channel_id INTEGER")

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
                PRIMARY KEY (guild_id, user_id)
            )
            """
        )
        connection.commit()
