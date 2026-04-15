"""Bot-owner-only slash commands."""

from __future__ import annotations

import os
import zipfile
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

from config import settings

DB_PATH = Path("/data/bot.db")
ZIP_PATH = Path("/data/bot-backup.zip")
TEMP_RESTORE_ZIP_PATH = Path("/data/restore-upload.zip")
TEMP_EXTRACT_DIR = Path("/data/restore_tmp")


def is_bot_admin(user_id: int) -> bool:
    """Return True if the given user ID is in the bot-admin allowlist."""
    return user_id in settings.bot_admin_ids


class BotAdminCog(commands.Cog):
    """Commands reserved for the owners of the bot."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    # The Python attribute name must not start with "bot_",
    # but the slash command group itself can still be named "bot".
    admin_group = app_commands.Group(name="bot", description="Bot-owner-only commands")

    @admin_group.command(name="status", description="Show basic bot status")
    async def status(self, interaction: discord.Interaction) -> None:
        """Show a small status summary for the bot."""
        if not is_bot_admin(interaction.user.id):
            await interaction.response.send_message(
                "You are not allowed to use this command.",
                ephemeral=True,
            )
            return

        guild_count = len(self.bot.guilds)
        latency_ms = round(self.bot.latency * 1000, 2)

        await interaction.response.send_message(
            (
                f"**Bot status**\n"
                f"- Guilds: **{guild_count}**\n"
                f"- Latency: **{latency_ms} ms**\n"
                f"- DB path: `{DB_PATH}`\n"
                f"- DB exists: **{'yes' if DB_PATH.exists() else 'no'}**"
            ),
            ephemeral=True,
        )

    @admin_group.command(name="backup-db", description="Zip and send the live database")
    async def backup_db(self, interaction: discord.Interaction) -> None:
        """Create a zipped database backup and send it through Discord."""
        if not is_bot_admin(interaction.user.id):
            await interaction.response.send_message(
                "You are not allowed to use this command.",
                ephemeral=True,
            )
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
            content=f"Backup created ({file_size_mb} MB).",
            file=discord.File(ZIP_PATH, filename="bot-backup.zip"),
            ephemeral=True,
        )

    @admin_group.command(name="restore-db", description="Restore the live database from a backup zip")
    @app_commands.describe(file="Upload a bot-backup.zip file containing bot.db")
    async def restore_db(
        self,
        interaction: discord.Interaction,
        file: discord.Attachment,
    ) -> None:
        """Restore the SQLite database from an uploaded backup zip, then restart."""
        if not is_bot_admin(interaction.user.id):
            await interaction.response.send_message(
                "You are not allowed to use this command.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        if not file.filename.lower().endswith(".zip"):
            await interaction.followup.send(
                "Please upload a `.zip` backup file.",
                ephemeral=True,
            )
            return

        TEMP_EXTRACT_DIR.mkdir(parents=True, exist_ok=True)

        # Clean up any previous temporary restore files.
        if TEMP_RESTORE_ZIP_PATH.exists():
            TEMP_RESTORE_ZIP_PATH.unlink()

        extracted_db_path = TEMP_EXTRACT_DIR / "bot.db"
        if extracted_db_path.exists():
            extracted_db_path.unlink()

        # Save the uploaded zip file to disk.
        try:
            await file.save(TEMP_RESTORE_ZIP_PATH)
        except Exception as error:
            await interaction.followup.send(
                f"Failed to save uploaded file: `{error}`",
                ephemeral=True,
            )
            return

        # Open the zip and verify that bot.db exists inside it.
        try:
            with zipfile.ZipFile(TEMP_RESTORE_ZIP_PATH, "r") as archive:
                members = archive.namelist()

                if "bot.db" not in members:
                    await interaction.followup.send(
                        "The uploaded zip does not contain a `bot.db` file at its root.",
                        ephemeral=True,
                    )
                    return

                archive.extract("bot.db", path=TEMP_EXTRACT_DIR)
        except zipfile.BadZipFile:
            await interaction.followup.send(
                "That file is not a valid zip archive.",
                ephemeral=True,
            )
            return
        except Exception as error:
            await interaction.followup.send(
                f"Failed to extract backup zip: `{error}`",
                ephemeral=True,
            )
            return

        if not extracted_db_path.exists():
            await interaction.followup.send(
                "Extraction finished, but `bot.db` was not found afterwards.",
                ephemeral=True,
            )
            return

        # Replace the live DB with the restored one.
        # The bot will immediately restart afterwards so SQLite is reopened cleanly.
        try:
            backup_of_current = DB_PATH.with_suffix(".pre_restore.bak")

            if backup_of_current.exists():
                backup_of_current.unlink()

            if DB_PATH.exists():
                DB_PATH.replace(backup_of_current)

            extracted_db_path.replace(DB_PATH)
        except Exception as error:
            await interaction.followup.send(
                f"Failed to replace the live database: `{error}`",
                ephemeral=True,
            )
            return

        await interaction.followup.send(
            "Database restored successfully. Restarting the bot now...",
            ephemeral=True,
        )

        # Force the Railway process to exit so it restarts cleanly
        # and reopens the restored SQLite database.
        os._exit(0)


async def setup(bot: commands.Bot) -> None:
    """Cog loader hook."""
    await bot.add_cog(BotAdminCog(bot))