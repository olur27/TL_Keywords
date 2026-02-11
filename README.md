# OSINT Telegram Keyword Listener

A Python script that monitors Telegram channels you are subscribed to for specified keywords, logs hits locally, and forwards them to either a Telegram bot or a webhook, or both. It will also save the output to a file on your file system.  

---

## Features

- Monitors messages in channels for **custom keywords**.
- Saves hits in a local JSON file (`osint_hits.json` by default).
- Forwards hits to:
  - A **Telegram bot**.
  - A **webhook URL**.
- Supports media attachments (images, videos) for bot forwarding.
- Customizable via command-line arguments. Add --help to see options. By default keywords.txt will be the file to monitor, but you can modify it with arguments (--help)
- Logging with rotating log files for long-running monitoring.

---

## Requirements

- Python 3.10+
- Telethon
- aiohttp

You can install requirements using:

```bash
pip install -r requirements.txt

## Usage

Run the script using Python:

python osint_keywords_v4.py [OPTIONS]


If arguments are missing, the script will prompt for mandatory values.

Arguments
Argument	Type	Description
--api-id	int	Telegram API ID (mandatory)
--api-hash	str	Telegram API Hash (mandatory)
--keywords-file	str	Path to keywords file (default: keywords.txt)
--destination	str	Output destination: bot or webhook (mandatory)
--bot-chat-id	int	Chat ID of your Telegram bot (required if destination=bot)
--bot-username	str	Full bot username including @ (required if destination=bot)
--webhook	str	Webhook URL to send hits via HTTP POST (required if destination=webhook)

## Important: For bot forwarding, always use the full username including @, e.g., @MyBotName. Just using MyBotName will not work. Ensure you have sent at least one message to your bot in order to recognize the USERNAME. 

## Keywords File

One keyword per line.

Lines starting with # are ignored (comments).

Supports regex patterns for advanced matching.

# Example keywords
bmalware
hack
vulnerability

## Logging

Logs are saved in osint_listener.log.

Rotating logs: 10MB per file, up to 5 backups.

Console output shows hits and info messages.

## Notes

Webhooks currently receive text and metadata only. Media attachments are only forwarded to the Telegram bot.

Use a Telegram session; first run may require logging in via the API ID and Hash. It may ask your Telegram password if any.
