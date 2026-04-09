from __future__ import annotations

"""Channel-related service functions."""

import discord

from db import get_connection
from services.guild_settings import get_guild_settings
from services.logging_service import log_event


def get_personal_channel_id(guild_id, user_id):
    """Return the stored personal channel ID for the given user in the given guild, if any."""
    with get_connection() as connection:
        row = connection.execute(
            "SELECT channel_id FROM personal_channels WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        ).fetchone()
    return int(row["channel_id"]) if row else None


def save_personal_channel_id(guild_id, user_id, channel_id):
    """Insert or update the stored personal channel mapping for the user in this guild."""
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO personal_channels (guild_id, user_id, channel_id)
            VALUES (?, ?, ?)
            ON CONFLICT(guild_id, user_id) DO UPDATE SET channel_id = excluded.channel_id
            """,
            (guild_id, user_id, channel_id),
        )
        connection.commit()


def clear_personal_channel_id(guild_id, user_id):
    """Remove a stored personal room record for one user."""
    with get_connection() as connection:
        connection.execute(
            "DELETE FROM personal_channels WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        )
        connection.execute(
            "DELETE FROM room_locks WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        )
        connection.commit()


def iter_personal_channel_rows(guild_id):
    """Return all stored user/channel pairs for one guild."""
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT user_id, channel_id FROM personal_channels WHERE guild_id = ?",
            (guild_id,),
        ).fetchall()
    return [(int(row["user_id"]), int(row["channel_id"])) for row in rows]


def get_member_room(guild, user_id):
    """Return the member's stored text channel in this guild if it still exists."""
    channel_id = get_personal_channel_id(guild.id, user_id)
    if not channel_id:
        return None

    channel = guild.get_channel(channel_id)
    return channel if isinstance(channel, discord.TextChannel) else None


def get_room_lock_state(guild_id, user_id):
    """Return whether a room is locked, whether staff created that lock, and who locked it."""
    with get_connection() as connection:
        row = connection.execute(
            "SELECT locked_by_staff, lock_actor_id FROM room_locks WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        ).fetchone()
    if row is None:
        return {"locked": False, "locked_by_staff": False, "lock_actor_id": None}
    return {
        "locked": True,
        "locked_by_staff": bool(row["locked_by_staff"]),
        "lock_actor_id": int(row["lock_actor_id"]) if row["lock_actor_id"] else None,
    }


def set_room_lock_state(guild_id, user_id, locked_by_staff, actor_id):
    """Store that a room is locked, whether staff created the lock, and who applied it."""
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO room_locks (guild_id, user_id, locked_by_staff, lock_actor_id)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(guild_id, user_id)
            DO UPDATE SET locked_by_staff = excluded.locked_by_staff, lock_actor_id = excluded.lock_actor_id
            """,
            (guild_id, user_id, 1 if locked_by_staff else 0, actor_id),
        )
        connection.commit()


def clear_room_lock_state(guild_id, user_id):
    """Remove any stored lock state for a user's room."""
    with get_connection() as connection:
        connection.execute(
            "DELETE FROM room_locks WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        )
        connection.commit()


def build_room_overwrites(guild, member):
    """Build the permission overwrites for a public personal room."""
    guild_settings = get_guild_settings(guild.id)
    lock_state = get_room_lock_state(guild.id, member.id)
    locked = lock_state["locked"]

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=False if locked else True,
            read_message_history=True,
            add_reactions=False if locked else True,
            attach_files=False if locked else True,
            embed_links=False if locked else True,
            pin_messages=False,
        ),
        member: discord.PermissionOverwrite(
            send_messages=False if locked else True,
            add_reactions=False if locked else True,
            attach_files=False if locked else True,
            embed_links=False if locked else True,
            pin_messages=True,
            manage_messages=False,
            manage_channels=False,
            manage_permissions=False,
        ),
    }

    staff_role_id = guild_settings["staff_role_id"]
    if staff_role_id:
        staff_role = guild.get_role(staff_role_id)
        if staff_role is not None:
            overwrites[staff_role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                add_reactions=True,
                attach_files=True,
                embed_links=True,
                pin_messages=True,
                manage_messages=True,
                manage_channels=False,
                manage_permissions=False,
                read_message_history=True,
            )

    return overwrites


async def sync_room_permissions(member):
    """Reapply the current expected overwrites to the member's tracked room."""
    channel = get_member_room(member.guild, member.id)
    if channel is None:
        raise LookupError("No personal room was found for this member in this server.")

    await channel.edit(
        overwrites=build_room_overwrites(member.guild, member),
        reason="Syncing personal room permissions for {0}".format(member),
    )
    return channel


async def create_room_for_member(member):
    """Create and store a public text room for the given member."""
    guild_settings = get_guild_settings(member.guild.id)
    room_category_id = guild_settings["room_category_id"]

    if room_category_id is None:
        raise RuntimeError(
            "No room category is configured for this server. "
            "Ask an admin to run `/setup category` or `/setup create-category`."
        )

    category = member.guild.get_channel(room_category_id)
    if not isinstance(category, discord.CategoryChannel):
        raise RuntimeError(
            "The configured room category no longer exists. "
            "Ask an admin to run `/setup category` again."
        )

    channel = await member.guild.create_text_channel(
        name="room-{0}".format(member.display_name).lower().replace(" ", "-")[:90],
        category=category,
        overwrites=build_room_overwrites(member.guild, member),
        reason="Creating personal room for {0}".format(member),
        topic="Personal room owned by {0}".format(member.display_name),
    )

    save_personal_channel_id(member.guild.id, member.id, channel.id)
    await log_event(member.guild, "Room Created", "Created a tracked personal room.", actor=member, target=channel)
    return channel


async def rename_member_room(guild, user_id, new_name, actor=None):
    """Rename the member's room in this guild and return the updated channel."""
    channel = get_member_room(guild, user_id)
    if channel is None:
        raise LookupError("No personal room was found for you in this server.")

    actor_label = actor if actor is not None else "<@{0}>".format(user_id)
    await channel.edit(name=new_name, reason="Personal room renamed by {0}".format(actor_label))
    await log_event(guild, "Room Renamed", "Renamed a tracked personal room.", actor=actor_label, target=channel)
    return channel


async def delete_member_room(guild, user_id):
    """Delete a member's tracked room if it exists, then clear the stored record."""
    channel = get_member_room(guild, user_id)
    if channel is not None:
        await channel.delete(reason="Deleting personal room for user {0}".format(user_id))
        await log_event(guild, "Room Deleted", "Deleted a tracked personal room.", actor="<@{0}>".format(user_id), target=channel)
    clear_personal_channel_id(guild.id, user_id)


async def reset_member_room(member):
    """Delete the tracked room for a member and create a fresh replacement."""
    await delete_member_room(member.guild, member.id)
    return await create_room_for_member(member)


async def claim_member_room(member, channel):
    """Adopt an existing text channel as a member's tracked room and apply room overwrites."""
    await channel.edit(
        overwrites=build_room_overwrites(member.guild, member),
        reason="Claiming channel as personal room for {0}".format(member),
        topic="Personal room owned by {0}".format(member.display_name),
    )
    save_personal_channel_id(member.guild.id, member.id, channel.id)
    await log_event(member.guild, "Room Claimed", "Claimed an existing channel as a tracked room.", actor=member, target=channel)
    return channel


async def archive_member_room(member):
    """Move a tracked room to the archive category and clear the DB record."""
    guild_settings = get_guild_settings(member.guild.id)
    archive_category_id = guild_settings["archive_category_id"]
    channel = get_member_room(member.guild, member.id)

    clear_personal_channel_id(member.guild.id, member.id)

    if channel is None:
        return

    if archive_category_id is None:
        await channel.edit(
            name=("archived-" + channel.name)[:100],
            topic="Archived room for former member {0}".format(member.display_name),
            reason="Archiving room for departed member {0}".format(member),
        )
        await log_event(member.guild, "Room Archived", "Archived a room in place because no archive category is configured.", actor=member, target=channel)
        return

    archive_category = member.guild.get_channel(archive_category_id)
    if isinstance(archive_category, discord.CategoryChannel):
        await channel.edit(
            category=archive_category,
            name=("archived-" + channel.name)[:100],
            topic="Archived room for former member {0}".format(member.display_name),
            reason="Archiving room for departed member {0}".format(member),
        )
        await log_event(member.guild, "Room Archived", "Moved a room into the configured archive category.", actor=member, target=channel)
    else:
        await channel.edit(
            name=("archived-" + channel.name)[:100],
            topic="Archived room for former member {0}".format(member.display_name),
            reason="Archiving room for departed member {0}".format(member),
        )
        await log_event(member.guild, "Room Archived", "Archive category missing, so the room was archived in place.", actor=member, target=channel)


async def lock_member_room(member, locked_by_staff, actor):
    """Lock a member's room so only staff can talk there."""
    set_room_lock_state(member.guild.id, member.id, locked_by_staff=locked_by_staff, actor_id=actor.id)
    channel = await sync_room_permissions(member)
    await log_event(
        member.guild,
        "Room Locked",
        "Locked a tracked room.",
        actor=actor,
        target=channel,
        extra_fields=[("Lock Type", "Staff" if locked_by_staff else "Owner")],
    )
    return channel


async def unlock_member_room(member, by_staff, actor):
    """Unlock a member's room, respecting staff-owned locks."""
    lock_state = get_room_lock_state(member.guild.id, member.id)
    if not lock_state["locked"]:
        raise LookupError("That room is not currently locked.")
    if lock_state["locked_by_staff"] and not by_staff:
        raise PermissionError("This room was locked by staff, so only staff can unlock it.")

    clear_room_lock_state(member.guild.id, member.id)
    channel = await sync_room_permissions(member)
    await log_event(member.guild, "Room Unlocked", "Unlocked a tracked room.", actor=actor, target=channel)
    return channel


def describe_member_room(guild, user_id):
    """Return a small info dict about a tracked personal room."""
    channel_id = get_personal_channel_id(guild.id, user_id)
    channel = guild.get_channel(channel_id) if channel_id else None
    lock_state = get_room_lock_state(guild.id, user_id)
    lock_actor_id = lock_state["lock_actor_id"]
    if lock_state["locked"] and lock_actor_id is None and not lock_state["locked_by_staff"]:
        lock_actor_id = user_id
    return {
        "channel_id": channel_id,
        "exists": isinstance(channel, discord.TextChannel),
        "channel_name": channel.name if isinstance(channel, discord.TextChannel) else None,
        "locked": lock_state["locked"],
        "locked_by_staff": lock_state["locked_by_staff"],
        "lock_actor_id": lock_actor_id,
    }
