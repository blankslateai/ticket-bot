"""
Discord Ticket Bot — Web Control Panel
Password protected. Run alongside ticket_bot.py.
"""

from flask import Flask, jsonify, request, render_template_string, session, redirect
import json, os, subprocess, sys, threading

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "tbot-s3cr3t-kEy-9z")

CONFIG_FILE = "config.json"
LOG_FILE    = "logs.json"
PASSWORD    = os.environ.get("PANEL_PASSWORD", "201203")

bot_process = None
bot_lock    = threading.Lock()

DEFAULT_CONFIG = {
    "enabled":     True,
    "greeting":    "hi",
    "token":       os.environ.get("DISCORD_TOKEN", ""),
    "category_id": 1396563397503619113,
}

# ── Helpers ────────────────────────────────────────────────────────────────────

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            cfg = json.load(f)
        for k, v in DEFAULT_CONFIG.items():
            cfg.setdefault(k, v)
        return cfg
    return DEFAULT_CONFIG.copy()

def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)

def load_logs():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE) as f:
            return json.load(f)
    return []

def bot_running():
    global bot_process
    return bot_process is not None and bot_process.poll() is None

def require_auth(fn):
    from functools import wraps
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("authed"):
            if request.path.startswith("/api/"):
                return jsonify({"ok": False, "msg": "Unauthorized"}), 401
            return redirect("/login")
        return fn(*args, **kwargs)
    return wrapper

# ── Auth routes ────────────────────────────────────────────────────────────────

LOGIN_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Ticket Bot — Login</title>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Syne:wght@700;800&display=swap" rel="stylesheet">
<style>
  :root {
    --bg:#0d0d0f; --card:#141416; --border:#222226;
    --accent:#5865f2; --text:#e8e8f0; --muted:#5a5a72; --red:#ed4245;
  }
  *{box-sizing:border-box;margin:0;padding:0;}
  body{
    background:var(--bg);color:var(--text);
    font-family:'JetBrains Mono',monospace;
    min-height:100vh;display:grid;place-items:center;
  }
  .card{
    background:var(--card);border:1px solid var(--border);
    border-radius:18px;padding:2.5rem 2rem;width:100%;max-width:360px;
    text-align:center;
  }
  .logo{font-size:2.5rem;margin-bottom:1rem;}
  h1{font-family:'Syne',sans-serif;font-size:1.5rem;margin-bottom:.3rem;}
  .sub{color:var(--muted);font-size:.72rem;margin-bottom:2rem;}
  input{
    width:100%;padding:.7rem 1rem;margin-bottom:.9rem;
    background:var(--bg);border:1px solid var(--border);border-radius:9px;
    color:var(--text);font-family:'JetBrains Mono',monospace;font-size:.9rem;
    outline:none;text-align:center;letter-spacing:.2em;
    transition:border-color .2s;
  }
  input:focus{border-color:var(--accent);}
  button{
    width:100%;padding:.7rem;border:none;border-radius:9px;
    background:var(--accent);color:#fff;
    font-family:'JetBrains Mono',monospace;font-size:.85rem;font-weight:600;
    cursor:pointer;transition:opacity .15s;
  }
  button:hover{opacity:.85;}
  .err{color:var(--red);font-size:.75rem;margin-top:.8rem;}
</style>
</head>
<body>
<div class="card">
  <div class="logo">🎫</div>
  <h1>Ticket Bot</h1>
  <p class="sub">Enter your panel password</p>
  <form method="POST" action="/login">
    <input type="password" name="password" placeholder="••••••" autofocus>
    <button type="submit">Unlock →</button>
  </form>
  {% if error %}<div class="err">❌ Wrong password</div>{% endif %}
</div>
</body>
</html>"""

@app.route("/login", methods=["GET", "POST"])
def login():
    error = False
    if request.method == "POST":
        if request.form.get("password") == PASSWORD:
            session["authed"] = True
            return redirect("/")
        error = True
    return render_template_string(LOGIN_HTML, error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ── API ────────────────────────────────────────────────────────────────────────

@app.route("/api/status")
@require_auth
def status():
    cfg = load_config()
    return jsonify({
        "running":     bot_running(),
        "enabled":     cfg.get("enabled", True),
        "greeting":    cfg.get("greeting", "hi"),
        "category_id": cfg.get("category_id"),
    })

@app.route("/api/start", methods=["POST"])
@require_auth
def start():
    global bot_process
    with bot_lock:
        if bot_running():
            return jsonify({"ok": False, "msg": "Bot is already running"})
        bot_process = subprocess.Popen([sys.executable, "ticket_bot.py"])
        return jsonify({"ok": True, "msg": "Bot started"})

@app.route("/api/stop", methods=["POST"])
@require_auth
def stop():
    global bot_process
    with bot_lock:
        if not bot_running():
            return jsonify({"ok": False, "msg": "Bot is not running"})
        bot_process.terminate()
        bot_process.wait()
        bot_process = None
        return jsonify({"ok": True, "msg": "Bot stopped"})

@app.route("/api/toggle", methods=["POST"])
@require_auth
def toggle():
    cfg = load_config()
    cfg["enabled"] = not cfg.get("enabled", True)
    save_config(cfg)
    state = "enabled" if cfg["enabled"] else "paused"
    return jsonify({"ok": True, "enabled": cfg["enabled"], "msg": f"Bot {state} (no restart needed)"})

@app.route("/api/greeting", methods=["POST"])
@require_auth
def set_greeting():
    data = request.get_json()
    greeting = (data or {}).get("greeting", "").strip()
    if not greeting:
        return jsonify({"ok": False, "msg": "Greeting cannot be empty"})
    cfg = load_config()
    cfg["greeting"] = greeting
    save_config(cfg)
    return jsonify({"ok": True, "msg": f"Greeting saved: {greeting}"})

@app.route("/api/logs")
@require_auth
def logs():
    return jsonify(load_logs())

@app.route("/api/clear_logs", methods=["POST"])
@require_auth
def clear_logs():
    with open(LOG_FILE, "w") as f:
        json.dump([], f)
    return jsonify({"ok": True})

# ── Dashboard ──────────────────────────────────────────────────────────────────

PANEL_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Ticket Bot Panel</title>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Syne:wght@700;800&display=swap" rel="stylesheet">
<style>
  :root {
    --bg:#0d0d0f; --surface:#141416; --border:#222226;
    --accent:#5865f2; --accent2:#57f287; --red:#ed4245; --yellow:#faa61a;
    --text:#e8e8f0; --muted:#5a5a72; --card:#18181c;
  }
  *{box-sizing:border-box;margin:0;padding:0;}
  body{
    background:var(--bg);color:var(--text);
    font-family:'JetBrains Mono',monospace;
    min-height:100vh;padding:2rem;
  }
  header{display:flex;align-items:center;justify-content:space-between;margin-bottom:2.5rem;}
  .header-left{display:flex;align-items:center;gap:1rem;}
  .logo{width:42px;height:42px;background:var(--accent);border-radius:12px;display:grid;place-items:center;font-size:1.3rem;}
  h1{font-family:'Syne',sans-serif;font-size:1.6rem;font-weight:800;}
  .subtitle{color:var(--muted);font-size:.75rem;margin-top:2px;}
  .logout-btn{
    font-family:'JetBrains Mono',monospace;font-size:.72rem;
    color:var(--muted);background:none;border:1px solid var(--border);
    border-radius:7px;padding:.35rem .75rem;cursor:pointer;
    text-decoration:none;transition:color .15s,border-color .15s;
  }
  .logout-btn:hover{color:var(--red);border-color:var(--red);}

  .grid{display:grid;grid-template-columns:1fr 1fr;gap:1.5rem;max-width:900px;}
  @media(max-width:640px){.grid{grid-template-columns:1fr;}}

  .card{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:1.4rem;}
  .card-title{
    font-size:.7rem;font-weight:600;letter-spacing:.12em;
    text-transform:uppercase;color:var(--muted);margin-bottom:1rem;
  }

  .pill{display:inline-flex;align-items:center;gap:.4rem;padding:.3rem .8rem;border-radius:999px;font-size:.75rem;font-weight:600;}
  .pill.online {background:#57f28720;color:var(--accent2);border:1px solid #57f28740;}
  .pill.offline{background:#ed424520;color:var(--red);    border:1px solid #ed424540;}
  .pill.paused {background:#faa61a20;color:var(--yellow); border:1px solid #faa61a40;}
  .dot{width:7px;height:7px;border-radius:50%;background:currentColor;}

  .btn{
    display:inline-flex;align-items:center;gap:.4rem;
    padding:.5rem 1.1rem;border-radius:8px;border:none;
    font-family:'JetBrains Mono',monospace;font-size:.8rem;font-weight:600;
    cursor:pointer;transition:opacity .15s,transform .1s;
  }
  .btn:hover{opacity:.85;} .btn:active{transform:scale(.97);}
  .btn-primary{background:var(--accent);color:#fff;}
  .btn-danger {background:var(--red);   color:#fff;}
  .btn-ghost  {background:var(--border);color:var(--text);}
  .btn-sm{padding:.35rem .8rem;font-size:.72rem;}
  .btn-row{display:flex;gap:.6rem;flex-wrap:wrap;}

  input[type=text]{
    width:100%;padding:.6rem .9rem;
    background:var(--surface);border:1px solid var(--border);
    border-radius:8px;color:var(--text);
    font-family:'JetBrains Mono',monospace;font-size:.85rem;
    outline:none;transition:border-color .2s;margin-bottom:.7rem;
  }
  input[type=text]:focus{border-color:var(--accent);}

  .switch{position:relative;width:44px;height:24px;cursor:pointer;}
  .switch input{opacity:0;width:0;height:0;}
  .slider{position:absolute;inset:0;background:var(--border);border-radius:24px;transition:background .2s;}
  .slider::before{
    content:'';position:absolute;width:18px;height:18px;border-radius:50%;
    background:#fff;left:3px;top:3px;transition:transform .2s;
  }
  input:checked+.slider{background:var(--accent2);}
  input:checked+.slider::before{transform:translateX(20px);}
  .toggle-row{display:flex;align-items:center;justify-content:space-between;}

  .log-list{max-height:260px;overflow-y:auto;display:flex;flex-direction:column;gap:.5rem;}
  .log-item{background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:.6rem .9rem;font-size:.72rem;}
  .log-time{color:var(--muted);margin-bottom:.15rem;}
  .log-channel{color:var(--accent);font-weight:600;}
  .log-msg{color:var(--accent2);}
  .empty{color:var(--muted);font-size:.78rem;text-align:center;padding:1.5rem 0;}

  #toast{
    position:fixed;bottom:1.5rem;right:1.5rem;
    background:var(--card);border:1px solid var(--border);
    border-radius:10px;padding:.7rem 1.2rem;font-size:.8rem;
    transform:translateY(100px);opacity:0;transition:all .3s;
    max-width:280px;z-index:999;
  }
  #toast.show{transform:translateY(0);opacity:1;}

  .full-width{grid-column:1/-1;}
  .info-row{font-size:.72rem;color:var(--muted);margin-top:.5rem;}
  .info-row span{color:var(--text);}
  .status-row{display:flex;align-items:center;gap:.8rem;margin-bottom:1.2rem;}
</style>
</head>
<body>

<header>
  <div class="header-left">
    <div class="logo">🎫</div>
    <div>
      <h1>Ticket Bot</h1>
      <div class="subtitle">Control Panel</div>
    </div>
  </div>
  <a href="/logout" class="logout-btn">🔒 Logout</a>
</header>

<div class="grid">

  <!-- Status & Control -->
  <div class="card">
    <div class="card-title">Bot Status</div>
    <div class="status-row">
      <span class="pill offline" id="status-pill"><span class="dot"></span><span id="status-text">Loading…</span></span>
    </div>
    <div class="btn-row">
      <button class="btn btn-primary" onclick="startBot()">▶ Start</button>
      <button class="btn btn-danger"  onclick="stopBot()">■ Stop</button>
    </div>
    <div class="info-row" style="margin-top:.9rem">Category: <span id="cat-id">—</span></div>
  </div>

  <!-- Toggle -->
  <div class="card">
    <div class="card-title">Auto-Reply Toggle</div>
    <div class="toggle-row">
      <div>
        <div style="font-size:.85rem;font-weight:600;margin-bottom:.3rem">Auto-greet tickets</div>
        <div style="font-size:.72rem;color:var(--muted)">Pause without stopping the bot</div>
      </div>
      <label class="switch">
        <input type="checkbox" id="enabled-toggle" onchange="toggleEnabled()">
        <span class="slider"></span>
      </label>
    </div>
  </div>

  <!-- Greeting -->
  <div class="card">
    <div class="card-title">Greeting Message</div>
    <input type="text" id="greeting-input" placeholder="hi" />
    <button class="btn btn-primary btn-sm" onclick="saveGreeting()">💾 Save</button>
  </div>

  <!-- Logs -->
  <div class="card full-width">
    <div class="card-title" style="display:flex;justify-content:space-between;align-items:center">
      <span>Ticket Log</span>
      <button class="btn btn-ghost btn-sm" onclick="clearLogs()">🗑 Clear</button>
    </div>
    <div class="log-list" id="log-list">
      <div class="empty">No tickets greeted yet.</div>
    </div>
  </div>

</div>
<div id="toast"></div>

<script>
  function toast(msg) {
    const t = document.getElementById('toast');
    t.textContent = msg;
    t.classList.add('show');
    setTimeout(() => t.classList.remove('show'), 2800);
  }

  async function fetchStatus() {
    const r = await fetch('/api/status');
    if (r.status === 401) { location.href = '/login'; return; }
    const d = await r.json();
    document.getElementById('cat-id').textContent = d.category_id;
    document.getElementById('greeting-input').value = d.greeting;
    document.getElementById('enabled-toggle').checked = d.enabled;
    const pill = document.getElementById('status-pill');
    const txt  = document.getElementById('status-text');
    if (d.running && d.enabled)       { pill.className='pill online';  txt.textContent='Online'; }
    else if (d.running && !d.enabled) { pill.className='pill paused';  txt.textContent='Paused'; }
    else                              { pill.className='pill offline'; txt.textContent='Offline'; }
  }

  async function fetchLogs() {
    const r = await fetch('/api/logs');
    if (r.status === 401) return;
    const logs = await r.json();
    const el = document.getElementById('log-list');
    if (!logs.length) { el.innerHTML='<div class="empty">No tickets greeted yet.</div>'; return; }
    el.innerHTML = logs.map(l => `
      <div class="log-item">
        <div class="log-time">${l.time} · ${l.guild}</div>
        <div><span class="log-channel">#${l.channel}</span> &rarr; <span class="log-msg">"${l.message}"</span></div>
      </div>`).join('');
  }

  async function startBot() {
    const d = await (await fetch('/api/start',{method:'POST'})).json();
    toast(d.msg); fetchStatus();
  }
  async function stopBot() {
    const d = await (await fetch('/api/stop',{method:'POST'})).json();
    toast(d.msg); fetchStatus();
  }
  async function toggleEnabled() {
    const d = await (await fetch('/api/toggle',{method:'POST'})).json();
    toast(d.msg); fetchStatus();
  }
  async function saveGreeting() {
    const greeting = document.getElementById('greeting-input').value.trim();
    if (!greeting) { toast('Greeting cannot be empty'); return; }
    const d = await (await fetch('/api/greeting',{
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({greeting})
    })).json();
    toast(d.msg);
  }
  async function clearLogs() {
    await fetch('/api/clear_logs',{method:'POST'});
    toast('Logs cleared'); fetchLogs();
  }

  fetchStatus(); fetchLogs();
  setInterval(fetchStatus, 4000);
  setInterval(fetchLogs,   4000);
</script>
</body>
</html>"""

@app.route("/")
@require_auth
def index():
    return render_template_string(PANEL_HTML)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
