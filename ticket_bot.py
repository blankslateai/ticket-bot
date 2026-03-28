"""
Discord Ticket Auto-Greeter — Bot Process
Reads config from config.json, logs activity to logs.json
Controlled by the web panel (web.py)
"""

import discord
import asyncio
import json
import os
from datetime import datetime, timezone

CONFIG_FILE = "config.json"
LOG_FILE = "logs.json"
MAX_LOGS = 200

# ── Defaults (overridden by config.json) ──────────────────────────────────────
DEFAULT_CONFIG = {
    "enabled": True,
    "greeting": "hi",
    "token": os.environ.get("DISCORD_TOKEN", ""),
    "category_id": 1396563397503619113,
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            cfg = json.load(f)
        for k, v in DEFAULT_CONFIG.items():
            cfg.setdefault(k, v)
        return cfg
    return DEFAULT_CONFIG.copy()

def append_log(channel_name, guild_name, message):
    logs = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE) as f:
            logs = json.load(f)
    logs.insert(0, {
        "time": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "channel": channel_name,
        "guild": guild_name,
        "message": message,
    })
    logs = logs[:MAX_LOGS]
    with open(LOG_FILE, "w") as f:
        json.dump(logs, f)

# ── Bot ───────────────────────────────────────────────────────────────────────
client = discord.Client()
greeted_channels = set()  # Deduplicate — prevent sending hi multiple times per channel

@client.event
async def on_ready():
    cfg = load_config()
    print(f"[BOT] Logged in as {client.user} | Category: {cfg['category_id']}")

@client.event
async def on_guild_channel_create(channel):
    cfg = load_config()

    if not cfg.get("enabled", True):
        return
    if not isinstance(channel, discord.TextChannel):
        return
    if channel.category_id != cfg["category_id"]:
        return
    if channel.id in greeted_channels:
        return  # Already greeted, skip duplicate event

    greeted_channels.add(channel.id)

    await asyncio.sleep(1.5)
    greeting = cfg.get("greeting", "hi")
    await channel.send(greeting)

    guild_name = channel.guild.name if channel.guild else "Unknown"
    append_log(channel.name, guild_name, greeting)
    print(f"[BOT] Greeted #{channel.name} in {guild_name}")

def main():
    cfg = load_config()
    token = cfg.get("token") or os.environ.get("DISCORD_TOKEN", "")
    if not token:
        print("[BOT] ERROR: No Discord token found. Set DISCORD_TOKEN env var or add to config.json")
        return
    client.run(token)

if __name__ == "__main__":
    main()
