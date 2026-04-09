from __future__ import annotations

"""Slash commands for personal public text rooms."""

import discord
from discord import app_commands
from discord.ext import commands

from services.channels import (
    create_room_for_member,
    describe_member_room,
    get_member_room,
    lock_member_room,
    rename_member_room,
    unlock_member_room,
)
from utils.checks import ensure_guild_interaction
from utils.naming import sanitise_channel_name


class RoomCog(commands.Cog):
    """Commands that let a member create and manage only their own room."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    room_group = app_commands.Group(name="room", description="Manage your personal room")

    @room_group.command(name="create", description="Create your public personal room")
    async def room_create(self, interaction: discord.Interaction) -> None:
        try:
            ensure_guild_interaction(interaction)
        except ValueError as error:
            await interaction.response.send_message(str(error), ephemeral=True)
            return

        member = interaction.user
        assert isinstance(member, discord.Member)

        existing = get_member_room(interaction.guild, member.id)
        if existing is not None:
            await interaction.response.send_message(
                "You already have a room: {0}".format(existing.mention),
                ephemeral=True,
            )
            return

        try:
            channel = await create_room_for_member(member)
        except RuntimeError as error:
            await interaction.response.send_message(str(error), ephemeral=True)
            return

        await interaction.response.send_message(
            "Created your room: {0}".format(channel.mention),
            ephemeral=True,
        )

    @room_group.command(name="rename", description="Rename your personal room")
    @app_commands.describe(new_name="New channel name, for example moss-corner")
    async def room_rename(self, interaction: discord.Interaction, new_name: str) -> None:
        try:
            ensure_guild_interaction(interaction)
        except ValueError as error:
            await interaction.response.send_message(str(error), ephemeral=True)
            return

        member = interaction.user
        assert isinstance(member, discord.Member)

        try:
            clean_name = sanitise_channel_name(new_name)
        except ValueError as error:
            await interaction.response.send_message(str(error), ephemeral=True)
            return

        try:
            channel = await rename_member_room(interaction.guild, member.id, clean_name)
        except LookupError as error:
            await interaction.response.send_message(str(error), ephemeral=True)
            return

        await interaction.response.send_message(
            "Renamed your room to {0}.".format(channel.mention),
            ephemeral=True,
        )

    @room_group.command(name="info", description="Show tracking information for your personal room")
    async def room_info(self, interaction: discord.Interaction) -> None:
        try:
            ensure_guild_interaction(interaction)
        except ValueError as error:
            await interaction.response.send_message(str(error), ephemeral=True)
            return

        member = interaction.user
        assert isinstance(member, discord.Member)

        info = describe_member_room(interaction.guild, member.id)
        exists_text = "Yes" if info["exists"] else "No"
        channel_text = "<#{0}>".format(info["channel_id"]) if info["channel_id"] else "Not tracked"
        lock_text = "Locked by staff" if info["locked_by_staff"] else ("Locked by owner" if info["locked"] else "Unlocked")

        embed = discord.Embed(title="Your Room Info")
        embed.add_field(name="Tracked Channel", value=channel_text, inline=False)
        embed.add_field(name="Exists", value=exists_text, inline=True)
        embed.add_field(name="Channel Name", value=info["channel_name"] or "Unknown", inline=True)
        embed.add_field(name="Lock State", value=lock_text, inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @room_group.command(name="lock", description="Lock your room so only staff can send messages")
    async def room_lock(self, interaction: discord.Interaction) -> None:
        try:
            ensure_guild_interaction(interaction)
        except ValueError as error:
            await interaction.response.send_message(str(error), ephemeral=True)
            return

        member = interaction.user
        assert isinstance(member, discord.Member)

        try:
            channel = await lock_member_room(member, locked_by_staff=False)
        except LookupError as error:
            await interaction.response.send_message(str(error), ephemeral=True)
            return

        await interaction.response.send_message(
            "Locked your room: {0}".format(channel.mention),
            ephemeral=True,
        )

    @room_group.command(name="unlock", description="Unlock your room")
    async def room_unlock(self, interaction: discord.Interaction) -> None:
        try:
            ensure_guild_interaction(interaction)
        except ValueError as error:
            await interaction.response.send_message(str(error), ephemeral=True)
            return

        member = interaction.user
        assert isinstance(member, discord.Member)

        try:
            channel = await unlock_member_room(member, by_staff=False)
        except (LookupError, PermissionError) as error:
            await interaction.response.send_message(str(error), ephemeral=True)
            return

        await interaction.response.send_message(
            "Unlocked your room: {0}".format(channel.mention),
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    """Cog loader hook."""
    await bot.add_cog(RoomCog(bot))
