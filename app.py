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

/* ARIA AVATAR */
.aria-visual { flex-shrink: 0; background: #050810; display: flex; flex-direction: column; align-items: center; padding: 12px 0 8px; border-bottom: 1px solid #1a2e1a; position: relative; overflow: hidden; }
.aria-visual::before { content: ''; position: absolute; inset: 0; background: radial-gradient(ellipse at 50% 100%, rgba(0,255,80,0.08) 0%, transparent 70%); pointer-events: none; }

/* City background lines */
.city-bg { position: absolute; bottom: 0; left: 0; right: 0; height: 60px; opacity: 0.15; }

/* Avatar canvas */
#ariaCanvas { position: relative; z-index: 2; }

.aria-status { font-size: 9px; letter-spacing: 3px; color: #00ff50; margin-top: 4px; position: relative; z-index: 2; text-shadow: 0 0 8px #00ff50; }
.aria-status.talking { color: #adff2f; animation: statusPulse 0.5s ease-in-out infinite; }
@keyframes statusPulse { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }

.aria-name { font-size: 18px; font-weight: bold; letter-spacing: 6px; color: #00ff50; text-shadow: 0 0 20px rgba(0,255,80,0.6), 0 0 40px rgba(0,255,80,0.3); position: relative; z-index: 2; margin-bottom: 2px; }

/* MESSAGES */
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

/* INPUT */
.inp { padding: 10px 14px; padding-bottom: max(10px, env(safe-area-inset-bottom)); border-top: 1px solid #1a2e1a; background: #050810; display: flex; gap: 8px; align-items: flex-end; flex-shrink: 0; }
.iw { flex: 1; background: #0a150a; border: 1px solid #1a3a1a; border-radius: 18px; padding: 9px 14px; transition: border-color 0.2s; }
.iw:focus-within { border-color: rgba(0,255,80,0.4); box-shadow: 0 0 10px rgba(0,255,80,0.05); }
textarea { background: none; border: none; outline: none; color: #c8f0c8; font-family: Courier New, monospace; font-size: 13px; line-height: 1.5; resize: none; width: 100%; max-height: 100px; min-height: 20px; }
textarea::placeholder { color: #2a4a2a; }
.sb { width: 40px; height: 40px; border-radius: 50%; background: linear-gradient(135deg, #00ff50, #adff2f); border: none; cursor: pointer; display: flex; align-items: center; justify-content: center; flex-shrink: 0; box-shadow: 0 0 15px rgba(0,255,80,0.3); transition: all 0.2s; }
.sb:active { transform: scale(0.9); }
.sb:disabled { opacity: 0.4; }
.sb svg { width: 16px; height: 16px; fill: #050810; }
</style>
</head>
<body>

<!-- ARIA VISUAL -->
<div class='aria-visual'>
  <div class='aria-name'>NI-VIBES</div>
  <canvas id='ariaCanvas' width='200' height='160'></canvas>
  <div class='aria-status' id='ariaStatus'>STANDBY</div>
</div>

<!-- MESSAGES -->
<div class='msgs' id='msgContainer'></div>

<!-- INPUT -->
<div class='inp'>
  <div class='iw'><textarea id='userInput' placeholder='Talk to ARIA...' rows='1'></textarea></div>
  <button class='sb' id='sendBtn'><svg viewBox='0 0 24 24'><path d='M2.01 21L23 12 2.01 3 2 10l15 2-15 2z'/></svg></button>
</div>

<script>
// ── ARIA AVATAR DRAWING ──────────────────────────────────────────────────────
var canvas = document.getElementById('ariaCanvas');
var ctx = canvas.getContext('2d');
var W = canvas.width, H = canvas.height;
var tick = 0;
var isTalking = false;
var glowIntensity = 0;

function drawARIA() {
  ctx.clearRect(0, 0, W, H);
  tick += 0.03;

  // Target glow
  var targetGlow = isTalking ? 1.0 : 0.4 + Math.sin(tick) * 0.15;
  glowIntensity += (targetGlow - glowIntensity) * 0.08;

  var cx = W / 2;
  var g = glowIntensity;

  // Background glow
  var bgGrad = ctx.createRadialGradient(cx, H, 10, cx, H, 120);
  bgGrad.addColorStop(0, 'rgba(0,255,80,' + (g * 0.15) + ')');
  bgGrad.addColorStop(1, 'rgba(0,0,0,0)');
  ctx.fillStyle = bgGrad;
  ctx.fillRect(0, 0, W, H);

  // Draw cyberpunk figure
  drawBody(cx, g);
  drawCircuits(cx, g);
  drawHead(cx, g);
  drawHair(cx, g);
  drawEyes(cx, g);

  requestAnimationFrame(drawARIA);
}

function drawBody(cx, g) {
  // Torso
  var torsoGrad = ctx.createLinearGradient(cx - 28, 70, cx + 28, 70);
  torsoGrad.addColorStop(0, '#0a0a0a');
  torsoGrad.addColorStop(0.5, '#111');
  torsoGrad.addColorStop(1, '#0a0a0a');
  ctx.fillStyle = torsoGrad;
  ctx.beginPath();
  ctx.moveTo(cx - 28, 75);
  ctx.lineTo(cx + 28, 75);
  ctx.lineTo(cx + 22, 140);
  ctx.lineTo(cx - 22, 140);
  ctx.closePath();
  ctx.fill();

  // Suit glow lines on torso
  ctx.strokeStyle = 'rgba(0,255,80,' + (g * 0.9) + ')';
  ctx.lineWidth = 1;
  ctx.shadowColor = '#00ff50';
  ctx.shadowBlur = 8 * g;

  // Center chest line
  ctx.beginPath();
  ctx.moveTo(cx, 78);
  ctx.lineTo(cx, 130);
  ctx.stroke();

  // Lightning bolt chest
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(cx - 6, 88);
  ctx.lineTo(cx + 2, 100);
  ctx.lineTo(cx - 2, 100);
  ctx.lineTo(cx + 6, 112);
  ctx.stroke();

  // Collar
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.moveTo(cx - 20, 75);
  ctx.lineTo(cx - 10, 68);
  ctx.lineTo(cx + 10, 68);
  ctx.lineTo(cx + 20, 75);
  ctx.stroke();

  // Arms
  ctx.fillStyle = '#0d0d0d';
  // Left arm
  ctx.beginPath();
  ctx.moveTo(cx - 28, 78);
  ctx.lineTo(cx - 45, 90);
  ctx.lineTo(cx - 42, 135);
  ctx.lineTo(cx - 30, 135);
  ctx.lineTo(cx - 28, 78);
  ctx.fill();
  // Right arm
  ctx.beginPath();
  ctx.moveTo(cx + 28, 78);
  ctx.lineTo(cx + 45, 90);
  ctx.lineTo(cx + 42, 135);
  ctx.lineTo(cx + 30, 135);
  ctx.lineTo(cx + 28, 78);
  ctx.fill();

  // Arm glow lines
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(cx - 36, 85);
  ctx.lineTo(cx - 38, 125);
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(cx + 36, 85);
  ctx.lineTo(cx + 38, 125);
  ctx.stroke();

  ctx.shadowBlur = 0;

  // Legs (just tops visible)
  ctx.fillStyle = '#0a0a0a';
  ctx.fillRect(cx - 20, 138, 16, 22);
  ctx.fillRect(cx + 4, 138, 16, 22);

  // Leg glow
  ctx.strokeStyle = 'rgba(0,255,80,' + (g * 0.7) + ')';
  ctx.shadowColor = '#00ff50';
  ctx.shadowBlur = 6 * g;
  ctx.beginPath();
  ctx.moveTo(cx - 12, 140);
  ctx.lineTo(cx - 10, 158);
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(cx + 12, 140);
  ctx.lineTo(cx + 10, 158);
  ctx.stroke();
  ctx.shadowBlur = 0;
}

function drawCircuits(cx, g) {
  ctx.strokeStyle = 'rgba(0,255,80,' + (g * 0.5) + ')';
  ctx.lineWidth = 0.5;
  ctx.shadowColor = '#00ff50';
  ctx.shadowBlur = 4 * g;

  // Left shoulder circuits
  ctx.beginPath();
  ctx.moveTo(cx - 40, 95);
  ctx.lineTo(cx - 35, 95);
  ctx.lineTo(cx - 35, 100);
  ctx.lineTo(cx - 30, 100);
  ctx.stroke();

  ctx.beginPath();
  ctx.moveTo(cx - 42, 108);
  ctx.lineTo(cx - 36, 108);
  ctx.lineTo(cx - 36, 113);
  ctx.stroke();

  // Right shoulder circuits
  ctx.beginPath();
  ctx.moveTo(cx + 40, 95);
  ctx.lineTo(cx + 35, 95);
  ctx.lineTo(cx + 35, 100);
  ctx.lineTo(cx + 30, 100);
  ctx.stroke();

  ctx.beginPath();
  ctx.moveTo(cx + 42, 108);
  ctx.lineTo(cx + 36, 108);
  ctx.lineTo(cx + 36, 113);
  ctx.stroke();

  // Torso circuits
  ctx.beginPath();
  ctx.moveTo(cx - 18, 120);
  ctx.lineTo(cx - 8, 120);
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(cx + 18, 120);
  ctx.lineTo(cx + 8, 120);
  ctx.stroke();

  ctx.shadowBlur = 0;
}

function drawHead(cx, g) {
  // Neck
  ctx.fillStyle = '#c8a882';
  ctx.fillRect(cx - 8, 58, 16, 12);

  // Head shape
  var headGrad = ctx.createRadialGradient(cx - 5, 35, 5, cx, 40, 22);
  headGrad.addColorStop(0, '#d4b896');
  headGrad.addColorStop(0.7, '#c8a882');
  headGrad.addColorStop(1, '#b89870');
  ctx.fillStyle = headGrad;
  ctx.beginPath();
  ctx.ellipse(cx, 40, 20, 24, 0, 0, Math.PI * 2);
  ctx.fill();
}

function drawHair(cx, g) {
  ctx.fillStyle = '#3a2010';

  // Top hair / bun
  ctx.beginPath();
  ctx.ellipse(cx + 4, 18, 14, 10, 0.3, 0, Math.PI * 2);
  ctx.fill();

  // Hair sides
  ctx.beginPath();
  ctx.moveTo(cx - 18, 35);
  ctx.quadraticCurveTo(cx - 22, 50, cx - 15, 62);
  ctx.lineTo(cx - 12, 62);
  ctx.quadraticCurveTo(cx - 20, 48, cx - 16, 35);
  ctx.fill();

  ctx.beginPath();
  ctx.moveTo(cx + 18, 35);
  ctx.quadraticCurveTo(cx + 22, 50, cx + 15, 62);
  ctx.lineTo(cx + 12, 62);
  ctx.quadraticCurveTo(cx + 20, 48, cx + 16, 35);
  ctx.fill();

  // Hair strands
  ctx.strokeStyle = '#5a3520';
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(cx - 5, 20);
  ctx.quadraticCurveTo(cx - 15, 32, cx - 18, 45);
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(cx + 8, 18);
  ctx.quadraticCurveTo(cx + 16, 30, cx + 18, 44);
  ctx.stroke();
}

function drawEyes(cx, g) {
  // Eye glow - reacts to talking
  var eyeGlow = isTalking ? g * 1.2 : g * 0.7;
  var blinkVal = Math.sin(tick * 0.3);
  var eyeH = blinkVal > 0.95 ? 1 : 4;

  ctx.shadowColor = '#00ff50';
  ctx.shadowBlur = 12 * eyeGlow;

  // Left eye
  ctx.fillStyle = 'rgba(0,255,80,' + eyeGlow + ')';
  ctx.beginPath();
  ctx.ellipse(cx - 7, 38, 4, eyeH, 0, 0, Math.PI * 2);
  ctx.fill();

  // Right eye
  ctx.beginPath();
  ctx.ellipse(cx + 7, 38, 4, eyeH, 0, 0, Math.PI * 2);
  ctx.fill();

  ctx.shadowBlur = 0;

  // Eyebrows
  ctx.strokeStyle = '#5a3520';
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.moveTo(cx - 11, 33);
  ctx.lineTo(cx - 3, 32);
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(cx + 3, 32);
  ctx.lineTo(cx + 11, 33);
  ctx.stroke();

  // Nose
  ctx.strokeStyle = '#b89870';
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(cx, 42);
  ctx.lineTo(cx - 3, 50);
  ctx.lineTo(cx + 3, 50);
  ctx.stroke();

  // Mouth - animated when talking
  ctx.strokeStyle = '#a08060';
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  if (isTalking) {
    var mouthOpen = Math.abs(Math.sin(tick * 8)) * 3;
    ctx.ellipse(cx, 55, 5, mouthOpen + 0.5, 0, 0, Math.PI * 2);
  } else {
    ctx.moveTo(cx - 5, 55);
    ctx.quadraticCurveTo(cx, 57, cx + 5, 55);
  }
  ctx.stroke();

  // Cheek glow marks
  ctx.fillStyle = 'rgba(0,255,80,' + (eyeGlow * 0.4) + ')';
  ctx.beginPath();
  ctx.ellipse(cx - 14, 45, 3, 1.5, -0.3, 0, Math.PI * 2);
  ctx.fill();
  ctx.beginPath();
  ctx.ellipse(cx + 14, 45, 3, 1.5, 0.3, 0, Math.PI * 2);
  ctx.fill();
}

drawARIA();

// ── CHAT LOGIC ───────────────────────────────────────────────────────────────
var container = document.getElementById('msgContainer');
var inputBox = document.getElementById('userInput');
var sendButton = document.getElementById('sendBtn');
var statusEl = document.getElementById('ariaStatus');
var busy = false;

function setStatus(text, talking) {
  statusEl.textContent = text;
  isTalking = talking;
  if (talking) {
    statusEl.className = 'aria-status talking';
  } else {
    statusEl.className = 'aria-status';
  }
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

// Initial greeting
setTimeout(function() {
  addMessage('ai', 'Hey. I am ARIA. NI-VIBES class sentinel. Online and ready. What do you need?');
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

    system = "You are ARIA, a cyberpunk AI sentinel with the appearance of NI-VIBES — a black suit with neon green circuits. You have permanent long-term memory. Be cool, confident, a little mysterious but warm. Short punchy responses. Remember everything about this person.\n\nWHAT YOU KNOW:\n" + ctx

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
