from __future__ import annotations

"""Helpers for syncing existing members and repairing tracked assets."""

from services.channels import (
    clear_personal_channel_id,
    create_room_for_member,
    iter_personal_channel_rows,
)
from services.roles import ensure_personal_role, iter_personal_role_rows


async def sync_existing_members(guild):
    """Create missing personal roles for current guild members."""
    created = 0
    skipped = 0

    for member in guild.members:
        if member.bot:
            skipped += 1
            continue

        existing_role_ids = set(role.id for role in member.roles)
        role = await ensure_personal_role(member)
        if role.id in existing_role_ids:
            skipped += 1
        else:
            created += 1

    return created, skipped


async def repair_guild_assets(guild, dry_run=False):
    """Repair stored roles and rooms for one guild, optionally as a preview only."""
    roles_recreated = 0
    rooms_recreated = 0
    room_records_cleared = 0

    for user_id, role_id in iter_personal_role_rows(guild.id):
        member = guild.get_member(user_id)
        if member is None or member.bot:
            continue

        role = guild.get_role(role_id)
        if role is None:
            roles_recreated += 1
            if not dry_run:
                await ensure_personal_role(member)

    for user_id, channel_id in iter_personal_channel_rows(guild.id):
        member = guild.get_member(user_id)
        if member is None or member.bot:
            continue

        channel = guild.get_channel(channel_id)
        if channel is None:
            try:
                if dry_run:
                    rooms_recreated += 1
                else:
                    await create_room_for_member(member)
                    rooms_recreated += 1
            except RuntimeError:
                room_records_cleared += 1
                if not dry_run:
                    clear_personal_channel_id(guild.id, user_id)

    return {
        "roles_recreated": roles_recreated,
        "rooms_recreated": rooms_recreated,
        "room_records_cleared": room_records_cleared,
        "dry_run": dry_run,
    }
