"""Bot-owner-only slash commands."""

from __future__ import annotations

import os
import sqlite3
import time
import zipfile
from pathlib import Path
from typing import List, Optional

import discord
from discord import app_commands
from discord.ext import commands

from config import settings
from db import get_connection

DB_PATH = Path("/data/bot.db")
ZIP_PATH = Path("/data/bot-backup.zip")
TEMP_RESTORE_ZIP_PATH = Path("/data/restore-upload.zip")
TEMP_EXTRACT_DIR = Path("/data/restore_tmp")

MAINTENANCE_FLAG_PATH = Path("/data/maintenance.flag")
MAINTENANCE_MESSAGE_PATH = Path("/data/maintenance_message.txt")


def is_bot_admin(user_id: int) -> bool:
    """Return True if the given user ID is in the bot-admin allowlist."""
    return user_id in settings.bot_admin_ids


def format_bytes(num_bytes: int) -> str:
    """Return a human-readable size string."""
    size = float(num_bytes)
    units = ["B", "KB", "MB", "GB", "TB"]

    for unit in units:
        if size < 1024.0 or unit == units[-1]:
            return "{0:.2f} {1}".format(size, unit)
        size /= 1024.0

    return "{0:.2f} B".format(size)


def format_duration(seconds: float) -> str:
    """Return a human-readable uptime string."""
    total = int(seconds)
    days, rem = divmod(total, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, seconds = divmod(rem, 60)

    parts = []
    if days:
        parts.append("{0}d".format(days))
    if hours:
        parts.append("{0}h".format(hours))
    if minutes:
        parts.append("{0}m".format(minutes))
    parts.append("{0}s".format(seconds))
    return " ".join(parts)


def get_scalar(query: str, params: tuple = ()) -> int:
    """Run a scalar SQL query and return the first value as an int."""
    with get_connection() as connection:
        row = connection.execute(query, params).fetchone()

    if row is None:
        return 0

    value = row[0]
    return int(value) if value is not None else 0


def get_maintenance_state() -> bool:
    """Return whether maintenance mode is enabled."""
    return MAINTENANCE_FLAG_PATH.exists()


def get_maintenance_message() -> str:
    """Return the stored maintenance message, if any."""
    if not MAINTENANCE_MESSAGE_PATH.exists():
        return "Maintenance mode is enabled."
    return MAINTENANCE_MESSAGE_PATH.read_text(encoding="utf-8").strip() or "Maintenance mode is enabled."


def set_maintenance_state(enabled: bool, message: str = "") -> None:
    """Persist maintenance state to disk."""
    if enabled:
        MAINTENANCE_FLAG_PATH.parent.mkdir(parents=True, exist_ok=True)
        MAINTENANCE_FLAG_PATH.write_text("1", encoding="utf-8")
        MAINTENANCE_MESSAGE_PATH.write_text(message.strip(), encoding="utf-8")
    else:
        if MAINTENANCE_FLAG_PATH.exists():
            MAINTENANCE_FLAG_PATH.unlink()
        if MAINTENANCE_MESSAGE_PATH.exists():
            MAINTENANCE_MESSAGE_PATH.unlink()


class BotAdminCog(commands.Cog):
    """Commands reserved for the owners of the bot."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.started_at = time.time()

    admin_group = app_commands.Group(name="bot", description="Bot-owner-only commands")

    async def reject_if_not_bot_admin(self, interaction: discord.Interaction) -> bool:
        """Return True and respond if the user is not a bot admin."""
        if is_bot_admin(interaction.user.id):
            return False

        if interaction.response.is_done():
            await interaction.followup.send(
                "You are not allowed to use this command.",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                "You are not allowed to use this command.",
                ephemeral=True,
            )
        return True

    @admin_group.command(name="status", description="Show basic bot status")
    async def status(self, interaction: discord.Interaction) -> None:
        """Show a small status summary for the bot."""
        if await self.reject_if_not_bot_admin(interaction):
            return

        guild_count = len(self.bot.guilds)
        latency_ms = round(self.bot.latency * 1000, 2)
        db_exists = DB_PATH.exists()
        db_size = format_bytes(DB_PATH.stat().st_size) if db_exists else "N/A"
        uptime = format_duration(time.time() - self.started_at)

        embed = discord.Embed(title="Bot Status")
        embed.add_field(name="Guilds", value=str(guild_count), inline=True)
        embed.add_field(name="Latency", value="{0} ms".format(latency_ms), inline=True)
        embed.add_field(name="Uptime", value=uptime, inline=True)
        embed.add_field(name="Database Path", value="`{0}`".format(DB_PATH), inline=False)
        embed.add_field(name="Database Exists", value="Yes" if db_exists else "No", inline=True)
        embed.add_field(name="Database Size", value=db_size, inline=True)
        embed.add_field(
            name="Maintenance Mode",
            value="On" if get_maintenance_state() else "Off",
            inline=True,
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @admin_group.command(name="stats", description="Show high-level tracked data counts")
    async def stats(self, interaction: discord.Interaction) -> None:
        """Show database counts for tracked assets."""
        if await self.reject_if_not_bot_admin(interaction):
            return

        guild_settings_count = get_scalar("SELECT COUNT(*) FROM guild_settings")
        role_count = get_scalar("SELECT COUNT(*) FROM personal_roles")
        room_count = get_scalar("SELECT COUNT(*) FROM personal_channels")
        lock_count = get_scalar("SELECT COUNT(*) FROM room_locks")
        color_block_count = get_scalar("SELECT COUNT(*) FROM user_blocks WHERE color_blocked = 1")
        room_block_count = get_scalar("SELECT COUNT(*) FROM user_blocks WHERE room_blocked = 1")

        embed = discord.Embed(title="Bot Stats")
        embed.add_field(name="Guild Settings Rows", value=str(guild_settings_count), inline=True)
        embed.add_field(name="Tracked Roles", value=str(role_count), inline=True)
        embed.add_field(name="Tracked Rooms", value=str(room_count), inline=True)
        embed.add_field(name="Locked Rooms", value=str(lock_count), inline=True)
        embed.add_field(name="Color Blocks", value=str(color_block_count), inline=True)
        embed.add_field(name="Room Blocks", value=str(room_block_count), inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @admin_group.command(name="guilds", description="List guilds the bot is currently in")
    async def guilds(self, interaction: discord.Interaction) -> None:
        """List the guilds the bot is currently connected to."""
        if await self.reject_if_not_bot_admin(interaction):
            return

        if not self.bot.guilds:
            await interaction.response.send_message("The bot is not in any guilds.", ephemeral=True)
            return

        lines: List[str] = []
        for guild in sorted(self.bot.guilds, key=lambda g: g.name.lower()):
            lines.append(
                "- {0} (`{1}`) | members: {2}".format(
                    guild.name,
                    guild.id,
                    guild.member_count if guild.member_count is not None else "?",
                )
            )

        content = "\n".join(lines)
        if len(content) > 1900:
            content = content[:1900] + "\n..."

        await interaction.response.send_message(content, ephemeral=True)

    @admin_group.command(name="guild-info", description="Show configuration and counts for one guild")
    @app_commands.describe(guild_id="Guild ID to inspect")
    async def guild_info(self, interaction: discord.Interaction, guild_id: str) -> None:
        """Show detailed information for one guild by ID."""
        if await self.reject_if_not_bot_admin(interaction):
            return

        try:
            parsed_guild_id = int(guild_id)
        except ValueError:
            await interaction.response.send_message("Guild ID must be a number.", ephemeral=True)
            return

        guild = self.bot.get_guild(parsed_guild_id)
        if guild is None:
            await interaction.response.send_message(
                "The bot is not currently in that guild.",
                ephemeral=True,
            )
            return

        with get_connection() as connection:
            settings_row = connection.execute(
                """
                SELECT room_category_id, archive_category_id, staff_role_id, log_channel_id
                FROM guild_settings
                WHERE guild_id = ?
                """,
                (parsed_guild_id,),
            ).fetchone()

        tracked_roles = get_scalar(
            "SELECT COUNT(*) FROM personal_roles WHERE guild_id = ?",
            (parsed_guild_id,),
        )
        tracked_rooms = get_scalar(
            "SELECT COUNT(*) FROM personal_channels WHERE guild_id = ?",
            (parsed_guild_id,),
        )
        locked_rooms = get_scalar(
            "SELECT COUNT(*) FROM room_locks WHERE guild_id = ?",
            (parsed_guild_id,),
        )

        embed = discord.Embed(title="Guild Info: {0}".format(guild.name))
        embed.add_field(name="Guild ID", value=str(guild.id), inline=True)
        embed.add_field(
            name="Member Count",
            value=str(guild.member_count) if guild.member_count is not None else "?",
            inline=True,
        )
        embed.add_field(name="Tracked Roles", value=str(tracked_roles), inline=True)
        embed.add_field(name="Tracked Rooms", value=str(tracked_rooms), inline=True)
        embed.add_field(name="Locked Rooms", value=str(locked_rooms), inline=True)

        if settings_row is None:
            embed.add_field(name="Guild Settings", value="No row found.", inline=False)
        else:
            embed.add_field(
                name="Room Category ID",
                value=str(settings_row["room_category_id"]) if settings_row["room_category_id"] else "Not set",
                inline=True,
            )
            embed.add_field(
                name="Archive Category ID",
                value=str(settings_row["archive_category_id"]) if settings_row["archive_category_id"] else "Not set",
                inline=True,
            )
            embed.add_field(
                name="Staff Role ID",
                value=str(settings_row["staff_role_id"]) if settings_row["staff_role_id"] else "Not set",
                inline=True,
            )
            embed.add_field(
                name="Log Channel ID",
                value=str(settings_row["log_channel_id"]) if settings_row["log_channel_id"] else "Not set",
                inline=True,
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @admin_group.command(name="maintenance-on", description="Enable maintenance mode")
    @app_commands.describe(message="Optional maintenance message")
    async def maintenance_on(self, interaction: discord.Interaction, message: Optional[str] = None) -> None:
        """Enable maintenance mode."""
        if await self.reject_if_not_bot_admin(interaction):
            return

        set_maintenance_state(True, message or "Maintenance mode is enabled.")
        await interaction.response.send_message(
            "Maintenance mode enabled.",
            ephemeral=True,
        )

    @admin_group.command(name="maintenance-off", description="Disable maintenance mode")
    async def maintenance_off(self, interaction: discord.Interaction) -> None:
        """Disable maintenance mode."""
        if await self.reject_if_not_bot_admin(interaction):
            return

        set_maintenance_state(False)
        await interaction.response.send_message(
            "Maintenance mode disabled.",
            ephemeral=True,
        )

    @admin_group.command(name="maintenance-status", description="Show maintenance mode state")
    async def maintenance_status(self, interaction: discord.Interaction) -> None:
        """Show maintenance mode state."""
        if await self.reject_if_not_bot_admin(interaction):
            return

        enabled = get_maintenance_state()
        message = get_maintenance_message() if enabled else "Maintenance mode is disabled."

        await interaction.response.send_message(
            "**Maintenance Mode:** {0}\n{1}".format("On" if enabled else "Off", message),
            ephemeral=True,
        )

    @admin_group.command(name="resync-commands", description="Force a global slash-command resync")
    async def resync_commands(self, interaction: discord.Interaction) -> None:
        """Force the bot to resync slash commands globally."""
        if await self.reject_if_not_bot_admin(interaction):
            return

        await interaction.response.defer(ephemeral=True)
        synced = await self.bot.tree.sync()
        await interaction.followup.send(
            "Resynced {0} global command(s).".format(len(synced)),
            ephemeral=True,
        )

    @admin_group.command(name="backup-db", description="Zip and send the live database")
    async def backup_db(self, interaction: discord.Interaction) -> None:
        """Create a zipped database backup and send it through Discord."""
        if await self.reject_if_not_bot_admin(interaction):
            return

        await interaction.response.defer(ephemeral=True)

        if not DB_PATH.exists():
            await interaction.followup.send(
                "Database file was not found.",
                ephemeral=True,
            )
            return

        ZIP_PATH.parent.mkdir(parents=True, exist_ok=True)

        if ZIP_PATH.exists():
            ZIP_PATH.unlink()

        with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.write(DB_PATH, arcname="bot.db")

        file_size = ZIP_PATH.stat().st_size
        file_size_mb = round(file_size / (1024 * 1024), 2)

        await interaction.followup.send(
            content="Backup created ({0} MB).".format(file_size_mb),
            file=discord.File(str(ZIP_PATH), filename="bot-backup.zip"),
            ephemeral=True,
        )

    @admin_group.command(name="restore-db", description="Restore the live database from a backup zip")
    @app_commands.describe(file="Upload a bot-backup.zip file containing bot.db")
    async def restore_db(self, interaction: discord.Interaction, file: discord.Attachment) -> None:
        """Restore the SQLite database from an uploaded backup zip, then restart."""
        if await self.reject_if_not_bot_admin(interaction):
            return

        await interaction.response.defer(ephemeral=True)

        if not file.filename.lower().endswith(".zip"):
            await interaction.followup.send(
                "Please upload a `.zip` backup file.",
                ephemeral=True,
            )
            return

        TEMP_EXTRACT_DIR.mkdir(parents=True, exist_ok=True)

        if TEMP_RESTORE_ZIP_PATH.exists():
            TEMP_RESTORE_ZIP_PATH.unlink()

        extracted_db_path = TEMP_EXTRACT_DIR / "bot.db"
        if extracted_db_path.exists():
            extracted_db_path.unlink()

        try:
            await file.save(TEMP_RESTORE_ZIP_PATH)
        except Exception as error:
            await interaction.followup.send(
                "Failed to save uploaded file: `{0}`".format(error),
                ephemeral=True,
            )
            return

        try:
            with zipfile.ZipFile(TEMP_RESTORE_ZIP_PATH, "r") as archive:
                members = archive.namelist()

                if "bot.db" not in members:
                    await interaction.followup.send(
                        "The uploaded zip does not contain a `bot.db` file at its root.",
                        ephemeral=True,
                    )
                    return

                archive.extract("bot.db", path=str(TEMP_EXTRACT_DIR))
        except zipfile.BadZipFile:
            await interaction.followup.send(
                "That file is not a valid zip archive.",
                ephemeral=True,
            )
            return
        except Exception as error:
            await interaction.followup.send(
                "Failed to extract backup zip: `{0}`".format(error),
                ephemeral=True,
            )
            return

        if not extracted_db_path.exists():
            await interaction.followup.send(
                "Extraction finished, but `bot.db` was not found afterwards.",
                ephemeral=True,
            )
            return

        try:
            backup_of_current = DB_PATH.with_suffix(".pre_restore.bak")

            if backup_of_current.exists():
                backup_of_current.unlink()

            if DB_PATH.exists():
                DB_PATH.replace(backup_of_current)

            extracted_db_path.replace(DB_PATH)
        except Exception as error:
            await interaction.followup.send(
                "Failed to replace the live database: `{0}`".format(error),
                ephemeral=True,
            )
            return

        await interaction.followup.send(
            "Database restored successfully. Restarting the bot now...",
            ephemeral=True,
        )

        os._exit(0)


async def setup(bot: commands.Bot) -> None:
    """Cog loader hook."""
    await bot.add_cog(BotAdminCog(bot))