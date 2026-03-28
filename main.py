"""
Entrypoint: starts both the web panel and the Discord bot together.
Used by Fly.io (and locally).
"""
import subprocess
import sys
import os
import threading

def run_bot():
    subprocess.run([sys.executable, "ticket_bot.py"])

def run_web():
    subprocess.run([sys.executable, "web.py"])

if __name__ == "__main__":
    t = threading.Thread(target=run_bot, daemon=True)
    t.start()
    run_web()
