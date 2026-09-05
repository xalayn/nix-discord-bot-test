# Zoho Mail Discord bot

This bot watches a Zoho Mail inbox and creates a Discord discussion thread for
each email conversation. Later incoming messages with the same Zoho `threadId`
are posted to the existing Discord thread.

The target may be a regular server text channel or a forum channel. In a text
channel, the bot posts an email summary and starts a public thread from it. In a
forum channel, the summary becomes the forum post's first message.

## Zoho setup

1. Create a **Self Client** in the [Zoho API Console](https://api-console.zoho.com/).
2. Generate a grant with these read-only scopes:

   ```text
   ZohoMail.accounts.READ,ZohoMail.folders.READ,ZohoMail.messages.READ
   ```

3. Exchange the grant for an offline access token and retain the returned
   refresh token. Zoho only returns the refresh token during the initial grant.

The account and Inbox folder are discovered automatically when the OAuth grant
has access to exactly one mail account. Set `ZOHO_ACCOUNT_ID` and/or
`ZOHO_FOLDER_ID` explicitly if discovery is ambiguous.

Zoho accounts in another data center must use the matching hosts. For example,
an EU account uses `https://accounts.zoho.eu` and
`https://mail.zoho.eu/api`.

## Discord setup

Set `DISCORD_CHANNEL_ID` to the numeric ID of the destination text or forum
channel. The bot needs permission to view the channel, send messages, create
public threads, and send messages in threads. Keep the channel private if email
content is confidential.

## Configuration

The following environment variables are required:

| Variable | Purpose |
| --- | --- |
| `DISCORD_TOKEN` | Discord bot token |
| `DISCORD_CHANNEL_ID` | Destination text or forum channel ID |
| `ZOHO_CLIENT_ID` | Zoho OAuth client ID |
| `ZOHO_CLIENT_SECRET` | Zoho OAuth client secret |
| `ZOHO_REFRESH_TOKEN` | Long-lived Zoho OAuth refresh token |

Optional configuration:

| Variable | Default | Purpose |
| --- | --- | --- |
| `ZOHO_ACCOUNT_ID` | auto-detected | Mail account to watch |
| `ZOHO_FOLDER_ID` | auto-detected | Inbox folder to watch |
| `ZOHO_API_BASE_URL` | `https://mail.zoho.com/api` | Zoho Mail data-center API URL |
| `ZOHO_ACCOUNTS_BASE_URL` | `https://accounts.zoho.com` | Zoho OAuth data-center URL |
| `STATE_DB_PATH` | `./zoho-discord-bot.sqlite3` | Persistent SQLite state file |
| `POLL_INTERVAL_SECONDS` | `30` | Inbox poll interval (minimum 10) |

`STATE_DB_PATH` must point to persistent writable storage. It holds message IDs
and the Zoho-to-Discord thread mapping; losing it can cause conversations to be
re-created.

## Run

```sh
DISCORD_TOKEN=... \
DISCORD_CHANNEL_ID=... \
ZOHO_CLIENT_ID=... \
ZOHO_CLIENT_SECRET=... \
ZOHO_REFRESH_TOKEN=... \
STATE_DB_PATH=/var/lib/zoho-discord-bot/state.sqlite3 \
nix run
```

On its first successful poll, the bot records the current inbox as a baseline
without posting it to Discord. Only mail received after that point is sent. It
does not mark messages read or otherwise modify the Zoho mailbox.

Email HTML is converted to plain text and clipped to Discord's embed limits.
Discord mentions are disabled for all email-derived messages. Attachments are
reported but are not copied into Discord.

## Code layout

The five-line `bot.py` is only a compatibility launcher. The implementation is
split by responsibility under `zoho_discord_bot/`: configuration, Zoho API
access, persistent state, email presentation, and Discord orchestration.
