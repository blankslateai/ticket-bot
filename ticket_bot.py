"""
Discord Ticket Auto-Greeter — Bot Process
Fetches live config from the web panel (web.py) instead of reading a file.
"""

import discord
import asyncio
import os
import requests
from datetime import datetime, timezone

# The web panel runs on the same machine, so we talk to it locally
PANEL_URL = os.environ.get("PANEL_URL", "http://localhost:8080")
# Use first 8 chars of the Discord token as a simple internal auth token
TOKEN = os.environ.get("DISCORD_TOKEN", "")
INTERNAL_TOKEN = TOKEN[:8] if TOKEN else ""

def get_config():
    """Fetch live config from the web panel."""
    try:
        r = requests.get(f"{PANEL_URL}/internal/config", params={"token": INTERNAL_TOKEN}, timeout=3)
        return r.json()
    except Exception as e:
        print(f"[BOT] Could not fetch config: {e}")
        return {"enabled": True, "greeting": "hi", "category_id": 1396563397503619113}

def post_log(channel_name, guild_name, message):
    """Send a log entry to the web panel."""
    try:
        requests.post(
            f"{PANEL_URL}/internal/log",
            params={"token": INTERNAL_TOKEN},
            json={
                "time": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                "channel": channel_name,
                "guild": guild_name,
                "message": message,
            },
            timeout=3,
        )
    except Exception as e:
        print(f"[BOT] Could not post log: {e}")

client = discord.Client()
greeted_channels = set()

@client.event
async def on_ready():
    print(f"[BOT] Logged in as {client.user}")

@client.event
async def on_guild_channel_create(channel):
    cfg = get_config()

    if not cfg.get("enabled", True):
        return
    if not isinstance(channel, discord.TextChannel):
        return
    if channel.category_id != cfg.get("category_id"):
        return
    if channel.id in greeted_channels:
        return

    greeted_channels.add(channel.id)
    await asyncio.sleep(1.5)

    greeting = cfg.get("greeting", "hi")
    await channel.send(greeting)

    guild_name = channel.guild.name if channel.guild else "Unknown"
    post_log(channel.name, guild_name, greeting)
    print(f"[BOT] Greeted #{channel.name} in {guild_name}")

def main():
    if not TOKEN:
        print("[BOT] ERROR: No DISCORD_TOKEN set")
        return
    client.run(TOKEN)

if __name__ == "__main__":
    main()
