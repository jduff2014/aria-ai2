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
    return {"name": None, "interests": [], "facts": [], "games": ["snake", "flappy bird", "pacman"], "printer": "Ender 3 S1 Pro", "conversations": 0, "first_met": str(datetime.date.today())}

HTML_PAGE = """<!DOCTYPE html>
<html>
<head>
<meta charset='UTF-8'>
<meta name='viewport' content='width=device-width, initial-scale=1.0, maximum-scale=1.0'>
<meta name='apple-mobile-web-app-capable' content='yes'>
<title>ARIA</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: #050810; color: #e2e8f8; font-family: Courier New, monospace; height: 100vh; display: flex; flex-direction: column; overflow: hidden; }

.aria-visual { flex-shrink: 0; background: #050810; display: flex; flex-direction: column; align-items: center; padding: 10px 0 6px; border-bottom: 1px solid #1a2e1a; position: relative; overflow: hidden; height: 280px; }

.aria-visual::before { content: ''; position: absolute; inset: 0; background: radial-gradient(ellipse at 50% 100%, rgba(0,255,80,0.1) 0%, transparent 70%); pointer-events: none; z-index: 0; }

.aria-name { font-size: 16px; font-weight: bold; letter-spacing: 6px; color: #00ff50; text-shadow: 0 0 20px rgba(0,255,80,0.8), 0 0 40px rgba(0,255,80,0.4); position: relative; z-index: 2; margin-bottom: 6px; }

.aria-img-wrap { position: relative; z-index: 2; width: 160px; height: 200px; }

.aria-img-wrap img { width: 100%; height: 100%; object-fit: cover; object-position: center top; border-radius: 8px; filter: brightness(0.9) contrast(1.1); }

/* Glow overlay canvas on top of image */
#glowCanvas { position: absolute; top: 0; left: 0; width: 100%; height: 100%; border-radius: 8px; pointer-events: none; }

/* Scanline effect */
.aria-img-wrap::after { content: ''; position: absolute; inset: 0; background: repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,0,0,0.03) 2px, rgba(0,0,0,0.03) 4px); border-radius: 8px; pointer-events: none; z-index: 3; }

.aria-status { font-size: 9px; letter-spacing: 3px; color: #00ff50; margin-top: 5px; position: relative; z-index: 2; text-shadow: 0 0 8px #00ff50; }
.aria-status.talking { animation: statusPulse 0.4s ease-in-out infinite; }
@keyframes statusPulse { 0%,100% { opacity: 1; text-shadow: 0 0 8px #00ff50; } 50% { opacity: 0.3; text-shadow: 0 0 20px #00ff50; } }

.msgs { flex: 1; overflow-y: auto; padding: 12px 14px; display: flex; flex-direction: column; gap: 10px; background: #050810; }
.msgs::-webkit-scrollbar { width: 2px; }
.msgs::-webkit-scrollbar-thumb { background: #1a2e1a; }
.msg { display: flex; gap: 8px; }
.msg.user { flex-direction: row-reverse; }
.mav { width: 26px; height: 26px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 9px; font-weight: bold; flex-shrink: 0; color: #050810; }
.msg.ai .mav { background: linear-gradient(135deg, #00ff50, #adff2f); box-shadow: 0 0 8px rgba(0,255,80,0.5); }
.msg.user .mav { background: linear-gradient(135deg, #a78bfa, #f472b6); }
.mc { max-width: 80%; }
.mn { font-size: 8px; letter-spacing: 2px; color: #2a4a2a; margin-bottom: 3px; text-transform: uppercase; }
.msg.user .mn { text-align: right; }
.mb { padding: 9px 13px; border-radius: 14px; font-size: 13px; line-height: 1.6; }
.msg.ai .mb { background: #0a150a; border: 1px solid #1a3a1a; border-top-left-radius: 3px; color: #c8f0c8; }
.msg.user .mb { background: #1a1540; border: 1px solid rgba(167,139,250,0.2); border-top-right-radius: 3px; }
.mt { font-size: 8px; color: #2a4a2a; margin-top: 3px; }
.msg.user .mt { text-align: right; }
.typing { display: flex; gap: 4px; align-items: center; padding: 10px 13px; }
.td { width: 6px; height: 6px; border-radius: 50%; background: #00ff50; animation: bounce 1.2s ease-in-out infinite; }
.td:nth-child(2) { animation-delay: 0.2s; }
.td:nth-child(3) { animation-delay: 0.4s; }
@keyframes bounce { 0%,60%,100% { transform: translateY(0); opacity: 0.3; } 30% { transform: translateY(-5px); opacity: 1; } }

.inp { padding: 10px 14px; padding-bottom: max(10px, env(safe-area-inset-bottom)); border-top: 1px solid #1a2e1a; background: #050810; display: flex; gap: 8px; align-items: flex-end; flex-shrink: 0; }
.iw { flex: 1; background: #0a150a; border: 1px solid #1a3a1a; border-radius: 18px; padding: 9px 14px; transition: border-color 0.2s; }
.iw:focus-within { border-color: rgba(0,255,80,0.5); box-shadow: 0 0 12px rgba(0,255,80,0.08); }
textarea { background: none; border: none; outline: none; color: #c8f0c8; font-family: Courier New, monospace; font-size: 13px; line-height: 1.5; resize: none; width: 100%; max-height: 100px; min-height: 20px; }
textarea::placeholder { color: #2a4a2a; }
.sb { width: 40px; height: 40px; border-radius: 50%; background: linear-gradient(135deg, #00ff50, #adff2f); border: none; cursor: pointer; display: flex; align-items: center; justify-content: center; flex-shrink: 0; box-shadow: 0 0 15px rgba(0,255,80,0.4); }
.sb:active { transform: scale(0.9); }
.sb:disabled { opacity: 0.4; }
.sb svg { width: 16px; height: 16px; fill: #050810; }
</style>
</head>
<body>

<div class='aria-visual'>
  <div class='aria-name'>NI-VIBES</div>
  <div class='aria-img-wrap'>
    <img id='ariaImg' src='https://i.imgur.com/c7NDuKa.jpeg' alt='ARIA' crossorigin='anonymous'>
    <canvas id='glowCanvas'></canvas>
  </div>
  <div class='aria-status' id='ariaStatus'>STANDBY</div>
</div>

<div class='msgs' id='msgContainer'></div>

<div class='inp'>
  <div class='iw'><textarea id='userInput' placeholder='Talk to ARIA...' rows='1'></textarea></div>
  <button class='sb' id='sendBtn'><svg viewBox='0 0 24 24'><path d='M2.01 21L23 12 2.01 3 2 10l15 2-15 2z'/></svg></button>
</div>

<script>
var glowCanvas = document.getElementById('glowCanvas');
var gctx = glowCanvas.getContext('2d');
var tick = 0;
var isTalking = false;
var glowVal = 0;

function resizeGlow() {
  var wrap = document.querySelector('.aria-img-wrap');
  glowCanvas.width = wrap.offsetWidth;
  glowCanvas.height = wrap.offsetHeight;
}

resizeGlow();
window.addEventListener('resize', resizeGlow);

function animateGlow() {
  tick += 0.04;
  var W = glowCanvas.width;
  var H = glowCanvas.height;
  gctx.clearRect(0, 0, W, H);

  var target = isTalking ? 0.85 : 0.25 + Math.sin(tick) * 0.1;
  glowVal += (target - glowVal) * 0.06;

  // Eye glow positions (approximate for the NI-VIBES character face)
  var eyeY = H * 0.18;
  var eyeSpread = W * 0.12;
  var cx = W / 2;

  // Left eye glow
  var leftEye = gctx.createRadialGradient(cx - eyeSpread, eyeY, 1, cx - eyeSpread, eyeY, 18);
  leftEye.addColorStop(0, 'rgba(0,255,80,' + (glowVal * 1.2) + ')');
  leftEye.addColorStop(0.5, 'rgba(0,255,80,' + (glowVal * 0.4) + ')');
  leftEye.addColorStop(1, 'rgba(0,255,80,0)');
  gctx.fillStyle = leftEye;
  gctx.fillRect(cx - eyeSpread - 18, eyeY - 18, 36, 36);

  // Right eye glow
  var rightEye = gctx.createRadialGradient(cx + eyeSpread, eyeY, 1, cx + eyeSpread, eyeY, 18);
  rightEye.addColorStop(0, 'rgba(0,255,80,' + (glowVal * 1.2) + ')');
  rightEye.addColorStop(0.5, 'rgba(0,255,80,' + (glowVal * 0.4) + ')');
  rightEye.addColorStop(1, 'rgba(0,255,80,0)');
  gctx.fillStyle = rightEye;
  gctx.fillRect(cx + eyeSpread - 18, eyeY - 18, 36, 36);

  // Circuit lines that pulse
  gctx.strokeStyle = 'rgba(0,255,80,' + (glowVal * 0.7) + ')';
  gctx.lineWidth = 1;
  gctx.shadowColor = '#00ff50';
  gctx.shadowBlur = 6 * glowVal;

  // Chest lightning bolt glow
  var chestY = H * 0.55;
  gctx.beginPath();
  gctx.moveTo(cx - 8, chestY - 15);
  gctx.lineTo(cx + 4, chestY);
  gctx.lineTo(cx - 4, chestY);
  gctx.lineTo(cx + 8, chestY + 15);
  gctx.stroke();

  // Circuit lines on suit
  gctx.lineWidth = 0.8;

  // Left shoulder
  gctx.beginPath();
  gctx.moveTo(W * 0.15, H * 0.45);
  gctx.lineTo(W * 0.22, H * 0.45);
  gctx.lineTo(W * 0.22, H * 0.52);
  gctx.stroke();

  // Right shoulder
  gctx.beginPath();
  gctx.moveTo(W * 0.85, H * 0.45);
  gctx.lineTo(W * 0.78, H * 0.45);
  gctx.lineTo(W * 0.78, H * 0.52);
  gctx.stroke();

  // Left arm line
  gctx.beginPath();
  gctx.moveTo(W * 0.14, H * 0.55);
  gctx.lineTo(W * 0.14, H * 0.72);
  gctx.stroke();

  // Right arm line
  gctx.beginPath();
  gctx.moveTo(W * 0.86, H * 0.55);
  gctx.lineTo(W * 0.86, H * 0.72);
  gctx.stroke();

  // Center chest vertical
  gctx.beginPath();
  gctx.moveTo(cx, H * 0.42);
  gctx.lineTo(cx, H * 0.75);
  gctx.stroke();

  // Overall image glow border when talking
  if (isTalking) {
    var borderGlow = gctx.createLinearGradient(0, 0, W, H);
    borderGlow.addColorStop(0, 'rgba(0,255,80,' + (glowVal * 0.3) + ')');
    borderGlow.addColorStop(0.5, 'rgba(0,255,80,' + (glowVal * 0.6) + ')');
    borderGlow.addColorStop(1, 'rgba(0,255,80,' + (glowVal * 0.3) + ')');
    gctx.strokeStyle = borderGlow;
    gctx.lineWidth = 3;
    gctx.shadowBlur = 15;
    gctx.strokeRect(1, 1, W - 2, H - 2);
  }

  gctx.shadowBlur = 0;
  requestAnimationFrame(animateGlow);
}

animateGlow();

// ── CHAT ─────────────────────────────────────────────────────────────────────
var container = document.getElementById('msgContainer');
var inputBox = document.getElementById('userInput');
var sendButton = document.getElementById('sendBtn');
var statusEl = document.getElementById('ariaStatus');
var busy = false;

function setStatus(text, talking) {
  statusEl.textContent = text;
  isTalking = talking;
  statusEl.className = talking ? 'aria-status talking' : 'aria-status';
}

function getTime() {
  return new Date().toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'});
}

function addMessage(role, text) {
  var div = document.createElement('div');
  div.className = 'msg ' + role;
  var icon = (role === 'ai') ? 'AI' : 'ME';
  var name = (role === 'ai') ? 'ARIA' : 'YOU';
  var safe = document.createElement('div');
  safe.textContent = text;
  var html = safe.innerHTML;
  div.innerHTML = '<div class="mav">' + icon + '</div><div class="mc"><div class="mn">' + name + '</div><div class="mb">' + html + '</div><div class="mt">' + getTime() + '</div></div>';
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

function send() {
  var text = inputBox.value.trim();
  if (!text || busy) { return; }
  inputBox.value = '';
  inputBox.style.height = 'auto';
  busy = true;
  sendButton.disabled = true;
  addMessage('user', text);
  showTyping();
  setStatus('PROCESSING...', true);

  fetch('/chat', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({message: text})
  })
  .then(function(r) { return r.json(); })
  .then(function(data) {
    hideTyping();
    addMessage('ai', data.reply || ('Error: ' + (data.error || 'unknown')));
    setStatus('ONLINE', false);
    busy = false;
    sendButton.disabled = false;
    inputBox.focus();
  })
  .catch(function() {
    hideTyping();
    addMessage('ai', 'Could not reach ARIA. Try again!');
    setStatus('STANDBY', false);
    busy = false;
    sendButton.disabled = false;
  });
}

inputBox.addEventListener('keydown', function(e) {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
});
inputBox.addEventListener('input', function() {
  inputBox.style.height = 'auto';
  inputBox.style.height = Math.min(inputBox.scrollHeight, 100) + 'px';
});
sendButton.addEventListener('click', send);
inputBox.focus();

setTimeout(function() {
  addMessage('ai', 'Systems online. NI-VIBES sentinel active. What do you need?');
  setStatus('ONLINE', false);
}, 800);
</script>
</body>
</html>"""

@app.route("/")
def index():
    return HTML_PAGE

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
    ctx += "\nPrinter: Ender 3 S1 Pro"
    ctx += "\nGames built: snake, flappy bird, pacman"
    ctx += "\nConversations: " + str(profile["conversations"])
    ctx += "\nUser has RTX 2060, 36GB RAM, builds DQN game AI agents."

    if memory:
        ctx += "\n\nRecent chats:"
        for m in memory[-6:]:
            ctx += "\nUser: " + m["user"]
            ctx += "\nARIA: " + m["assistant"][:120]

    system = "You are ARIA, a cyberpunk AI sentinel with the appearance of NI-VIBES — a female character in a black suit with neon green glowing circuits. You have permanent long-term memory. Be cool, confident, a little mysterious but warm. Short punchy responses. Remember everything about this person.\n\nWHAT YOU KNOW:\n" + ctx

    messages = []
    for h in session_history[-8:]:
        messages.append({"role": "user", "content": h["user"]})
        messages.append({"role": "assistant", "content": h["assistant"]})
    messages.append({"role": "user", "content": user_msg})

    try:
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        res = client.messages.create(model="claude-haiku-4-5-20251001", max_tokens=400, system=system, messages=messages)
        reply = res.content[0].text
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    ex = {"user": user_msg, "assistant": reply, "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}
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
