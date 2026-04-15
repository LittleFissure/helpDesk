from __future__ import annotations

"""Helpers for member-level moderation restrictions."""

import discord

from db import get_connection
from services.guild_settings import get_guild_settings
from services.logging_service import log_event


def _member_has_configured_staff_role(member: discord.Member) -> bool:
    """Return True when the member has the configured staff role for the guild."""
    settings = get_guild_settings(member.guild.id)
    staff_role_id = settings["staff_role_id"]
    if staff_role_id is None:
        return False
    return any(role.id == staff_role_id for role in member.roles)


def is_member_block_immune(member: discord.Member) -> bool:
    """Return True when the member should be immune from user blocking."""
    perms = member.guild_permissions
    return perms.administrator or perms.manage_guild or _member_has_configured_staff_role(member)


def is_user_blocked(guild_id: int, user_id: int) -> bool:
    """Return True when the user is blocked from selected self-service commands."""
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT 1 FROM user_blocks
            WHERE guild_id = ? AND user_id = ?
            AND (color_blocked = 1 OR room_blocked = 1)
            """,
            (guild_id, user_id),
        ).fetchone()
    return row is not None


def get_block_record(guild_id: int, user_id: int):
    """Return the raw block record for a guild/user pair, if any."""
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT color_blocked, room_blocked,
                   color_block_actor_id, room_block_actor_id
            FROM user_blocks
            WHERE guild_id = ? AND user_id = ?
            """,
            (guild_id, user_id),
        ).fetchone()
    return row


def describe_user_block(guild: discord.Guild, user_id: int):
    """Return a small info dict about a user's blocked state."""
    row = get_block_record(guild.id, user_id)

    if not row:
        return {
            "blocked": False,
            "blocked_by_user_id": None,
            "color_blocked": False,
            "room_blocked": False,
        }

    blocked = row["color_blocked"] or row["room_blocked"]

    # pick whichever actor exists (color or room)
    actor_id = row["color_block_actor_id"] or row["room_block_actor_id"]

    return {
        "blocked": blocked,
        "blocked_by_user_id": actor_id,
        "color_blocked": bool(row["color_blocked"]),
        "room_blocked": bool(row["room_blocked"]),
    }


async def block_user(member: discord.Member, actor: discord.abc.User):
    """Block a user from both room and color self-service commands."""
    if is_member_block_immune(member):
        raise PermissionError(
            "That member cannot be blocked because they are staff or have server management access."
        )

    if is_user_blocked(member.guild.id, member.id):
        raise LookupError("That member is already blocked.")

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO user_blocks (
                guild_id, user_id,
                color_blocked, color_block_actor_id,
                room_blocked, room_block_actor_id
            )
            VALUES (?, ?, 1, ?, 1, ?)
            ON CONFLICT(guild_id, user_id) DO UPDATE SET
                color_blocked = 1,
                color_block_actor_id = excluded.color_block_actor_id,
                room_blocked = 1,
                room_block_actor_id = excluded.room_block_actor_id
            """,
            (member.guild.id, member.id, actor.id, actor.id),
        )
        connection.commit()

    await log_event(
        member.guild,
        "User Blocked",
        "Blocked a member from room and role self-service commands.",
        actor=actor,
        target=member,
    )


async def unblock_user(member: discord.Member, actor: discord.abc.User):
    """Remove a previously stored user restriction."""
    if not is_user_blocked(member.guild.id, member.id):
        raise LookupError("That member is not currently blocked.")

    with get_connection() as connection:
        connection.execute(
            """
            UPDATE user_blocks
            SET color_blocked = 0,
                room_blocked = 0,
                color_block_actor_id = NULL,
                room_block_actor_id = NULL
            WHERE guild_id = ? AND user_id = ?
            """,
            (member.guild.id, member.id),
        )
        connection.commit()

    await log_event(
        member.guild,
        "User Unblocked",
        "Removed a member restriction for room and role commands.",
        actor=actor,
        target=member,
    )