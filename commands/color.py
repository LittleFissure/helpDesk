from __future__ import annotations

"""Slash commands for personal colour roles."""

import discord
from discord import app_commands
from discord.ext import commands

from services.roles import (
    describe_member_role,
    rename_personal_role,
    reset_personal_role_colour,
    set_personal_role_colour,
)
from utils.checks import ensure_guild_interaction, ensure_member_not_blocked
from utils.naming import normalise_hex_colour, sanitise_role_name


class ColorCog(commands.Cog):
    """Commands that let a member manage only their own colour role."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    color_group = app_commands.Group(name="color", description="Manage your personal colour role")

    @color_group.command(name="set", description="Set your personal role colour using a hex code")
    @app_commands.describe(hex_code="Hex colour in the form #ff66aa")
    async def color_set(self, interaction: discord.Interaction, hex_code: str) -> None:
        try:
            ensure_guild_interaction(interaction)
            ensure_member_not_blocked(interaction)
        except (ValueError, PermissionError) as error:
            await interaction.response.send_message(str(error), ephemeral=True)
            return

        try:
            clean_hex = normalise_hex_colour(hex_code)
            colour = discord.Colour.from_str(clean_hex)
        except ValueError as error:
            await interaction.response.send_message(str(error), ephemeral=True)
            return

        member = interaction.user
        assert isinstance(member, discord.Member)

        await set_personal_role_colour(member, colour, actor=member)
        await interaction.response.send_message(
            "Updated your personal colour to `{0}`.".format(clean_hex),
            ephemeral=True,
        )

    @color_group.command(name="reset", description="Reset your personal role back to no colour")
    async def color_reset(self, interaction: discord.Interaction) -> None:
        try:
            ensure_guild_interaction(interaction)
        except ValueError as error:
            await interaction.response.send_message(str(error), ephemeral=True)
            return

        member = interaction.user
        assert isinstance(member, discord.Member)

        await reset_personal_role_colour(member, actor=member)
        await interaction.response.send_message(
            "Your personal colour has been reset.",
            ephemeral=True,
        )

    @color_group.command(name="rename", description="Rename your personal colour role")
    @app_commands.describe(new_name="New role name, for example Moss Green")
    async def color_rename(self, interaction: discord.Interaction, new_name: str) -> None:
        try:
            ensure_guild_interaction(interaction)
            ensure_member_not_blocked(interaction)
        except (ValueError, PermissionError) as error:
            await interaction.response.send_message(str(error), ephemeral=True)
            return

        try:
            clean_name = sanitise_role_name(new_name)
        except ValueError as error:
            await interaction.response.send_message(str(error), ephemeral=True)
            return

        member = interaction.user
        assert isinstance(member, discord.Member)

        role = await rename_personal_role(member, clean_name, actor=member)
        await interaction.response.send_message(
            "Renamed your personal role to **{0}**.".format(role.name),
            ephemeral=True,
        )

    @color_group.command(name="info", description="Show tracking information for your personal role")
    async def color_info(self, interaction: discord.Interaction) -> None:
        try:
            ensure_guild_interaction(interaction)
        except ValueError as error:
            await interaction.response.send_message(str(error), ephemeral=True)
            return

        member = interaction.user
        assert isinstance(member, discord.Member)

        info = describe_member_role(interaction.guild, member.id)
        exists_text = "Yes" if info["exists"] else "No"
        role_text = "<@&{0}>".format(info["role_id"]) if info["role_id"] else "Not tracked"

        embed = discord.Embed(title="Your Role Info")
        embed.add_field(name="Tracked Role", value=role_text, inline=False)
        embed.add_field(name="Exists", value=exists_text, inline=True)
        embed.add_field(name="Role Name", value=info["role_name"] or "Unknown", inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    """Cog loader hook."""
    await bot.add_cog(ColorCog(bot))
