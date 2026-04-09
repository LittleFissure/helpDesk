from __future__ import annotations

"""Read and write per-guild configuration values."""

from db import get_connection


def get_guild_settings(guild_id):
    """Return the stored settings for a guild, inserting a default row if needed."""
    with get_connection() as connection:
        row = connection.execute(
            "SELECT room_category_id, staff_role_id, archive_category_id, log_channel_id FROM guild_settings WHERE guild_id = ?",
            (guild_id,),
        ).fetchone()

        if row is None:
            connection.execute(
                "INSERT INTO guild_settings (guild_id, room_category_id, staff_role_id, archive_category_id, log_channel_id) VALUES (?, NULL, NULL, NULL, NULL)",
                (guild_id,),
            )
            connection.commit()
            return {
                "room_category_id": None,
                "staff_role_id": None,
                "archive_category_id": None,
                "log_channel_id": None,
            }

    return {
        "room_category_id": int(row["room_category_id"]) if row["room_category_id"] else None,
        "staff_role_id": int(row["staff_role_id"]) if row["staff_role_id"] else None,
        "archive_category_id": int(row["archive_category_id"]) if row["archive_category_id"] else None,
        "log_channel_id": int(row["log_channel_id"]) if row["log_channel_id"] else None,
    }


def set_room_category_id(guild_id, category_id):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO guild_settings (guild_id, room_category_id, staff_role_id, archive_category_id, log_channel_id)
            VALUES (?, ?, NULL, NULL, NULL)
            ON CONFLICT(guild_id)
            DO UPDATE SET room_category_id = excluded.room_category_id
            """,
            (guild_id, category_id),
        )
        connection.commit()


def set_staff_role_id(guild_id, role_id):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO guild_settings (guild_id, room_category_id, staff_role_id, archive_category_id, log_channel_id)
            VALUES (?, NULL, ?, NULL, NULL)
            ON CONFLICT(guild_id)
            DO UPDATE SET staff_role_id = excluded.staff_role_id
            """,
            (guild_id, role_id),
        )
        connection.commit()


def set_archive_category_id(guild_id, category_id):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO guild_settings (guild_id, room_category_id, staff_role_id, archive_category_id, log_channel_id)
            VALUES (?, NULL, NULL, ?, NULL)
            ON CONFLICT(guild_id)
            DO UPDATE SET archive_category_id = excluded.archive_category_id
            """,
            (guild_id, category_id),
        )
        connection.commit()


def set_log_channel_id(guild_id, channel_id):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO guild_settings (guild_id, room_category_id, staff_role_id, archive_category_id, log_channel_id)
            VALUES (?, NULL, NULL, NULL, ?)
            ON CONFLICT(guild_id)
            DO UPDATE SET log_channel_id = excluded.log_channel_id
            """,
            (guild_id, channel_id),
        )
        connection.commit()
