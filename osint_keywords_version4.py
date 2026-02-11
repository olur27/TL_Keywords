from telethon import TelegramClient, events
from telethon.errors import FloodWaitError
import re
import json
import asyncio
import sys
import logging
from logging.handlers import RotatingFileHandler
import argparse
import time
import aiohttp

# ==========================================================
# ARGUMENT PARSING
# ==========================================================

parser = argparse.ArgumentParser(
    description="OSINT Telegram Keyword Listener",
    formatter_class=argparse.ArgumentDefaultsHelpFormatter
)

parser.add_argument("--api-id", type=int, help="Telegram API ID")
parser.add_argument("--api-hash", type=str, help="Telegram API Hash")
parser.add_argument("--keywords-file", type=str, default="keywords.txt",
                    help="Path to the keywords file")
parser.add_argument("--bot-chat-id", type=int, help="Bot chat ID (legacy, numeric, optional)")
parser.add_argument("--bot-username", type=str, help="Bot username (recommended)")
parser.add_argument("--webhook", type=str, help="Webhook URL (if sending to webhook)")

args = parser.parse_args()

# ==========================================================
# ASCII BANNER
# ==========================================================

def ninja_banner():
    print(r"""
⠀⠀⠀⠀⠀⣀⠠⠄⠒⠒⠒⠠⠤⢀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⡠⠊⠀⠀⠀⠀⠀⠀⠀⠀⠀⠉⢆⠀⠀⠀⠀⠀⠀
⠀⠀⢠⠁⠀⠀⠀OLur27⠀⠀⠈⡆⠀⠀⠀⠀⠀
⠀⠀⢸⠀⢀⢴⡂⠉⠁⠀⠈⠉⠐⠢⡀⠀⡇⠀⠀⠀⠀⠀
⠀⠀⢸⠀⡇⠀⢻⣿⠂⠀⠐⣿⣿⠁⠈⠄⡇⠀⠀⠀⠀⠀
⠀⠀⠀⠣⡱⣀⠈⠉⠀⠀⠀⠈⠁⣀⠜⡘⠀⠀⡠⡞⣍⡂
⠀⠀⠀⠀⠀⢢⡥⠐⣒⣒⣒⡒⢬⡔⠊⢰⣶⡮⡱⡬⠚⠁
⠀⠀⠀⢀⠔⠉⠀⠀⠀⠀⠀⠀⠀⠈⠲⡊⣑⢵⠏⠀⠀⠀
⠀⠀⡠⠃⠀⢠⠀⠀⠀⠀⠀⠀⠀⣄⠀⠈⢇⠀⠀⠀⠀⠀
⠀⡰⠁⠀⡰⡇⠀⠀⠀⠀⠀⠀⠀⢸⢢⠀⠀⢃⠀⠀⠀⠀
⢰⠥⣀⡐⢠⠭⠍⢉⣉⣉⣉⡉⠉⠭⡆⢣⣀⠠⡆⠀⠀⠀
⠘⢄⡠⠏⡝⠀⠀⠀⠀⠀⠀⠀⠀⠀⢱⠘⢄⡠⠆⠀⠀⠀
⠈⠑⠒⢨⠃⠀⠀⠀⡔⠉⢢⠀⠀⠀⠀⡄⠀⠀⠀⠀⠀⠀
⠀⠀⠀⡘⠀⠀⠀⡸⠀⠀⠀⢃⠀⠀⠀⢡⠀⠀⠀⠀⠀⠀
⠀⠀⡠⠧⠤⠄⢀⠃⠀⠀⠀⠘⡄⠀⠤⠼⢄⠀⠀⠀⠀⠀
⠀⠘⠥⠤⠤⠤⠜⠀⠀⠀⠀⠀⠣⠤⠤⠤⠤⠇⠀⠀⠀⠀
""")

ninja_banner()

# ==========================================================
# PROMPT MANDATORY INPUTS
# ==========================================================

# API credentials
if not args.api_id:
    args.api_id = int(input("Enter Telegram API ID: ").strip())

if not args.api_hash:
    args.api_hash = input("Enter Telegram API Hash: ").strip()

# OUTPUT DESTINATION PROMPT
while True:
    print("\nSelect output destination(s) (file output always enabled):")
    print("1 - Telegram Bot")
    print("2 - Webhook URL")
    print("3 - Both Bot and Webhook")
    choice = input("Enter choice (1/2/3): ").strip()
    if choice not in {"1", "2", "3"}:
        print("Invalid choice. Try again.")
        continue

    if choice in {"1", "3"}:
        if not args.bot_username:
            args.bot_username = input("Enter BOT_USERNAME: ").strip()

    if choice in {"2", "3"}:
        if not args.webhook:
            args.webhook = input("Enter Webhook URL: ").strip()

    break

send_to_bot = choice in {"1", "3"}
send_to_webhook = choice in {"2", "3"}

# ==========================================================
# LOGGING
# ==========================================================

LOG_FILE = "osint_listener.log"

logging.basicConfig(level=logging.INFO, handlers=[])

file_handler = RotatingFileHandler(
    LOG_FILE,
    maxBytes=10 * 1024 * 1024,
    backupCount=5,
    encoding="utf-8"
)
file_formatter = logging.Formatter(
    fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ"
)
file_handler.setFormatter(file_formatter)

console_handler = logging.StreamHandler(sys.stdout)
console_formatter = logging.Formatter(fmt="[%(levelname)s] %(message)s")
console_handler.setFormatter(console_formatter)

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

logging.getLogger("telethon").setLevel(logging.ERROR)
logger = logging.getLogger("osint-listener")

# ==========================================================
# KEYWORDS
# ==========================================================

def load_keywords(file_path):
    keywords = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    keywords.append(re.compile(line, re.IGNORECASE))
    except Exception as e:
        logger.error(f"Error loading keywords file: {e}")
        sys.exit(1)
    return keywords

KEYWORDS = load_keywords(args.keywords_file)

# ==========================================================
# OUTPUT FILE
# ==========================================================

OUTPUT_FILE = "osint_hits.json"

def save_hit(record):
    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

# ==========================================================
# TELEGRAM CLIENT
# ==========================================================

client = TelegramClient(
    "osint_session",
    args.api_id,
    args.api_hash,
    connection_retries=5,
    sequential_updates=True
)

# ==========================================================
# SANITIZER
# ==========================================================

def sanitize(obj):
    if isinstance(obj, bytes):
        return obj.hex()
    if isinstance(obj, dict):
        return {k: sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize(i) for i in obj]
    try:
        json.dumps(obj)
        return obj
    except Exception:
        return str(obj)

# ==========================================================
# BOT FORWARDING
# ==========================================================

async def forward_to_bot(hit):
    if not send_to_bot:
        return
    bot_text = (
        f"🚨 Keyword Hit Detected!\n"
        f"Keyword: {hit['keyword']}\n"
        f"Chat: {hit['chat_name']} (ID: {hit['chat_id']})\n"
        f"Sender: {hit['sender_display_name']} (@{hit['sender_username']})\n"
        f"Time: {hit['datetime_utc']}\n"
        f"Message ID: {hit['message_id']}\n\n"
        f"Message:\n{hit['message_text']}"
    )
    try:
        if hit["has_media"] and hit["media_saved_path"]:
            await client.send_file(args.bot_username, hit["media_saved_path"], caption=bot_text)
        else:
            await client.send_message(args.bot_username, bot_text)
    except FloodWaitError as e:
        logger.warning(f"Flood wait while sending to bot: sleeping {e.seconds}s")
        await asyncio.sleep(e.seconds)
    except Exception:
        logger.exception("Failed to forward hit to bot")

# ==========================================================
# WEBHOOK FORWARDING
# ==========================================================

async def forward_to_webhook(hit):
    if not send_to_webhook:
        return
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(args.webhook, json=hit, timeout=10) as resp:
                if resp.status != 200:
                    logger.warning(f"Webhook returned status {resp.status}")
    except Exception as e:
        logger.warning(f"Webhook send failed: {e}")

# ==========================================================
# MESSAGE HANDLER
# ==========================================================

@client.on(events.NewMessage())
async def handler(event):
    try:
        msg = event.message
        if not msg:
            return
        text = msg.message or ""
        chat = await event.get_chat()
        sender = await event.get_sender()

        for pattern in KEYWORDS:
            if not pattern.search(text):
                continue

            media_info = None
            media_path = None
            if msg.media:
                try:
                    media_info = sanitize(msg.media.to_dict())
                    media_path = await event.download_media()
                except Exception as e:
                    media_info = {"error": str(e)}

            hit = {
                "datetime_utc": msg.date.replace(tzinfo=None).isoformat(),
                "chat_id": event.chat_id,
                "chat_name": getattr(chat, "title", None) or getattr(chat, "username", None) or "Unknown",
                "message_id": msg.id,
                "keyword": pattern.pattern,
                "message_text": text,
                "sender_id": getattr(sender, "id", None),
                "sender_first_name": getattr(sender, "first_name", None),
                "sender_last_name": getattr(sender, "last_name", None),
                "sender_username": getattr(sender, "username", None),
                "sender_display_name": (
                    f"{getattr(sender, 'first_name', '') or ''} "
                    f"{getattr(sender, 'last_name', '') or ''}"
                ).strip(),
                "has_media": bool(msg.media),
                "media_info": media_info,
                "media_saved_path": media_path,
            }

            logger.info(
                "KEYWORD HIT | Keyword: %s | Chat: %s | Sender: %s\nMessage: %s",
                hit["keyword"], hit["chat_name"], hit["sender_display_name"], hit["message_text"]
            )

            save_hit(hit)
            await forward_to_bot(hit)
            await forward_to_webhook(hit)

            break

    except FloodWaitError as e:
        logger.warning(f"Flood wait in handler: sleeping {e.seconds}s")
        await asyncio.sleep(e.seconds)
    except Exception:
        logger.exception("Unhandled exception in message handler")

# ==========================================================
# CONNECTION
# ==========================================================

async def ensure_connection():
    logger.info("Connecting to Telegram...")
    await client.connect()
    if not await client.is_user_authorized():
        logger.error("Session not authorized. Run login first.")
        sys.exit(1)
    logger.info("Connected. Listening for messages...")

# ==========================================================
# MAIN LOOP
# ==========================================================

async def main():
    await ensure_connection()

while True:
    try:
        client.start()
        client.loop.run_until_complete(main())
        client.run_until_disconnected()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        break
    except Exception as e:
        logger.error(f"Unhandled error: {e}, restarting in 10 seconds")
        time.sleep(10)
        try:
            client.disconnect()
        except:
            pass