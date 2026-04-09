from __future__ import annotations

"""Staff moderation commands for controlled overrides on personal roles and rooms."""

from typing import List

import discord
from discord import app_commands
from discord.ext import commands

from services.channels import (
    claim_member_room,
    delete_member_room,
    describe_member_room,
    lock_member_room,
    reset_member_room,
    rename_member_room,
    sync_room_permissions,
    unlock_member_room,
    iter_personal_channel_rows,
)
from services.roles import (
    claim_personal_role,
    delete_personal_role,
    describe_member_role,
    ensure_personal_role,
    rename_personal_role,
    reset_personal_role_colour,
    iter_personal_role_rows,
)
from services.sync_tools import repair_guild_assets
from utils.checks import ensure_guild_interaction, staff_only
from utils.confirmations import confirm_action
from utils.naming import sanitise_channel_name, sanitise_role_name


PAGE_SIZE = 10


class PagedAssetView(discord.ui.View):
    """Simple previous/next pagination view for staff asset listings."""

    def __init__(self, author_id: int, title: str, pages: List[str]) -> None:
        super().__init__(timeout=120)
        self.author_id = author_id
        self.title = title
        self.pages = pages
        self.index = 0

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "Only the command user can control this pagination view.",
                ephemeral=True,
            )
            return False
        return True

    def build_embed(self) -> discord.Embed:
        page_number = self.index + 1
        page_count = len(self.pages)
        embed = discord.Embed(
            title=self.title,
            description=self.pages[self.index] if self.pages else "No entries found.",
        )
        embed.set_footer(text="Page {0}/{1}".format(page_number, page_count if page_count else 1))
        return embed

    def update_buttons(self) -> None:
        self.prev_button.disabled = self.index <= 0
        self.next_button.disabled = self.index >= len(self.pages) - 1

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.index -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.index += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    async def on_timeout(self) -> None:
        for child in self.children:
            child.disabled = True


def chunk_lines(lines: List[str], page_size: int) -> List[str]:
    """Split a list of lines into multiple text pages."""
    pages: List[str] = []
    for start in range(0, len(lines), page_size):
        pages.append("\n".join(lines[start:start + page_size]))
    return pages or ["No entries found."]


def build_room_lines(guild: discord.Guild) -> List[str]:
    """Build one display line per tracked room in the guild."""
    lines: List[str] = []
    for user_id, channel_id in iter_personal_channel_rows(guild.id):
        member = guild.get_member(user_id)
        channel = guild.get_channel(channel_id)
        owner_text = member.mention if member is not None else "<@{0}>".format(user_id)
        if isinstance(channel, discord.TextChannel):
            channel_text = channel.mention
            exists_text = "exists"
        else:
            channel_text = "#{0}".format(channel_id)
            exists_text = "missing"

        lines.append("{0} — {1} — `{2}`".format(owner_text, channel_text, exists_text))
    return lines


def build_role_lines(guild: discord.Guild) -> List[str]:
    """Build one display line per tracked role in the guild."""
    lines: List[str] = []
    for user_id, role_id in iter_personal_role_rows(guild.id):
        member = guild.get_member(user_id)
        role = guild.get_role(role_id)
        owner_text = member.mention if member is not None else "<@{0}>".format(user_id)
        if role is not None:
            role_text = role.mention
            exists_text = "exists"
        else:
            role_text = "@deleted-role ({0})".format(role_id)
            exists_text = "missing"

        lines.append("{0} — {1} — `{2}`".format(owner_text, role_text, exists_text))
    return lines


class StaffCog(commands.Cog):
    """Commands that staff can use to moderate or repair personal assets."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    staff_group = app_commands.Group(name="staff", description="Moderate personal roles and rooms")

    @staff_group.command(name="repair", description="Repair tracked roles and rooms for this server")
    @staff_only()
    @app_commands.describe(dry_run="If true, preview the repair without changing anything")
    async def staff_repair(self, interaction: discord.Interaction, dry_run: bool = False) -> None:
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

    @staff_group.command(name="verify-user", description="Preview what would be fixed for one member")
    @staff_only()
    async def verify_user(self, interaction: discord.Interaction, member: discord.Member) -> None:
        try:
            ensure_guild_interaction(interaction)
        except ValueError as error:
            await interaction.response.send_message(str(error), ephemeral=True)
            return

        room_info = describe_member_room(interaction.guild, member.id)
        role_info = describe_member_role(interaction.guild, member.id)

        lines: List[str] = []
        if role_info["role_id"] is None:
            lines.append("Role: no tracked role record; ensure_personal_role would create one.")
        elif not role_info["exists"]:
            lines.append("Role: tracked role is missing; repair would recreate it.")
        else:
            lines.append("Role: tracked role exists.")

        if room_info["channel_id"] is None:
            lines.append("Room: no tracked room record.")
        elif not room_info["exists"]:
            lines.append("Room: tracked room is missing; repair would recreate it if setup is valid.")
        else:
            lines.append("Room: tracked room exists.")

        await interaction.response.send_message(
            embed=discord.Embed(
                title="Verify User: {0}".format(member),
                description="\n".join(lines),
            ),
            ephemeral=True,
        )

    @staff_group.command(name="sync-user", description="Repair one member's tracked assets after a preview")
    @staff_only()
    async def sync_user(self, interaction: discord.Interaction, member: discord.Member) -> None:
        try:
            ensure_guild_interaction(interaction)
        except ValueError as error:
            await interaction.response.send_message(str(error), ephemeral=True)
            return

        room_info = describe_member_room(interaction.guild, member.id)
        role_info = describe_member_role(interaction.guild, member.id)

        preview_lines: List[str] = []
        if role_info["role_id"] is None or not role_info["exists"]:
            preview_lines.append("Role would be created or repaired.")
        else:
            preview_lines.append("Role already looks valid.")

        if room_info["channel_id"] is None:
            preview_lines.append("No tracked room exists, so room sync would do nothing.")
        elif not room_info["exists"]:
            preview_lines.append("Tracked room would be recreated if the server setup is valid.")
        else:
            preview_lines.append("Tracked room exists; permissions would be resynced.")

        confirmed = await confirm_action(
            interaction,
            "Preview for {0}:\n- {1}\n\nConfirm sync?".format(member.mention, "\n- ".join(preview_lines)),
        )
        if not confirmed:
            await interaction.followup.send("Cancelled.", ephemeral=True)
            return

        role_changed = False
        room_changed = False

        if role_info["role_id"] is None or not role_info["exists"]:
            await ensure_personal_role(member)
            role_changed = True

        if room_info["channel_id"] is not None:
            if not room_info["exists"]:
                try:
                    await reset_member_room(member)
                    room_changed = True
                except RuntimeError as error:
                    await interaction.followup.send(str(error), ephemeral=True)
                    return
            else:
                await sync_room_permissions(member)
                room_changed = True

        await interaction.followup.send(
            "Sync complete for {0}. Role changed: **{1}**. Room changed: **{2}**.".format(
                member.mention,
                "Yes" if role_changed else "No",
                "Yes" if room_changed else "No",
            ),
            ephemeral=True,
        )

    @staff_group.command(name="list-assets", description="List tracked rooms or roles in a paginated embed")
    @staff_only()
    @app_commands.describe(asset_type="Choose whether to list rooms or roles")
    @app_commands.choices(
        asset_type=[
            app_commands.Choice(name="rooms", value="rooms"),
            app_commands.Choice(name="roles", value="roles"),
        ]
    )
    async def list_assets(
        self,
        interaction: discord.Interaction,
        asset_type: str,
    ) -> None:
        try:
            ensure_guild_interaction(interaction)
        except ValueError as error:
            await interaction.response.send_message(str(error), ephemeral=True)
            return

        if asset_type == "rooms":
            lines = build_room_lines(interaction.guild)
            title = "Tracked Rooms"
        else:
            lines = build_role_lines(interaction.guild)
            title = "Tracked Roles"

        pages = chunk_lines(lines, PAGE_SIZE)
        view = PagedAssetView(interaction.user.id, title, pages)
        view.update_buttons()
        await interaction.response.send_message(embed=view.build_embed(), view=view, ephemeral=True)

    @staff_group.command(name="room-info", description="Show another member's tracked room info")
    @staff_only()
    async def room_info_user(self, interaction: discord.Interaction, member: discord.Member) -> None:
        info = describe_member_room(interaction.guild, member.id)
        exists_text = "Yes" if info["exists"] else "No"
        channel_text = "<#{0}>".format(info["channel_id"]) if info["channel_id"] else "Not tracked"
        lock_text = "Locked by staff" if info["locked_by_staff"] else ("Locked by owner" if info["locked"] else "Unlocked")

        embed = discord.Embed(title="Room Info for {0}".format(member))
        embed.add_field(name="Tracked Channel", value=channel_text, inline=False)
        embed.add_field(name="Exists", value=exists_text, inline=True)
        embed.add_field(name="Channel Name", value=info["channel_name"] or "Unknown", inline=True)
        embed.add_field(name="Lock State", value=lock_text, inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @staff_group.command(name="role-info", description="Show another member's tracked role info")
    @staff_only()
    async def role_info_user(self, interaction: discord.Interaction, member: discord.Member) -> None:
        info = describe_member_role(interaction.guild, member.id)
        exists_text = "Yes" if info["exists"] else "No"
        role_text = "<@&{0}>".format(info["role_id"]) if info["role_id"] else "Not tracked"

        embed = discord.Embed(title="Role Info for {0}".format(member))
        embed.add_field(name="Tracked Role", value=role_text, inline=False)
        embed.add_field(name="Exists", value=exists_text, inline=True)
        embed.add_field(name="Role Name", value=info["role_name"] or "Unknown", inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @staff_group.command(name="room-lock", description="Lock another member's room so only staff can send there")
    @staff_only()
    async def room_lock_user(self, interaction: discord.Interaction, member: discord.Member) -> None:
        try:
            channel = await lock_member_room(member, locked_by_staff=True)
        except LookupError as error:
            await interaction.response.send_message(str(error), ephemeral=True)
            return

        await interaction.response.send_message(
            "Staff-locked {0}'s room: {1}".format(member.mention, channel.mention),
            ephemeral=True,
        )

    @staff_group.command(name="room-unlock", description="Unlock another member's room")
    @staff_only()
    async def room_unlock_user(self, interaction: discord.Interaction, member: discord.Member) -> None:
        try:
            channel = await unlock_member_room(member, by_staff=True)
        except (LookupError, PermissionError) as error:
            await interaction.response.send_message(str(error), ephemeral=True)
            return

        await interaction.response.send_message(
            "Unlocked {0}'s room: {1}".format(member.mention, channel.mention),
            ephemeral=True,
        )

    @staff_group.command(name="room-rename", description="Rename another member's tracked room")
    @staff_only()
    async def room_rename_user(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        new_name: str,
    ) -> None:
        try:
            ensure_guild_interaction(interaction)
            clean_name = sanitise_channel_name(new_name)
            channel = await rename_member_room(interaction.guild, member.id, clean_name)
        except (ValueError, LookupError) as error:
            await interaction.response.send_message(str(error), ephemeral=True)
            return

        await interaction.response.send_message(
            "Renamed {0}'s room to {1}.".format(member.mention, channel.mention),
            ephemeral=True,
        )

    @staff_group.command(name="room-delete", description="Delete another member's tracked room")
    @staff_only()
    async def room_delete_user(self, interaction: discord.Interaction, member: discord.Member) -> None:
        try:
            ensure_guild_interaction(interaction)
        except ValueError as error:
            await interaction.response.send_message(str(error), ephemeral=True)
            return

        confirmed = await confirm_action(
            interaction,
            "Confirm deletion of the tracked room for {0}?".format(member.mention),
        )
        if not confirmed:
            await interaction.followup.send("Cancelled.", ephemeral=True)
            return

        await delete_member_room(interaction.guild, member.id)
        await interaction.followup.send(
            "Deleted the tracked room for {0}.".format(member.mention),
            ephemeral=True,
        )

    @staff_group.command(name="room-reset", description="Delete and recreate another member's tracked room")
    @staff_only()
    async def room_reset_user(self, interaction: discord.Interaction, member: discord.Member) -> None:
        confirmed = await confirm_action(
            interaction,
            "Confirm reset of the tracked room for {0}?".format(member.mention),
        )
        if not confirmed:
            await interaction.followup.send("Cancelled.", ephemeral=True)
            return

        try:
            channel = await reset_member_room(member)
        except RuntimeError as error:
            await interaction.followup.send(str(error), ephemeral=True)
            return

        await interaction.followup.send(
            "Reset {0}'s room: {1}".format(member.mention, channel.mention),
            ephemeral=True,
        )

    @staff_group.command(name="color-reset", description="Reset another member's personal role colour")
    @staff_only()
    async def color_reset_user(self, interaction: discord.Interaction, member: discord.Member) -> None:
        await reset_personal_role_colour(member)
        await interaction.response.send_message(
            "Reset the personal role colour for {0}.".format(member.mention),
            ephemeral=True,
        )

    @staff_group.command(name="color-rename", description="Rename another member's personal role")
    @staff_only()
    async def color_rename_user(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        new_name: str,
    ) -> None:
        try:
            clean_name = sanitise_role_name(new_name)
        except ValueError as error:
            await interaction.response.send_message(str(error), ephemeral=True)
            return

        role = await rename_personal_role(member, clean_name)
        await interaction.response.send_message(
            "Renamed {0}'s personal role to **{1}**.".format(member.mention, role.name),
            ephemeral=True,
        )

    @staff_group.command(name="role-delete", description="Delete another member's tracked personal role")
    @staff_only()
    async def role_delete_user(self, interaction: discord.Interaction, member: discord.Member) -> None:
        confirmed = await confirm_action(
            interaction,
            "Confirm deletion of the tracked personal role for {0}?".format(member.mention),
        )
        if not confirmed:
            await interaction.followup.send("Cancelled.", ephemeral=True)
            return

        await delete_personal_role(member)
        await interaction.followup.send(
            "Deleted the tracked personal role for {0}.".format(member.mention),
            ephemeral=True,
        )

    @staff_group.command(name="claim-room", description="Adopt an existing text channel as a member's room")
    @staff_only()
    async def claim_room(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        channel: discord.TextChannel,
    ) -> None:
        claimed = await claim_member_room(member, channel)
        await interaction.response.send_message(
            "Claimed {0} as the tracked room for {1}.".format(claimed.mention, member.mention),
            ephemeral=True,
        )

    @staff_group.command(name="claim-role", description="Adopt an existing role as a member's personal role")
    @staff_only()
    async def claim_role(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        role: discord.Role,
    ) -> None:
        await claim_personal_role(member, role)
        await interaction.response.send_message(
            "Claimed **{0}** as the tracked personal role for {1}.".format(role.name, member.mention),
            ephemeral=True,
        )

    @staff_repair.error
    @verify_user.error
    @sync_user.error
    @list_assets.error
    @room_info_user.error
    @role_info_user.error
    @room_lock_user.error
    @room_unlock_user.error
    @room_rename_user.error
    @room_delete_user.error
    @room_reset_user.error
    @color_reset_user.error
    @color_rename_user.error
    @role_delete_user.error
    @claim_room.error
    @claim_role.error
    async def staff_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
        if isinstance(error, app_commands.errors.CheckFailure):
            message = (
                "You need the configured staff role or **Manage Server** permission "
                "to use staff commands."
            )
            if interaction.response.is_done():
                await interaction.followup.send(message, ephemeral=True)
            else:
                await interaction.response.send_message(message, ephemeral=True)
            return

        raise error


async def setup(bot: commands.Bot) -> None:
    """Cog loader hook."""
    await bot.add_cog(StaffCog(bot))
