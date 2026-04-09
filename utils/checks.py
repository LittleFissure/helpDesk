from __future__ import annotations

"""Small validation helpers for command handlers."""

from typing import Callable, Coroutine, Any

import discord
from discord import app_commands

from services.guild_settings import get_guild_settings


def ensure_guild_interaction(interaction: discord.Interaction) -> None:
    """Raise a ValueError if a command is used outside a guild."""
    if interaction.guild is None:
        raise ValueError("This command can only be used inside a server.")


def member_has_staff_access(member: discord.Member, staff_role_id: int) -> bool:
    """Return True when the member has the configured staff role."""
    return any(role.id == staff_role_id for role in member.roles)


def staff_only() -> Callable[[Callable[..., Coroutine[Any, Any, Any]]], app_commands.Command]:
    """Allow a command when the user has the configured staff role or manage-server access."""

    async def predicate(interaction: discord.Interaction) -> bool:
        ensure_guild_interaction(interaction)

        member = interaction.user
        if not isinstance(member, discord.Member):
            return False

        perms = member.guild_permissions
        if perms.administrator or perms.manage_guild:
            return True

        settings = get_guild_settings(interaction.guild.id)
        staff_role_id = settings["staff_role_id"]
        if staff_role_id is None:
            return False

        return member_has_staff_access(member, staff_role_id)

    return app_commands.check(predicate)
