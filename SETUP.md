# Ticket Bot — Setup Guide

## Files in this project
```
ticket_bot.py   ← The Discord bot
web.py          ← The control panel website
main.py         ← Starts both together
requirements.txt
Dockerfile
fly.toml
```

---

## Running locally (to test first)

1. Install dependencies:
   ```
   pip install discord.py-self flask
   ```

2. Set your Discord token as an environment variable:
   - Windows PowerShell:
     ```
     $env:DISCORD_TOKEN="your_token_here"
     ```
   - Mac/Linux:
     ```
     export DISCORD_TOKEN="your_token_here"
     ```

3. Run everything:
   ```
   python main.py
   ```

4. Open http://localhost:8080 in your browser to see the control panel.

---

## Deploying to Fly.io

### Step 1 — Install the Fly CLI
Download from: https://fly.io/docs/hands-on/install-flyctl/
Or run in PowerShell:
```
iwr https://fly.io/install.ps1 -useb | iex
```

### Step 2 — Sign up / log in
```
fly auth signup
```
(or `fly auth login` if you already have an account)

### Step 3 — Edit fly.toml
Open fly.toml and change the app name from "ticket-bot" to something unique,
e.g. "tarun-ticket-bot". App names must be globally unique on Fly.

### Step 4 — Create the app
Inside the ticketbot folder, run:
```
fly apps create tarun-ticket-bot
```

### Step 5 — Set your Discord token as a secret
```
fly secrets set DISCORD_TOKEN="your_token_here"
```
This keeps your token safe — it won't be in any files.

### Step 6 — Deploy
```
fly deploy
```
Fly will build the Docker image and launch your app.

### Step 7 — Open your control panel
```
fly open
```
Or visit: https://tarun-ticket-bot.fly.dev

---

## Using the control panel

- **Start / Stop** — turns the bot process on or off
- **Toggle switch** — pauses auto-replies without stopping the bot
- **Greeting message** — change what the bot says (live, no restart needed)
- **Ticket Log** — shows every ticket the bot has greeted

---

## Notes

- The bot watches for new channels created inside category 1396563397503619113
- To change the category, edit `DEFAULT_CONFIG["category_id"]` in ticket_bot.py
- Logs are saved to logs.json (up to 200 entries)
- Config is saved to config.json — changes apply instantly without restarting
