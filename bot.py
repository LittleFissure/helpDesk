"""Application entry point for the multi-server Discord personal rooms bot."""

from __future__ import annotations

import asyncio
import logging

import discord
from discord.ext import commands

from config import settings
from db import init_db
from commands.bot_admin import BotAdminCog
from commands.color import ColorCog
from commands.help import HelpCog
from commands.room import RoomCog
from commands.setup import SetupCog
from commands.staff import StaffCog
from services.roles import ensure_personal_role

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready() -> None:
    """Run once after the bot has connected successfully."""
    logger.info("Logged in as %s (%s)", bot.user, bot.user.id if bot.user else "unknown")
    synced = await bot.tree.sync()
    logger.info("Synced %s global command(s)", len(synced))


@bot.event
async def on_member_join(member: discord.Member) -> None:
    """Create and assign a personal colour role for a newly joined member."""
    await ensure_personal_role(member)


async def main() -> None:
    """Initialise the database, register cogs, and start the bot."""
    await asyncio.sleep(5)

    init_db()
    await bot.add_cog(ColorCog(bot))
    await bot.add_cog(RoomCog(bot))
    await bot.add_cog(SetupCog(bot))
    await bot.add_cog(StaffCog(bot))
    await bot.add_cog(HelpCog(bot))
    await bot.add_cog(BotAdminCog(bot))

    await bot.start(settings.bot_token)


if __name__ == "__main__":
    asyncio.run(main())