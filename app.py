from flask import Flask, request, jsonify
import json, os, datetime, anthropic
from pathlib import Path

app = Flask(__name__)

MEMORY_FILE = "/tmp/memory.json"
PROFILE_FILE = "/tmp/profile.json"
session_history = []

def load_json(path, default):
    try:
        if Path(path).exists():
            with open(path) as f:
                return json.load(f)
    except:
        pass
    return default

def save_json(path, data):
    try:
        with open(path, "w") as f:
            json.dump(data, f)
    except:
        pass

def default_profile():
    return {
        "name": None,
        "interests": [],
        "facts": [],
        "games": ["snake", "flappy bird", "pacman"],
        "printer": "Ender 3 S1 Pro",
        "conversations": 0,
        "first_met": str(datetime.date.today())
    }

@app.route("/")
def index():
    return """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
<title>ARIA</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: #080b14; color: #e2e8f8; font-family: Courier New, monospace; height: 100vh; display: flex; flex-direction: column; overflow: hidden; }
header { padding: 14px 16px; border-bottom: 1px solid #1c2540; display: flex; align-items: center; gap: 12px; background: #080b14; flex-shrink: 0; }
.av { width: 38px; height: 38px; border-radius: 50%; background: linear-gradient(135deg, #5effd8, #a78bfa); display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: bold; color: #080b14; }
.hn { font-size: 16px; font-weight: bold; letter-spacing: 3px; color: #5effd8; }
.hs { font-size: 10px; color: #4a5580; letter-spacing: 1px; margin-top: 2px; }
.msgs { flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 12px; }
.msg { display: flex; gap: 8px; }
.msg.user { flex-direction: row-reverse; }
.mav { width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 10px; font-weight: bold; flex-shrink: 0; color: #080b14; }
.msg.ai .mav { background: linear-gradient(135deg, #5effd8, #a78bfa); }
.msg.user .mav { background: linear-gradient(135deg, #a78bfa, #f472b6); }
.mc { max-width: 78%; }
.mn { font-size: 9px; letter-spacing: 2px; color: #4a5580; margin-bottom: 4px; text-transform: uppercase; }
.msg.user .mn { text-align: right; }
.mb { padding: 10px 14px; border-radius: 14px; font-size: 13px; line-height: 1.6; }
.msg.ai .mb { background: #0d1220; border: 1px solid #1c2540; border-top-left-radius: 3px; }
.msg.user .mb { background: #1a2540; border: 1px solid rgba(167,139,250,0.2); border-top-right-radius: 3px; }
.mt { font-size: 9px; color: #4a5580; margin-top: 4px; }
.msg.user .mt { text-align: right; }
.typing { display: flex; gap: 4px; align-items: center; padding: 12px 14px; }
.td { width: 6px; height: 6px; border-radius: 50%; background: #5effd8; animation: bounce 1.2s ease-in-out infinite; }
.td:nth-child(2) { animation-delay: 0.2s; background: #a78bfa; }
.td:nth-child(3) { animation-delay: 0.4s; background: #f472b6; }
@keyframes bounce { 0%, 60%, 100% { transform: translateY(0); opacity: 0.4; } 30% { transform: translateY(-5px); opacity: 1; } }
.inp { padding: 10px 14px; border-top: 1px solid #1c2540; background: #080b14; display: flex; gap: 8px; align-items: flex-end; flex-shrink: 0; }
.iw { flex: 1; background: #0d1220; border: 1px solid #1c2540; border-radius: 18px; padding: 9px 14px; }
textarea { background: none; border: none; outline: none; color: #e2e8f8; font-family: Courier New, monospace; font-size: 13px; line-height: 1.5; resize: none; width: 100%; max-height: 100px; min-height: 20px; }
textarea::placeholder { color: #4a5580; }
.sb { width: 40px; height: 40px; border-radius: 50%; background: linear-gradient(135deg, #5effd8, #a78bfa); border: none; cursor: pointer; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.sb:disabled { opacity: 0.4; }
.sb svg { width: 16px; height: 16px; fill: #080b14; }
.welcome { text-align: center; padding: 40px 20px; color: #4a5580; }
.wl { font-size: 42px; font-weight: bold; letter-spacing: 8px; color: #5effd8; margin-bottom: 8px; }
.welcome p { font-size: 11px; letter-spacing: 2px; line-height: 2; }
</style>
</head>
<body>
<header>
  <div class="av">AI</div>
  <div>
    <div class="hn">ARIA</div>
    <div class="hs">ONLINE - REMEMBERS EVERYTHING</div>
  </div>
</header>
<div class="msgs" id="msgContainer">
  <div class="welcome">
    <div class="wl">ARIA</div>
    <p>Your personal AI.<br>She remembers everything.<br>Forever.</p>
  </div>
</div>
<div class="inp">
  <div class="iw">
    <textarea id="userInput" placeholder="Talk to ARIA..." rows="1"></textarea>
  </div>
  <button class="sb" id="sendBtn">
    <svg viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
  </button>
</div>
<script>
var container = document.getElementById('msgContainer');
var inputBox = document.getElementById('userInput');
var sendButton = document.getElementById('sendBtn');
var busy = false;

function getTime() {
  return new Date().toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'});
}

function addMessage(role, text) {
  var welcome = container.querySelector('.welcome');
  if (welcome) { welcome.remove(); }
  var div = document.createElement('div');
  div.className = 'msg ' + role;
  var icon = (role === 'ai') ? 'AI' : 'ME';
  var name = (role === 'ai') ? 'ARIA' : 'YOU';
  var safe = text.replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\n/g, '<br>');
  div.innerHTML = '<div class="mav">' + icon + '</div><div class="mc"><div class="mn">' + name + '</div><div class="mb">' + safe + '</div><div class="mt">' + getTime() + '</div></div>';
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function showTyping() {
  var div = document.createElement('div');
  div.className = 'msg ai';
  div.id = 'typingDiv';
  div.innerHTML = '<div class="mav">AI</div><div class="mc"><div class="mn">ARIA</div><div class="mb typing"><div class="td"></div><div class="td"></div><div class="td"></div></div></div>';
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function hideTyping() {
  var t = document.getElementById('typingDiv');
  if (t) { t.remove(); }
}

function sendMessage() {
  var text = inputBox.value.trim();
  if (!text || busy) { return; }
  inputBox.value = '';
  inputBox.style.height = 'auto';
  busy = true;
  sendButton.disabled = true;
  addMessage('user', text);
  showTyping();
  fetch('/chat', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({message: text})
  })
  .then(function(r) { return r.json(); })
  .then(function(data) {
    hideTyping();
    addMessage('ai', data.reply || ('Error: ' + (data.error || 'unknown')));
    busy = false;
    sendButton.disabled = false;
    inputBox.focus();
  })
  .catch(function() {
    hideTyping();
    addMessage('ai', 'Could not reach ARIA. Try again!');
    busy = false;
    sendButton.disabled = false;
  });
}

inputBox.addEventListener('keydown', function(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

inputBox.addEventListener('input', function() {
  inputBox.style.height = 'auto';
  inputBox.style.height = Math.min(inputBox.scrollHeight, 100) + 'px';
});

sendButton.addEventListener('click', sendMessage);
inputBox.focus();
</script>
</body>
</html>"""

@app.route("/chat", methods=["POST"])
def chat():
    global session_history
    user_msg = request.json.get("message", "").strip()
    if not user_msg:
        return jsonify({"error": "empty"}), 400

    memory = load_json(MEMORY_FILE, [])
    profile = load_json(PROFILE_FILE, default_profile())
    profile["conversations"] += 1

    ctx = "Name: " + str(profile.get("name", "unknown"))
    ctx += "\nInterests: " + str(profile.get("interests", []))
    ctx += "\nPrinter: " + str(profile.get("printer", "Ender 3 S1 Pro"))
    ctx += "\nGames built: " + str(profile.get("games", []))
    ctx += "\nConversations: " + str(profile["conversations"])
    ctx += "\nUser has RTX 2060, 36GB RAM, builds DQN game AI agents."

    if memory:
        ctx += "\n\nRecent chats:"
        for m in memory[-6:]:
            ctx += "\nUser: " + m["user"]
            ctx += "\nARIA: " + m["assistant"][:120]

    system = "You are ARIA, a personal AI with permanent long-term memory. Remember everything about this person. Be warm, witty, curious. Keep responses conversational and concise.\n\nWHAT YOU KNOW:\n" + ctx

    messages = []
    for h in session_history[-8:]:
        messages.append({"role": "user", "content": h["user"]})
        messages.append({"role": "assistant", "content": h["assistant"]})
    messages.append({"role": "user", "content": user_msg})

    try:
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        res = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=400,
            system=system,
            messages=messages
        )
        reply = res.content[0].text
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    ex = {
        "user": user_msg,
        "assistant": reply,
        "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    session_history.append(ex)
    memory.append(ex)
    if len(memory) > 500:
        memory = memory[-500:]

    ml = user_msg.lower()
    for kw in ["i love", "i like", "i enjoy", "i play"]:
        if kw in ml:
            idx = ml.find(kw) + len(kw)
            interest = user_msg[idx:idx+40].strip(".,!? ").lower()
            if interest and interest not in profile["interests"]:
                profile["interests"].append(interest)
    if "my name is" in ml:
        words = user_msg.split()
        for i, w in enumerate(words):
            if w.lower() == "is" and i + 1 < len(words):
                n = words[i+1].strip(".,!?")
                if len(n) > 1 and n[0].isupper():
                    profile["name"] = n
                    break

    save_json(MEMORY_FILE, memory[-500:])
    save_json(PROFILE_FILE, profile)
    return jsonify({"reply": reply})

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
