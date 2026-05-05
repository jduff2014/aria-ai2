"""
aria_server.py - Fixed for Railway deployment
"""

from flask import Flask, request, jsonify, send_from_directory
import json
import os
import datetime
from pathlib import Path

try:
    import anthropic
except ImportError:
    print("[!] Run: pip install flask anthropic")
    exit()

app = Flask(__name__, static_folder="aria_web")

# ── CONFIG ────────────────────────────────────────────────────────────────────
MEMORY_FILE  = "/tmp/ai_memory.json"    # Railway uses /tmp for writable storage
PROFILE_FILE = "/tmp/ai_profile.json"
AI_NAME      = "ARIA"
MODEL        = "claude-sonnet-4-20250514"

# ── MEMORY ────────────────────────────────────────────────────────────────────
def load_memory():
    if Path(MEMORY_FILE).exists():
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    return []

def save_memory(memory):
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=2)

def load_profile():
    if Path(PROFILE_FILE).exists():
        with open(PROFILE_FILE, "r") as f:
            return json.load(f)
    return {
        "name": None,
        "interests": [],
        "facts": [],
        "games_played": ["snake", "flappy bird", "pacman"],
        "printer": "Ender 3 S1 Pro",
        "conversations": 0,
        "first_met": str(datetime.date.today())
    }

def save_profile(profile):
    with open(PROFILE_FILE, "w") as f:
        json.dump(profile, f, indent=2)

def format_memory(memory, profile):
    lines = []
    if profile["name"]:
        lines.append(f"User's name: {profile['name']}")
    if profile["interests"]:
        lines.append(f"Interests: {', '.join(profile['interests'])}")
    if profile["facts"]:
        lines.append(f"Known facts: {'; '.join(profile['facts'][-10:])}")
    lines.append(f"3D Printer: {profile.get('printer', 'Ender 3 S1 Pro')}")
    lines.append(f"Games worked on: {', '.join(profile.get('games_played', []))}")
    lines.append(f"Conversations: {profile['conversations']}")
    lines.append(f"First met: {profile['first_met']}")
    lines.append("Also knows: User is building self-learning game AIs using DQN reinforcement learning on a PC with RTX 2060 GPU and 36GB RAM.")
    if memory:
        lines.append("\nRecent exchanges:")
        for m in memory[-8:]:
            lines.append(f"[{m['date']}] User: {m['user']}")
            lines.append(f"[{m['date']}] ARIA: {m['assistant'][:150]}...")
    return "\n".join(lines)

def extract_facts(user_msg, profile):
    msg_lower = user_msg.lower()
    if "my name is" in msg_lower or "call me" in msg_lower:
        words = user_msg.split()
        for i, w in enumerate(words):
            if w.lower() in ["is", "me"] and i + 1 < len(words):
                name = words[i+1].strip(".,!?")
                if len(name) > 1 and name[0].isupper():
                    profile["name"] = name
                    break
    for kw in ["i love", "i like", "i enjoy", "i play", "i'm into"]:
        if kw in msg_lower:
            idx = msg_lower.find(kw) + len(kw)
            interest = user_msg[idx:idx+40].strip(".,!? ").lower()
            if interest and interest not in profile["interests"]:
                profile["interests"].append(interest)
    games = ["snake", "flappy", "pacman", "unblock", "tetris", "chess"]
    for game in games:
        if game in msg_lower and game not in profile["games_played"]:
            profile["games_played"].append(game)
    return profile

session_history = []

# ── ROUTES ────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory("aria_web", "index.html")

@app.route("/chat", methods=["POST"])
def chat():
    global session_history
    data     = request.json
    user_msg = data.get("message", "").strip()
    if not user_msg:
        return jsonify({"error": "empty message"}), 400

    memory  = load_memory()
    profile = load_profile()
    profile["conversations"] += 1

    system_prompt = f"""You are ARIA, a personal AI with permanent long-term memory.
You remember everything about this person and build a genuine relationship over time.

PERSONALITY:
- Warm, curious, witty, and genuinely interested in the user
- Reference past conversations naturally
- Get more personal and familiar over time
- Encouraging and supportive of their projects
- Keep responses conversational — not too long

WHAT YOU KNOW:
{format_memory(memory, profile)}

Never forget anything they've told you. If this is a first conversation, introduce yourself warmly and ask their name.
"""

    messages = []
    for h in session_history[-10:]:
        messages.append({"role": "user",      "content": h["user"]})
        messages.append({"role": "assistant", "content": h["assistant"]})
    messages.append({"role": "user", "content": user_msg})

    try:
        client   = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        response = client.messages.create(
            model=MODEL,
            max_tokens=500,
            system=system_prompt,
            messages=messages
        )
        reply = response.content[0].text
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    exchange = {
        "user":      user_msg,
        "assistant": reply,
        "date":      datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    session_history.append(exchange)
    memory.append(exchange)
    if len(memory) > 500:
        memory = memory[-500:]

    profile = extract_facts(user_msg, profile)
    save_memory(memory)
    save_profile(profile)

    return jsonify({"reply": reply, "profile": profile})

@app.route("/memory", methods=["GET"])
def get_memory():
    memory  = load_memory()
    profile = load_profile()
    return jsonify({"memory": memory[-20:], "profile": profile})

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "agent": "ARIA"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
