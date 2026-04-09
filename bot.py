from __future__ import annotations

"""Application entry point for the multi-server Discord personal rooms bot."""

import logging

import discord
from discord.ext import commands

from config import settings
from db import init_db
from commands.color import ColorCog
from commands.help import HelpCog
from commands.room import RoomCog
from commands.setup import SetupCog
from commands.staff import StaffCog
from services.channels import archive_member_room
from services.roles import delete_personal_role, ensure_personal_role

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    """Run once after the bot has connected successfully."""
    logger.info("Logged in as %s (%s)", bot.user, bot.user.id if bot.user else "unknown")
    synced = await bot.tree.sync()
    logger.info("Synced %s global command(s)", len(synced))


@bot.event
async def on_member_join(member):
    """Create and assign a personal colour role for a newly joined member."""
    await ensure_personal_role(member)


@bot.event
async def on_member_remove(member):
    """Archive the departing member's room and delete their tracked role."""
    await archive_member_room(member)
    await delete_personal_role(member)


async def main():
    """Initialise the database, register cogs, and start the bot."""
    init_db()
    await bot.add_cog(ColorCog(bot))
    await bot.add_cog(RoomCog(bot))
    await bot.add_cog(SetupCog(bot))
    await bot.add_cog(StaffCog(bot))
    await bot.add_cog(HelpCog(bot))
    await bot.start(settings.bot_token)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
