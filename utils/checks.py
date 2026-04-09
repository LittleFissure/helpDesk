from __future__ import annotations

"""Small validation helpers for command handlers."""

from typing import Any, Callable, Coroutine

import discord
from discord import app_commands

from services.guild_settings import get_guild_settings
from services.restrictions import is_user_blocked


BLOCKED_SELF_SERVICE_MESSAGE = (
    "You are blocked from using room creation and self-service rename or colour-set commands in this server. "
    "Ask staff if this should be removed."
)


def ensure_guild_interaction(interaction: discord.Interaction) -> None:
    """Raise a ValueError if a command is used outside a guild."""
    if interaction.guild is None:
        raise ValueError("This command can only be used inside a server.")


def member_has_staff_access(member: discord.Member, staff_role_id: int) -> bool:
    """Return True when the member has the configured staff role."""
    return any(role.id == staff_role_id for role in member.roles)


def ensure_member_not_blocked(interaction: discord.Interaction) -> None:
    """Raise a PermissionError if the interaction user is blocked from selected self-service commands."""
    ensure_guild_interaction(interaction)
    if is_user_blocked(interaction.guild.id, interaction.user.id):
        raise PermissionError(BLOCKED_SELF_SERVICE_MESSAGE)


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
