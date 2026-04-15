"""Help commands for showing command lists and command-specific guidance."""

from __future__ import annotations

from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from config import settings
from services.guild_settings import get_guild_settings


def is_bot_admin(user_id: int) -> bool:
    """Return True if the user is a bot admin."""
    return user_id in settings.bot_admin_ids


def can_use_setup(interaction: discord.Interaction) -> bool:
    """Return True if the user can use setup commands."""
    if interaction.guild is None:
        return False

    member = interaction.user
    if not isinstance(member, discord.Member):
        return False

    return member.guild_permissions.manage_guild


def can_use_staff(interaction: discord.Interaction) -> bool:
    """Return True if the user can use staff commands."""
    if interaction.guild is None:
        return False

    member = interaction.user
    if not isinstance(member, discord.Member):
        return False

    settings_row = get_guild_settings(interaction.guild.id)
    staff_role_id = settings_row.get("staff_role_id")

    if not staff_role_id:
        return False

    return any(role.id == staff_role_id for role in member.roles)


HELP_ENTRIES = {
    "/help": {
        "summary": "Show all commands you can use or detailed help for one command.",
        "usage": "/help [command]",
        "details": "Use `/help` for your visible commands, or `/help command:/room create` for one command.",
        "scope": "user",
    },
    "/color set": {
        "summary": "Set your personal role colour using a hex code.",
        "usage": "/color set <hex_code>",
        "details": "Creates your personal role if needed, then updates its colour.",
        "scope": "user",
    },
    "/color reset": {
        "summary": "Reset your personal role back to Discord's default colour.",
        "usage": "/color reset",
        "details": "Keeps your personal role but removes the custom colour.",
        "scope": "user",
    },
    "/color rename": {
        "summary": "Rename your personal role.",
        "usage": "/color rename <new_name>",
        "details": "Only affects your tracked role in the current server.",
        "scope": "user",
    },
    "/color info": {
        "summary": "Show information about your tracked personal role.",
        "usage": "/color info",
        "details": "Shows your tracked role name, existence, and current colour.",
        "scope": "user",
    },
    "/room create": {
        "summary": "Create your public personal room.",
        "usage": "/room create",
        "details": "Requires the server to have a configured personal-room category.",
        "scope": "user",
    },
    "/room rename": {
        "summary": "Rename your personal room.",
        "usage": "/room rename <new_name>",
        "details": "Only renames the room tracked as yours in the current server.",
        "scope": "user",
    },
    "/room info": {
        "summary": "Show information about your tracked room.",
        "usage": "/room info",
        "details": "Shows whether your tracked room exists and whether it is locked.",
        "scope": "user",
    },
    "/room lock": {
        "summary": "Lock your personal room while keeping your own messaging access.",
        "usage": "/room lock",
        "details": "Owner locks still allow the owner to send messages.",
        "scope": "user",
    },
    "/room unlock": {
        "summary": "Unlock your personal room.",
        "usage": "/room unlock",
        "details": "If staff applied the lock, only staff can remove it.",
        "scope": "user",
    },
    "/setup category": {
        "summary": "Set the category used for personal rooms.",
        "usage": "/setup category <category>",
        "details": "Administrator-only. Stores the room category for this server.",
        "scope": "setup",
    },
    "/setup archive-category": {
        "summary": "Set the archive category for archived rooms.",
        "usage": "/setup archive-category <category>",
        "details": "Administrator-only. Stores the archive category for this server.",
        "scope": "setup",
    },
    "/setup log-channel": {
        "summary": "Set the log channel for bot events.",
        "usage": "/setup log-channel <channel>",
        "details": "Administrator-only. Stores the log channel for this server.",
        "scope": "setup",
    },
    "/setup create-category": {
        "summary": "Create and register a category for personal rooms.",
        "usage": "/setup create-category [name]",
        "details": "Administrator-only. Creates the room category and stores it.",
        "scope": "setup",
    },
    "/setup staff-role": {
        "summary": "Set the staff role used by this bot.",
        "usage": "/setup staff-role <role>",
        "details": "Administrator-only. Sets the staff role for this server.",
        "scope": "setup",
    },
    "/setup show": {
        "summary": "Show this server's stored bot configuration.",
        "usage": "/setup show",
        "details": "Administrator-only. Shows configured categories, roles, and log channel.",
        "scope": "setup",
    },
    "/setup sync-members": {
        "summary": "Backfill personal roles for current members.",
        "usage": "/setup sync-members",
        "details": "Administrator-only. Creates missing tracked roles for members already in the server.",
        "scope": "setup",
    },
    "/setup repair": {
        "summary": "Repair missing or broken tracked assets.",
        "usage": "/setup repair",
        "details": "Administrator-only. Recreates or cleans tracked rooms and roles where possible.",
        "scope": "setup",
    },
    "/setup diagnostics": {
        "summary": "Show deeper server diagnostics.",
        "usage": "/setup diagnostics",
        "details": "Administrator-only. Useful for checking stored config and tracked assets.",
        "scope": "setup",
    },
    "/staff repair": {
        "summary": "Run repair actions as staff.",
        "usage": "/staff repair",
        "details": "Staff-only. Repairs tracked assets in the current server.",
        "scope": "staff",
    },
    "/staff verify-user": {
        "summary": "Verify one user's tracked assets.",
        "usage": "/staff verify-user <member>",
        "details": "Staff-only. Checks whether tracked room and role state looks correct.",
        "scope": "staff",
    },
    "/staff sync-user": {
        "summary": "Sync one user's tracked assets.",
        "usage": "/staff sync-user <member>",
        "details": "Staff-only. Rebuilds or re-syncs tracked room and role state for one user.",
        "scope": "staff",
    },
    "/staff list-assets": {
        "summary": "List tracked assets in the current server.",
        "usage": "/staff list-assets",
        "details": "Staff-only. Shows tracked room and role data for review.",
        "scope": "staff",
    },
    "/staff room-info": {
        "summary": "Show tracked room details for a user.",
        "usage": "/staff room-info <member>",
        "details": "Staff-only. Shows the tracked room, lock state, and lock owner.",
        "scope": "staff",
    },
    "/staff room-lock": {
        "summary": "Lock a user's room as staff.",
        "usage": "/staff room-lock <member>",
        "details": "Staff-only. Staff locks mute the owner as well.",
        "scope": "staff",
    },
    "/staff room-unlock": {
        "summary": "Unlock a user's room as staff.",
        "usage": "/staff room-unlock <member>",
        "details": "Staff-only. Removes staff-applied room locks.",
        "scope": "staff",
    },
    "/staff room-rename": {
        "summary": "Rename a user's tracked room.",
        "usage": "/staff room-rename <member> <new_name>",
        "details": "Staff-only. Renames the tracked room directly.",
        "scope": "staff",
    },
    "/staff room-delete": {
        "summary": "Delete a user's tracked room.",
        "usage": "/staff room-delete <member>",
        "details": "Staff-only. Deletes the tracked room and clears the record.",
        "scope": "staff",
    },
    "/staff room-reset": {
        "summary": "Rebuild a user's tracked room.",
        "usage": "/staff room-reset <member>",
        "details": "Staff-only. Deletes the old room and creates a replacement.",
        "scope": "staff",
    },
    "/staff role-info": {
        "summary": "Show tracked role information for a user.",
        "usage": "/staff role-info <member>",
        "details": "Staff-only. Shows tracked role existence and colour.",
        "scope": "staff",
    },
    "/staff color-reset": {
        "summary": "Reset a user's tracked role colour.",
        "usage": "/staff color-reset <member>",
        "details": "Staff-only. Resets the tracked role back to default colour.",
        "scope": "staff",
    },
    "/staff color-rename": {
        "summary": "Rename a user's tracked role.",
        "usage": "/staff color-rename <member> <new_name>",
        "details": "Staff-only. Renames the tracked personal role.",
        "scope": "staff",
    },
    "/staff color-set": {
        "summary": "Set a user's tracked role colour.",
        "usage": "/staff color-set <member> <hex_code>",
        "details": "Staff-only. Sets the tracked role colour directly.",
        "scope": "staff",
    },
    "/staff role-delete": {
        "summary": "Delete a user's tracked role.",
        "usage": "/staff role-delete <member>",
        "details": "Staff-only. Deletes the tracked role and clears or repairs the record.",
        "scope": "staff",
    },
    "/staff claim-room": {
        "summary": "Claim an existing channel as a user's tracked room.",
        "usage": "/staff claim-room <member> <channel>",
        "details": "Staff-only. Adopts an existing channel as the official tracked room.",
        "scope": "staff",
    },
    "/staff claim-role": {
        "summary": "Claim an existing role as a user's tracked role.",
        "usage": "/staff claim-role <member> <role>",
        "details": "Staff-only. Adopts an existing role as the official tracked role.",
        "scope": "staff",
    },
    "/staff color-block": {
        "summary": "Block a user from changing their own role customisation.",
        "usage": "/staff color-block <member>",
        "details": "Staff-only. Prevents `/color set`, `/color reset`, and `/color rename`.",
        "scope": "staff",
    },
    "/staff color-unblock": {
        "summary": "Remove a user's role customisation block.",
        "usage": "/staff color-unblock <member>",
        "details": "Staff-only. Removes the user's colour customisation block.",
        "scope": "staff",
    },
    "/staff room-block": {
        "summary": "Block a user from renaming their own room.",
        "usage": "/staff room-block <member>",
        "details": "Staff-only. Prevents `/room rename`.",
        "scope": "staff",
    },
    "/staff room-unblock": {
        "summary": "Remove a user's room customisation block.",
        "usage": "/staff room-unblock <member>",
        "details": "Staff-only. Removes the user's room block.",
        "scope": "staff",
    },
    "/staff user-info": {
        "summary": "Show a detailed overview of a user in this server.",
        "usage": "/staff user-info <member>",
        "details": "Staff-only. Shows tracked assets, lock state, blocks, and privilege state.",
        "scope": "staff",
    },
    "/bot status": {
        "summary": "Show basic global bot status.",
        "usage": "/bot status",
        "details": "Bot-admin-only. Shows latency, uptime, DB path, and maintenance state.",
        "scope": "bot",
    },
    "/bot stats": {
        "summary": "Show global tracked-data counts.",
        "usage": "/bot stats",
        "details": "Bot-admin-only. Shows total tracked roles, rooms, locks, and blocks.",
        "scope": "bot",
    },
    "/bot guilds": {
        "summary": "List all guilds the bot is in.",
        "usage": "/bot guilds",
        "details": "Bot-admin-only. Shows guild IDs and member counts.",
        "scope": "bot",
    },
    "/bot guild-info": {
        "summary": "Show detailed info for one guild.",
        "usage": "/bot guild-info <guild_id>",
        "details": "Bot-admin-only. Shows configuration and tracked counts for one guild.",
        "scope": "bot",
    },
    "/bot maintenance-on": {
        "summary": "Enable maintenance mode.",
        "usage": "/bot maintenance-on [message]",
        "details": "Bot-admin-only. Stores a maintenance flag and message.",
        "scope": "bot",
    },
    "/bot maintenance-off": {
        "summary": "Disable maintenance mode.",
        "usage": "/bot maintenance-off",
        "details": "Bot-admin-only. Clears the maintenance flag.",
        "scope": "bot",
    },
    "/bot maintenance-status": {
        "summary": "Show maintenance mode state.",
        "usage": "/bot maintenance-status",
        "details": "Bot-admin-only. Shows whether maintenance mode is enabled.",
        "scope": "bot",
    },
    "/bot resync-commands": {
        "summary": "Force a global slash-command resync.",
        "usage": "/bot resync-commands",
        "details": "Bot-admin-only. Resyncs the slash-command tree with Discord.",
        "scope": "bot",
    },
    "/bot backup-db": {
        "summary": "Create and send a zipped database backup.",
        "usage": "/bot backup-db",
        "details": "Bot-admin-only. Zips `/data/bot.db` and sends it back through Discord.",
        "scope": "bot",
    },
    "/bot restore-db": {
        "summary": "Restore the live database from a backup zip.",
        "usage": "/bot restore-db <file>",
        "details": "Bot-admin-only. Overwrites the live DB from an uploaded backup and restarts the bot.",
        "scope": "bot",
    },
}


def can_access_command(interaction: discord.Interaction, command_name: str) -> bool:
    """Return True if the user should see help for the given command."""
    entry = HELP_ENTRIES.get(command_name)
    if entry is None:
        return False

    scope = entry["scope"]

    if scope == "user":
        return True
    if scope == "setup":
        return can_use_setup(interaction)
    if scope == "staff":
        return can_use_staff(interaction)
    if scope == "bot":
        return is_bot_admin(interaction.user.id)

    return False


def build_command_list_embed(interaction: discord.Interaction) -> discord.Embed:
    """Create a help embed that only shows commands the user can access."""
    embed = discord.Embed(
        title="Bot Help",
        description="Use `/help command:<command name>` for details about one command.",
    )

    user_commands = [
        "/help",
        "/color set",
        "/color reset",
        "/color rename",
        "/color info",
        "/room create",
        "/room rename",
        "/room info",
        "/room lock",
        "/room unlock",
    ]
    embed.add_field(
        name="User Commands",
        value="\n".join("`{0}`".format(cmd) for cmd in user_commands),
        inline=False,
    )

    if can_use_setup(interaction):
        setup_commands = [
            "/setup category",
            "/setup archive-category",
            "/setup log-channel",
            "/setup create-category",
            "/setup staff-role",
            "/setup show",
            "/setup sync-members",
            "/setup repair",
            "/setup diagnostics",
        ]
        embed.add_field(
            name="Admin Commands",
            value="\n".join("`{0}`".format(cmd) for cmd in setup_commands),
            inline=False,
        )

    if can_use_staff(interaction):
        staff_commands = [
            "/staff repair",
            "/staff verify-user",
            "/staff sync-user",
            "/staff list-assets",
            "/staff room-info",
            "/staff room-lock",
            "/staff room-unlock",
            "/staff room-rename",
            "/staff room-delete",
            "/staff room-reset",
            "/staff role-info",
            "/staff color-reset",
            "/staff color-rename",
            "/staff color-set",
            "/staff role-delete",
            "/staff claim-room",
            "/staff claim-role",
            "/staff color-block",
            "/staff color-unblock",
            "/staff room-block",
            "/staff room-unblock",
            "/staff user-info",
        ]
        embed.add_field(
            name="Staff Commands",
            value="\n".join("`{0}`".format(cmd) for cmd in staff_commands),
            inline=False,
        )

    if is_bot_admin(interaction.user.id):
        bot_commands = [
            "/bot status",
            "/bot stats",
            "/bot guilds",
            "/bot guild-info",
            "/bot maintenance-on",
            "/bot maintenance-off",
            "/bot maintenance-status",
            "/bot resync-commands",
            "/bot backup-db",
            "/bot restore-db",
        ]
        embed.add_field(
            name="Bot Admin Commands",
            value="\n".join("`{0}`".format(cmd) for cmd in bot_commands),
            inline=False,
        )

    return embed


def build_command_help_embed(interaction: discord.Interaction, command_name: str):
    """Create a detailed help embed for one command if the user can access it."""
    if not can_access_command(interaction, command_name):
        return None

    entry = HELP_ENTRIES.get(command_name)
    if entry is None:
        return None

    embed = discord.Embed(title="Help: {0}".format(command_name))
    embed.add_field(name="What it does", value=entry["summary"], inline=False)
    embed.add_field(name="Usage", value="`{0}`".format(entry["usage"]), inline=False)
    embed.add_field(name="Details", value=entry["details"], inline=False)
    return embed


class HelpCog(commands.Cog):
    """Slash help command with overview and per-command detail modes."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="help", description="List commands or show help for one command")
    @app_commands.describe(command="Optional command path, for example /room create")
    async def help_command(self, interaction: discord.Interaction, command: Optional[str] = None) -> None:
        """Show the commands the user can access, or details for one command."""
        if not command:
            await interaction.response.send_message(
                embed=build_command_list_embed(interaction),
                ephemeral=True,
            )
            return

        cleaned = command.strip()
        if not cleaned.startswith("/"):
            cleaned = "/" + cleaned

        embed = build_command_help_embed(interaction, cleaned)
        if embed is None:
            await interaction.response.send_message(
                "Unknown command.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    """Cog loader hook."""
    await bot.add_cog(HelpCog(bot))