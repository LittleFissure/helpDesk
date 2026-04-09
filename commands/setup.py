from __future__ import annotations

"""Administrator setup commands for configuring each guild independently."""

import discord
from discord import app_commands
from discord.ext import commands

from services.guild_settings import (
    get_guild_settings,
    set_archive_category_id,
    set_log_channel_id,
    set_room_category_id,
    set_staff_role_id,
)
from services.sync_tools import repair_guild_assets, sync_existing_members
from utils.checks import ensure_guild_interaction


class SetupCog(commands.Cog):
    """Commands used by administrators to configure each server."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    setup_group = app_commands.Group(name="setup", description="Configure this server for the bot")

    @setup_group.command(name="category", description="Choose which category personal rooms should use")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(category="The category where personal rooms should be created")
    async def setup_category(
        self,
        interaction: discord.Interaction,
        category: discord.CategoryChannel,
    ) -> None:
        try:
            ensure_guild_interaction(interaction)
        except ValueError as error:
            await interaction.response.send_message(str(error), ephemeral=True)
            return

        set_room_category_id(interaction.guild.id, category.id)
        await interaction.response.send_message(
            "Personal rooms will now be created in **{0}**.".format(category.name),
            ephemeral=True,
        )

    @setup_group.command(name="archive-category", description="Choose which category archived rooms should use")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(category="The category where archived rooms should be moved")
    async def setup_archive_category(
        self,
        interaction: discord.Interaction,
        category: discord.CategoryChannel,
    ) -> None:
        try:
            ensure_guild_interaction(interaction)
        except ValueError as error:
            await interaction.response.send_message(str(error), ephemeral=True)
            return

        set_archive_category_id(interaction.guild.id, category.id)
        await interaction.response.send_message(
            "Archived rooms will now be moved into **{0}**.".format(category.name),
            ephemeral=True,
        )

    @setup_group.command(name="log-channel", description="Choose which channel receives bot audit logs")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(channel="Text channel where audit logs should be sent")
    async def setup_log_channel(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
    ) -> None:
        try:
            ensure_guild_interaction(interaction)
        except ValueError as error:
            await interaction.response.send_message(str(error), ephemeral=True)
            return

        set_log_channel_id(interaction.guild.id, channel.id)
        await interaction.response.send_message(
            "Audit logs will now be sent to {0}.".format(channel.mention),
            ephemeral=True,
        )

    @setup_group.command(name="create-category", description="Create a category for personal rooms")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(name="Name for the new category")
    async def setup_create_category(
        self,
        interaction: discord.Interaction,
        name: str = "Personal Rooms",
    ) -> None:
        try:
            ensure_guild_interaction(interaction)
        except ValueError as error:
            await interaction.response.send_message(str(error), ephemeral=True)
            return

        category = await interaction.guild.create_category(
            name=name,
            reason="Requested by {0} for personal rooms setup".format(interaction.user),
        )

        set_room_category_id(interaction.guild.id, category.id)
        await interaction.response.send_message(
            "Created category **{0}** and set it as the personal rooms category.".format(category.name),
            ephemeral=True,
        )

    @setup_group.command(name="staff-role", description="Choose which role gets staff access in personal rooms")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(role="Role that should keep moderation access in personal rooms")
    async def setup_staff_role(
        self,
        interaction: discord.Interaction,
        role: discord.Role,
    ) -> None:
        try:
            ensure_guild_interaction(interaction)
        except ValueError as error:
            await interaction.response.send_message(str(error), ephemeral=True)
            return

        set_staff_role_id(interaction.guild.id, role.id)
        await interaction.response.send_message(
            "Staff access in personal rooms is now assigned to **{0}**.".format(role.name),
            ephemeral=True,
        )

    @setup_group.command(name="show", description="Show the current configuration for this server")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setup_show(self, interaction: discord.Interaction) -> None:
        try:
            ensure_guild_interaction(interaction)
        except ValueError as error:
            await interaction.response.send_message(str(error), ephemeral=True)
            return

        settings = get_guild_settings(interaction.guild.id)
        category = interaction.guild.get_channel(settings["room_category_id"]) if settings["room_category_id"] else None
        archive = interaction.guild.get_channel(settings["archive_category_id"]) if settings["archive_category_id"] else None
        role = interaction.guild.get_role(settings["staff_role_id"]) if settings["staff_role_id"] else None
        log_channel = interaction.guild.get_channel(settings["log_channel_id"]) if settings["log_channel_id"] else None

        category_text = category.mention if isinstance(category, discord.CategoryChannel) else "Not set"
        archive_text = archive.mention if isinstance(archive, discord.CategoryChannel) else "Not set"
        role_text = role.mention if isinstance(role, discord.Role) else "Not set"
        log_text = log_channel.mention if isinstance(log_channel, discord.TextChannel) else "Not set"

        await interaction.response.send_message(
            "**Room category:** {0}\n**Archive category:** {1}\n**Staff role:** {2}\n**Log channel:** {3}".format(
                category_text, archive_text, role_text, log_text
            ),
            ephemeral=True,
        )

    @setup_group.command(name="sync-members", description="Create missing personal roles for current members")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setup_sync_members(self, interaction: discord.Interaction) -> None:
        try:
            ensure_guild_interaction(interaction)
        except ValueError as error:
            await interaction.response.send_message(str(error), ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        created, skipped = await sync_existing_members(interaction.guild)
        await interaction.followup.send(
            "Sync complete. Created **{0}** personal role(s) and skipped **{1}** member(s).".format(created, skipped),
            ephemeral=True,
        )

    @setup_group.command(name="repair", description="Repair missing roles and rooms from stored records")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(dry_run="If true, preview the repair without changing anything")
    async def setup_repair(
        self,
        interaction: discord.Interaction,
        dry_run: bool = False,
    ) -> None:
        try:
            ensure_guild_interaction(interaction)
        except ValueError as error:
            await interaction.response.send_message(str(error), ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        result = await repair_guild_assets(interaction.guild, dry_run=dry_run)
        prefix = "Repair preview" if dry_run else "Repair complete"
        await interaction.followup.send(
            (
                "{0}.\n"
                "- Roles recreated: **{1}**\n"
                "- Rooms recreated: **{2}**\n"
                "- Missing room records cleared: **{3}**"
            ).format(prefix, result["roles_recreated"], result["rooms_recreated"], result["room_records_cleared"]),
            ephemeral=True,
        )

    @setup_group.command(name="diagnostics", description="Check the current server setup and bot readiness")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setup_diagnostics(self, interaction: discord.Interaction) -> None:
        try:
            ensure_guild_interaction(interaction)
        except ValueError as error:
            await interaction.response.send_message(str(error), ephemeral=True)
            return

        guild = interaction.guild
        me = guild.me
        settings = get_guild_settings(guild.id)
        lines = []

        if me is None:
            await interaction.response.send_message("Could not resolve the bot member in this server.", ephemeral=True)
            return

        perms = guild.me.guild_permissions
        lines.append("Manage Roles: {0}".format("OK" if perms.manage_roles else "Missing"))
        lines.append("Manage Channels: {0}".format("OK" if perms.manage_channels else "Missing"))
        lines.append("View Channels: {0}".format("OK" if perms.view_channel else "Missing"))
        lines.append("Read Message History: {0}".format("OK" if perms.read_message_history else "Missing"))

        room_category = guild.get_channel(settings["room_category_id"]) if settings["room_category_id"] else None
        archive_category = guild.get_channel(settings["archive_category_id"]) if settings["archive_category_id"] else None
        staff_role = guild.get_role(settings["staff_role_id"]) if settings["staff_role_id"] else None

        lines.append("Room category configured: {0}".format("OK" if isinstance(room_category, discord.CategoryChannel) else "Missing"))
        lines.append("Archive category configured: {0}".format("OK" if isinstance(archive_category, discord.CategoryChannel) else "Missing"))
        lines.append("Staff role configured: {0}".format("OK" if isinstance(staff_role, discord.Role) else "Missing"))

        if guild.me.top_role:
            lines.append("Bot top role: {0}".format(guild.me.top_role.name))

        embed = discord.Embed(title="Setup Diagnostics", description="\n".join(lines))
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @setup_category.error
    @setup_archive_category.error
    @setup_log_channel.error
    @setup_create_category.error
    @setup_staff_role.error
    @setup_show.error
    @setup_sync_members.error
    @setup_repair.error
    @setup_diagnostics.error
    async def setup_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
        if isinstance(error, app_commands.errors.MissingPermissions):
            if interaction.response.is_done():
                await interaction.followup.send(
                    "You need the **Manage Server** permission to use setup commands.",
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    "You need the **Manage Server** permission to use setup commands.",
                    ephemeral=True,
                )
            return

        raise error


async def setup(bot: commands.Bot) -> None:
    """Cog loader hook."""
    await bot.add_cog(SetupCog(bot))
