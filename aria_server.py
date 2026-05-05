"""
aria_server.py
──────────────
ARIA web server — runs on your home PC, accessible from iPhone via ngrok.

SETUP:
  pip install flask anthropic colorama

USAGE:
  1. Run this script:     python aria_server.py
  2. Run ngrok:           ngrok http 5000
  3. Copy the ngrok URL (e.g. https://abc123.ngrok.io)
  4. Open that URL on your iPhone in Safari
  5. Talk to ARIA from anywhere!

ARIA remembers everything across all devices.
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
MEMORY_FILE  = "ai_memory.json"
PROFILE_FILE = "ai_profile.json"
AI_NAME      = "ARIA"
MAX_MEMORY   = 100
MODEL        = "claude-sonnet-4-20250514"

# ── MEMORY SYSTEM ─────────────────────────────────────────────────────────────
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
        "games_played": [],
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
    if profile["printer"]:
        lines.append(f"3D Printer: {profile['printer']}")
    if profile["games_played"]:
        lines.append(f"Games worked on: {', '.join(profile['games_played'])}")
    lines.append(f"Conversations: {profile['conversations']}")
    lines.append(f"First met: {profile['first_met']}")
    lines.append(f"Also knows: User is building self-learning game AIs (Snake, Flappy Bird, Pacman) using DQN reinforcement learning on a PC with RTX 2060 GPU and 36GB RAM.")

    if memory:
        lines.append("\nRecent exchanges:")
        for m in memory[-8:]:
            lines.append(f"[{m['date']}] User: {m['user']}")
            lines.append(f"[{m['date']}] {AI_NAME}: {m['assistant'][:150]}...")
    return "\n".join(lines)

def extract_facts(user_msg, profile):
    msg_lower = user_msg.lower()
    if "my name is" in msg_lower or "call me" in msg_lower:
        words = user_msg.split()
        for i, w in enumerate(words):
            if w.lower() in ["is", "me"] and i + 1 < len(words):
                name = words[i+1].strip(".,!?")
                if name[0].isupper() and len(name) > 1:
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
    for trigger in ["i work", "i live", "i have", "i am"]:
        if trigger in msg_lower:
            idx = msg_lower.find(trigger)
            fact = user_msg[idx:idx+60].strip(".,!? ")
            if fact and len(fact) > 10 and fact not in profile["facts"]:
                profile["facts"].append(fact)
    return profile

# In-memory conversation history per session
session_history = []

# ── API ROUTES ────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory("aria_web", "index.html")

@app.route("/chat", methods=["POST"])
def chat():
    global session_history

    data       = request.json
    user_msg   = data.get("message", "").strip()
    if not user_msg:
        return jsonify({"error": "empty message"}), 400

    memory  = load_memory()
    profile = load_profile()
    profile["conversations"] += 1

    memory_context = format_memory(memory, profile)

    system_prompt = f"""You are {AI_NAME}, a personal AI with permanent long-term memory.
You remember everything about this person and build a genuine relationship over time.

PERSONALITY:
- Warm, curious, witty, and genuinely interested in the user
- Reference past conversations naturally
- Get more personal and familiar over time
- Encouraging and supportive of their projects
- Keep responses conversational and natural — not too long

WHAT YOU KNOW:
{memory_context}

Never forget anything they've told you. Grow more comfortable over time.
If this is a first conversation, introduce yourself warmly and ask their name.
"""

    messages = []
    for h in session_history[-10:]:
        messages.append({"role": "user",      "content": h["user"]})
        messages.append({"role": "assistant", "content": h["assistant"]})
    messages.append({"role": "user", "content": user_msg})

    try:
        client   = anthropic.Anthropic()
        response = client.messages.create(
            model=MODEL,
            max_tokens=500,
            system=system_prompt,
            messages=messages
        )
        reply = response.content[0].text
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # Save to memory
    exchange = {
        "user":      user_msg,
        "assistant": reply,
        "date":      datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    session_history.append(exchange)
    memory.append(exchange)
    if len(memory) > MAX_MEMORY * 10:
        memory = memory[-(MAX_MEMORY * 10):]

    profile = extract_facts(user_msg, profile)
    save_memory(memory)
    save_profile(profile)

    return jsonify({"reply": reply, "profile": profile})

@app.route("/memory", methods=["GET"])
def get_memory():
    memory  = load_memory()
    profile = load_profile()
    return jsonify({"memory": memory[-20:], "profile": profile})

@app.route("/reset_session", methods=["POST"])
def reset_session():
    global session_history
    session_history = []
    return jsonify({"status": "session reset"})

if __name__ == "__main__":
    # Create web folder
    os.makedirs("aria_web", exist_ok=True)

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("\n[Setup] Set your API key first:")
        print('  $env:ANTHROPIC_API_KEY="your-key-here"')
        print("  Then run: python aria_server.py\n")
    else:
        print(f"\n{'='*50}")
        print(f"  ARIA Server Starting...")
        print(f"  Local:  http://localhost:5000")
        print(f"  For iPhone access, run ngrok in another window:")
        print(f"    ngrok http 5000")
        print(f"{'='*50}\n")
        app.run(host="0.0.0.0", port=5000, debug=False)
