from __future__ import annotations

"""Role-related service functions."""

from typing import List, Optional, Tuple

import discord

from db import get_connection
from services.logging_service import log_event


def get_personal_role_id(guild_id, user_id):
    """Return the stored personal role ID for the given user in the given guild, if any."""
    with get_connection() as connection:
        row = connection.execute(
            "SELECT role_id FROM personal_roles WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        ).fetchone()
    return int(row["role_id"]) if row else None


def save_personal_role_id(guild_id, user_id, role_id):
    """Insert or update the stored personal role mapping for the user in this guild."""
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO personal_roles (guild_id, user_id, role_id)
            VALUES (?, ?, ?)
            ON CONFLICT(guild_id, user_id) DO UPDATE SET role_id = excluded.role_id
            """,
            (guild_id, user_id, role_id),
        )
        connection.commit()


def clear_personal_role_id(guild_id, user_id):
    """Remove the stored personal role mapping for a guild/user pair."""
    with get_connection() as connection:
        connection.execute(
            "DELETE FROM personal_roles WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        )
        connection.commit()


def iter_personal_role_rows(guild_id):
    """Return all stored user/role pairs for one guild."""
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT user_id, role_id FROM personal_roles WHERE guild_id = ?",
            (guild_id,),
        ).fetchall()
    return [(int(row["user_id"]), int(row["role_id"])) for row in rows]


async def ensure_personal_role(member):
    """Return the member's personal role, creating and assigning it if needed."""
    stored_role_id = get_personal_role_id(member.guild.id, member.id)
    if stored_role_id:
        existing_role = member.guild.get_role(stored_role_id)
        if existing_role is not None:
            if existing_role not in member.roles:
                await member.add_roles(existing_role, reason="Restoring personal colour role")
            return existing_role

    role = await member.guild.create_role(
        name="color-{0}".format(member.id),
        colour=discord.Colour.default(),
        reason="Creating personal colour role",
        mentionable=False,
    )
    await member.add_roles(role, reason="Assigning personal colour role")
    save_personal_role_id(member.guild.id, member.id, role.id)
    await log_event(member.guild, "Role Created", "Created a tracked personal role.", actor=member, target=role)
    return role


async def reset_personal_role_colour(member):
    """Set the member's personal role back to Discord's default colour."""
    role = await ensure_personal_role(member)
    await role.edit(colour=discord.Colour.default(), reason="Personal colour reset by {0}".format(member))


async def rename_personal_role(member, new_name):
    """Rename the member's personal role and return it."""
    role = await ensure_personal_role(member)
    await role.edit(name=new_name, reason="Personal role renamed by {0}".format(member))
    await log_event(member.guild, "Role Renamed", "Renamed a tracked personal role.", actor=member, target=role)
    return role


async def claim_personal_role(member, role):
    """Adopt an existing role as the member's tracked personal role."""
    save_personal_role_id(member.guild.id, member.id, role.id)
    if role not in member.roles:
        await member.add_roles(role, reason="Claiming existing personal role")
    await log_event(member.guild, "Role Claimed", "Claimed an existing role as a tracked personal role.", actor=member, target=role)


async def delete_personal_role(member):
    """Delete a member's tracked personal role and clear its DB record."""
    role_id = get_personal_role_id(member.guild.id, member.id)
    role = member.guild.get_role(role_id) if role_id else None
    clear_personal_role_id(member.guild.id, member.id)
    if role is not None:
        await role.delete(reason="Deleting tracked personal role for {0}".format(member))
        await log_event(member.guild, "Role Deleted", "Deleted a tracked personal role.", actor=member, target=role)


def describe_member_role(guild, user_id):
    """Return a small info dict about a tracked personal role."""
    role_id = get_personal_role_id(guild.id, user_id)
    role = guild.get_role(role_id) if role_id else None
    return {
        "role_id": role_id,
        "exists": role is not None,
        "role_name": role.name if role is not None else None,
    }
