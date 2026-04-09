from __future__ import annotations

"""Guild audit logging helpers."""

import logging
from typing import Optional

import discord

from services.guild_settings import get_guild_settings

logger = logging.getLogger("bot.audit")


def build_log_embed(title, description, actor=None, target=None, extra_fields=None):
    """Create a consistent audit embed for the configured log channel."""
    embed = discord.Embed(title=title, description=description)

    if actor is not None:
        embed.add_field(name="Actor", value=getattr(actor, "mention", str(actor)), inline=True)
    if target is not None:
        embed.add_field(name="Target", value=getattr(target, "mention", str(target)), inline=True)

    if extra_fields:
        for name, value in extra_fields:
            embed.add_field(name=name, value=value, inline=True)

    return embed


async def log_event(guild, title, description, actor=None, target=None, extra_fields=None):
    """Write an audit event to console and the guild's configured log channel."""
    logger.info("[%s] %s | %s", guild.name if guild else "unknown-guild", title, description)

    if guild is None:
        return

    settings = get_guild_settings(guild.id)
    channel_id = settings["log_channel_id"]
    if channel_id is None:
        return

    channel = guild.get_channel(channel_id)
    if channel is None or not isinstance(channel, discord.TextChannel):
        return

    embed = build_log_embed(title, description, actor=actor, target=target, extra_fields=extra_fields)
    try:
        await channel.send(embed=embed)
    except Exception:
        logger.exception("Failed to send audit log embed.")
