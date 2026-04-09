# Discord Personal Rooms Bot (Multi-Server, Python 3.9, v10)

This version adds a built-in audit log that is well suited to moderation and server maintenance.

## Log system
Use:
- `/setup log-channel <channel>`

Once configured, the bot sends embedded audit entries to that channel for key actions such as:
- room creation
- room rename
- room deletion
- room archive
- room lock and unlock
- role creation
- role rename
- role deletion
- claim actions

The bot still logs to the console as well.

## Why this logging style
This version uses a per-server log channel with embeds instead of plain text spam or a database-only log because it is the most practical fit for your bot:
- moderators can read it directly in Discord
- it is structured and readable
- no extra query UI is needed
- it is useful immediately during normal server use

## New admin command
- `/setup log-channel <channel>`

## Notes
- Logs are only sent if a log channel is configured for that server.
- The log is per-server, not global.
- Existing commands and behaviour remain the same.
