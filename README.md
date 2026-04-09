# Discord Personal Rooms Bot

Multi-server Discord bot for public personal rooms and personal colour roles.

## Features
- per-server setup for room category, archive category, staff role, and log channel
- personal public room creation, rename, info, lock, and unlock
- personal colour role creation, colour set/reset, rename, and info
- staff tools to repair, claim, reset, rename, delete, lock, unlock, block, and inspect user assets
- audit logging to a configured server channel
- SQLite persistence for tracked rooms, roles, lock state, and blocked users

## New moderation additions
- `/staff block-user <member>` blocks a member from:
  - `/room create`
  - `/room rename`
  - `/color set`
  - `/color rename`
- `/staff unblock-user <member>` removes that restriction
- staff and admins cannot be blocked
- `/staff color-set <member> <hex_code>` sets another member's tracked colour role directly
- `/staff user-info <member>` shows a combined view of tracked room state, tracked role state, lock state, who locked the room, blocked state, and who blocked the user

## Setup
1. Create a `.env` file with:
   - `DISCORD_BOT_TOKEN=your_token_here`
2. Install dependencies:
   - `pip install -r requirements.txt`
3. Start the bot:
   - `python bot.py`

## Notes
- Logs are sent only if a log channel is configured.
- Blocking is stored per server and persists across restarts.
- Existing databases are migrated automatically when the bot starts.
