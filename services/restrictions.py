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
            "SELECT 1 FROM blocked_users WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        ).fetchone()
    return row is not None


def get_block_record(guild_id: int, user_id: int):
    """Return the raw block record for a guild/user pair, if any."""
    with get_connection() as connection:
        row = connection.execute(
            "SELECT blocked_by_user_id FROM blocked_users WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        ).fetchone()
    return row


def describe_user_block(guild: discord.Guild, user_id: int):
    """Return a small info dict about a user's blocked state."""
    row = get_block_record(guild.id, user_id)
    blocked_by_user_id = int(row["blocked_by_user_id"]) if row else None
    return {
        "blocked": row is not None,
        "blocked_by_user_id": blocked_by_user_id,
    }


async def block_user(member: discord.Member, actor: discord.abc.User):
    """Persist a restriction that blocks a user from selected self-service commands."""
    if is_member_block_immune(member):
        raise PermissionError("That member cannot be blocked because they are staff or have server management access.")
    if is_user_blocked(member.guild.id, member.id):
        raise LookupError("That member is already blocked from self-service rename and set commands.")

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO blocked_users (guild_id, user_id, blocked_by_user_id)
            VALUES (?, ?, ?)
            ON CONFLICT(guild_id, user_id) DO UPDATE SET blocked_by_user_id = excluded.blocked_by_user_id
            """,
            (member.guild.id, member.id, actor.id),
        )
        connection.commit()

    await log_event(
        member.guild,
        "User Blocked",
        "Blocked a member from selected self-service room and role commands.",
        actor=actor,
        target=member,
    )


async def unblock_user(member: discord.Member, actor: discord.abc.User):
    """Remove a previously stored user restriction."""
    if not is_user_blocked(member.guild.id, member.id):
        raise LookupError("That member is not currently blocked.")

    with get_connection() as connection:
        connection.execute(
            "DELETE FROM blocked_users WHERE guild_id = ? AND user_id = ?",
            (member.guild.id, member.id),
        )
        connection.commit()

    await log_event(
        member.guild,
        "User Unblocked",
        "Removed a member restriction for self-service room and role commands.",
        actor=actor,
        target=member,
    )
