from __future__ import annotations

"""Help commands for showing a command list and command-specific guidance."""

from typing import List, Optional

import discord
from discord import app_commands
from discord.ext import commands


HELP_ENTRIES = {
    "/help": {"summary": "Show all commands or detailed help for one command.", "usage": "/help [command]", "details": "Run `/help` by itself to see the full command list."},
    "/color set": {"summary": "Set your personal role colour using a hex code.", "usage": "/color set <hex_code>", "details": "Creates your personal role if it does not exist yet, then updates its colour. Blocked users cannot use this command."},
    "/color reset": {"summary": "Reset your personal role back to Discord's default colour.", "usage": "/color reset", "details": "Keeps your personal role but removes the custom colour."},
    "/color rename": {"summary": "Rename your personal role.", "usage": "/color rename <new_name>", "details": "Lets you rename only your tracked personal role in the current server. Blocked users cannot use this command."},
    "/color info": {"summary": "Show your tracked personal role information.", "usage": "/color info", "details": "Displays the tracked role ID, existence state, and current name."},
    "/room create": {"summary": "Create your public personal room in the configured category.", "usage": "/room create", "details": "Creates one tracked room for you in the current server. Blocked users cannot use this command."},
    "/room rename": {"summary": "Rename your personal room.", "usage": "/room rename <new_name>", "details": "Only renames the room tracked as yours in the current server. Blocked users cannot use this command."},
    "/room info": {"summary": "Show your tracked personal room information.", "usage": "/room info", "details": "Displays the tracked room ID, existence state, current name, and lock state."},
    "/room lock": {"summary": "Lock your room so only staff can send messages there.", "usage": "/room lock", "details": "Public visibility stays on, but only staff can talk while the room is locked."},
    "/room unlock": {"summary": "Unlock your room.", "usage": "/room unlock", "details": "If staff locked the room, only staff can unlock it."},
    "/setup category": {"summary": "Set the category used for personal rooms.", "usage": "/setup category <category>", "details": "Administrator-only. Stores the chosen category for the current server."},
    "/setup archive-category": {"summary": "Set the category used for archived rooms.", "usage": "/setup archive-category <category>", "details": "Administrator-only. Rooms are moved here when members leave."},
    "/setup log-channel": {"summary": "Set the channel used for bot audit logs.", "usage": "/setup log-channel <channel>", "details": "Administrator-only. Sends bot audit embeds to the chosen text channel."},
    "/setup create-category": {"summary": "Create and register a category for personal rooms.", "usage": "/setup create-category [name]", "details": "Administrator-only. Creates a category, then stores it as the room target."},
    "/setup staff-role": {"summary": "Set the staff role that keeps moderation access in personal rooms.", "usage": "/setup staff-role <role>", "details": "Administrator-only. Lets one role keep moderation access across personal rooms."},
    "/setup show": {"summary": "Show this server's stored bot configuration.", "usage": "/setup show", "details": "Administrator-only. Displays the stored room category, archive category, staff role, and log channel."},
    "/setup sync-members": {"summary": "Backfill personal roles for members already in the server.", "usage": "/setup sync-members", "details": "Administrator-only. Scans current members and ensures each non-bot member has a tracked personal role."},
    "/setup repair": {"summary": "Repair or preview missing roles and rooms from stored records.", "usage": "/setup repair [dry_run]", "details": "Administrator-only. Repairs tracked assets or previews the repair without changing anything."},
    "/setup diagnostics": {"summary": "Check bot readiness and current configuration.", "usage": "/setup diagnostics", "details": "Administrator-only. Verifies permissions, category config, and staff-role config."},
    "/staff repair": {"summary": "Repair or preview tracked roles and rooms for the current server.", "usage": "/staff repair [dry_run]", "details": "Staff-only. Runs the repair flow used for broken tracked roles and rooms."},
    "/staff verify-user": {"summary": "Preview what would be fixed for one member.", "usage": "/staff verify-user <member>", "details": "Staff-only. Shows a lightweight preview before syncing a single member."},
    "/staff sync-user": {"summary": "Repair one member's tracked assets after a preview.", "usage": "/staff sync-user <member>", "details": "Staff-only. Shows a preview in the confirmation prompt, then applies the per-user repair."},
    "/staff list-assets": {"summary": "List tracked rooms or roles in a paginated embed.", "usage": "/staff list-assets <rooms|roles>", "details": "Staff-only. Shows tracked rooms or roles in a paginated embedded message with previous/next buttons."},
    "/staff room-info": {"summary": "Show another member's tracked room info.", "usage": "/staff room-info <member>", "details": "Staff-only. Displays tracking details for a member's room."},
    "/staff role-info": {"summary": "Show another member's tracked role info.", "usage": "/staff role-info <member>", "details": "Staff-only. Displays tracking details for a member's role."},
    "/staff user-info": {"summary": "Show a detailed combined overview for one member.", "usage": "/staff user-info <member>", "details": "Staff-only. Shows tracked room and role state, lock state, who locked the room, blocked state, and who blocked the member."},
    "/staff room-lock": {"summary": "Lock another member's room so only staff can speak there.", "usage": "/staff room-lock <member>", "details": "Staff-only. A staff-created lock can only be removed by staff."},
    "/staff room-unlock": {"summary": "Unlock another member's room.", "usage": "/staff room-unlock <member>", "details": "Staff-only. Removes any lock state from the tracked room."},
    "/staff room-rename": {"summary": "Rename another member's tracked room.", "usage": "/staff room-rename <member> <new_name>", "details": "Staff-only. Useful for fixing inappropriate or messy channel names."},
    "/staff room-delete": {"summary": "Delete another member's tracked room.", "usage": "/staff room-delete <member>", "details": "Staff-only. Requires confirmation before deleting the tracked room and clearing the record."},
    "/staff room-reset": {"summary": "Delete and recreate another member's tracked room.", "usage": "/staff room-reset <member>", "details": "Staff-only. Requires confirmation before resetting the tracked room."},
    "/staff color-set": {"summary": "Set another member's personal role colour using a hex code.", "usage": "/staff color-set <member> <hex_code>", "details": "Staff-only. Creates the tracked role if needed, then updates its colour."},
    "/staff color-reset": {"summary": "Reset another member's personal role colour.", "usage": "/staff color-reset <member>", "details": "Staff-only. Keeps the role but removes the custom colour."},
    "/staff color-rename": {"summary": "Rename another member's personal role.", "usage": "/staff color-rename <member> <new_name>", "details": "Staff-only. Useful for fixing inappropriate role names."},
    "/staff role-delete": {"summary": "Delete another member's tracked personal role.", "usage": "/staff role-delete <member>", "details": "Staff-only. Requires confirmation before deleting the tracked personal role."},
    "/staff claim-room": {"summary": "Adopt an existing text channel as a member's tracked room.", "usage": "/staff claim-room <member> <channel>", "details": "Staff-only. Applies personal-room overwrites and stores channel ownership."},
    "/staff claim-role": {"summary": "Adopt an existing role as a member's tracked personal role.", "usage": "/staff claim-role <member> <role>", "details": "Staff-only. Stores the role ownership and assigns the role if needed."},
    "/staff block-user": {"summary": "Block a member from selected self-service room and role commands.", "usage": "/staff block-user <member>", "details": "Staff-only. Blocks /room create, /room rename, /color set, and /color rename. Staff and admins are immune."},
    "/staff unblock-user": {"summary": "Remove a member block for selected self-service commands.", "usage": "/staff unblock-user <member>", "details": "Staff-only. Restores access to blocked self-service room and role commands."},
}


def build_command_list_embed() -> discord.Embed:
    embed = discord.Embed(
        title="Bot Help",
        description="Use `/help command:<command name>` for details about one command.",
    )

    embed.add_field(
        name="User Commands",
        value="`/help`\n`/color set`\n`/color reset`\n`/color rename`\n`/color info`\n`/room create`\n`/room rename`\n`/room info`\n`/room lock`\n`/room unlock`",
        inline=False,
    )
    embed.add_field(
        name="Staff Commands",
        value="`/staff repair`\n`/staff verify-user`\n`/staff sync-user`\n`/staff list-assets`\n`/staff room-info`\n`/staff role-info`\n`/staff user-info`\n`/staff room-lock`\n`/staff room-unlock`\n`/staff room-rename`\n`/staff room-delete`\n`/staff room-reset`\n`/staff color-set`\n`/staff color-reset`\n`/staff color-rename`\n`/staff role-delete`\n`/staff claim-room`\n`/staff claim-role`\n`/staff block-user`\n`/staff unblock-user`",
        inline=False,
    )
    embed.add_field(
        name="Admin Commands",
        value="`/setup category`\n`/setup archive-category`\n`/setup log-channel`\n`/setup create-category`\n`/setup staff-role`\n`/setup show`\n`/setup sync-members`\n`/setup repair`\n`/setup diagnostics`",
        inline=False,
    )
    return embed


def build_command_help_embed(command_name: str) -> Optional[discord.Embed]:
    entry = HELP_ENTRIES.get(command_name)
    if entry is None:
        return None

    embed = discord.Embed(title="Help: {0}".format(command_name))
    embed.add_field(name="What it does", value=entry["summary"], inline=False)
    embed.add_field(name="Usage", value="`{0}`".format(entry["usage"]), inline=False)
    embed.add_field(name="Details", value=entry["details"], inline=False)
    return embed


class HelpCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def command_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> List[app_commands.Choice[str]]:
        current_lower = current.lower().strip()
        choices: List[app_commands.Choice[str]] = []
        for name in sorted(HELP_ENTRIES.keys()):
            if current_lower in name.lower():
                choices.append(app_commands.Choice(name=name, value=name))
            if len(choices) >= 25:
                break
        return choices

    @app_commands.command(name="help", description="List commands or show help for one command")
    @app_commands.describe(command="Optional command path, for example /room create")
    @app_commands.autocomplete(command=command_autocomplete)
    async def help_command(
        self,
        interaction: discord.Interaction,
        command: Optional[str] = None,
    ) -> None:
        if not command:
            await interaction.response.send_message(
                embed=build_command_list_embed(),
                ephemeral=True,
            )
            return

        cleaned = command.strip()
        if not cleaned.startswith("/"):
            cleaned = "/{0}".format(cleaned)

        embed = build_command_help_embed(cleaned)
        if embed is None:
            known = ", ".join(sorted(HELP_ENTRIES.keys()))
            await interaction.response.send_message(
                "Unknown command. Try one of: {0}".format(known),
                ephemeral=True,
            )
            return

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(HelpCog(bot))
