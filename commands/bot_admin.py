"""Bot-owner-only slash commands."""

from __future__ import annotations

import zipfile
from pathlib import Path

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

from config import settings


DB_PATH = Path("/data/bot.db")
ZIP_PATH = Path("/data/bot-backup.zip")


def is_bot_admin(user_id: int) -> bool:
    """Return True if the given user ID is in the bot-admin allowlist."""
    return user_id in settings.bot_admin_ids


class BotAdminCog(commands.Cog):
    """Commands reserved for the owners of the bot."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    # Important: the attribute name must NOT start with "bot_"
    # The slash command group name can still be "bot"
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

    @admin_group.command(name="backup-db", description="Zip and upload the live database")
    async def backup_db(self, interaction: discord.Interaction) -> None:
        """Create a zipped database backup and upload it to transfer.sh."""
        if not is_bot_admin(interaction.user.id):
            await interaction.response.send_message(
                "You are not allowed to use this command.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        if not DB_PATH.exists():
            await interaction.followup.send("Database file was not found.", ephemeral=True)
            return

        ZIP_PATH.parent.mkdir(parents=True, exist_ok=True)

        if ZIP_PATH.exists():
            ZIP_PATH.unlink()

        with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.write(DB_PATH, arcname="bot.db")

        file_size = ZIP_PATH.stat().st_size
        file_size_mb = round(file_size / (1024 * 1024), 2)

        try:
            async with aiohttp.ClientSession() as session:
                with ZIP_PATH.open("rb") as file_handle:
                    async with session.put("https://transfer.sh/bot-backup.zip", data=file_handle) as response:
                        response_text = (await response.text()).strip()

            if not response_text.startswith("http"):
                await interaction.followup.send(
                    f"Backup zip was created ({file_size_mb} MB), but upload failed.\nResponse: `{response_text}`",
                    ephemeral=True,
                )
                return

            await interaction.followup.send(
                (
                    f"Backup created and uploaded.\n"
                    f"- Size: **{file_size_mb} MB**\n"
                    f"- Download: {response_text}\n\n"
                    f"Treat this link as sensitive and remove this command after use."
                ),
                ephemeral=True,
            )

        except Exception as error:
            await interaction.followup.send(
                f"Backup zip was created ({file_size_mb} MB), but upload failed: `{error}`",
                ephemeral=True,
            )


async def setup(bot: commands.Bot) -> None:
    """Cog loader hook."""
    await bot.add_cog(BotAdminCog(bot))