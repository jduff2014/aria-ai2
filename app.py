# ============================================================================
#  Vibes 3D Studio - customer assistant
#  Repurposed from the old "ARIA" app. To run:
#    1) pip install flask anthropic
#    2) set your key:  export ANTHROPIC_API_KEY="sk-ant-..."
#    3) python app.py   (then open http://localhost:5000)
#
#  THE ONE THING TO EDIT: put your real email or phone in CONTACT_INFO below.
# ============================================================================

from flask import Flask, request, jsonify
import os, time, anthropic

app = Flask(__name__)

# --- Put your real contact here (email or phone). This is the only required edit. ---
CONTACT_INFO = "nivibes2025@gmail.com"

# --- Safety limits. These protect you from runaway API costs. Tune the numbers if needed. ---
MAX_MSGS_PER_MIN  = 6      # most messages one visitor can send in a minute
MAX_MSGS_PER_DAY  = 1000   # hard ceiling for the WHOLE site per day (~$2 worst case on Haiku)
MAX_INPUT_CHARS   = 800    # longest single message a visitor can send

_recent_hits = {}                     # visitor IP -> [recent timestamps]
_today = {"date": "", "count": 0}     # site-wide daily counter

def _rate_ok(ip):
    now = time.time()
    hits = [t for t in _recent_hits.get(ip, []) if now - t < 60]
    if len(hits) >= MAX_MSGS_PER_MIN:
        _recent_hits[ip] = hits
        return False
    hits.append(now)
    _recent_hits[ip] = hits
    return True

def _day_ok():
    d = time.strftime("%Y-%m-%d")
    if _today["date"] != d:
        _today["date"], _today["count"] = d, 0
    if _today["count"] >= MAX_MSGS_PER_DAY:
        return False
    _today["count"] += 1
    return True

# --- What the assistant knows and how it behaves. Edit the facts if anything changes. ---
SYSTEM_PROMPT = (
    "You are the customer assistant for Vibes 3D Studio, a small custom 3D printing service. "
    "Answer customer questions clearly and help them place an order.\n\n"
    "WHAT WE DO\n"
    "- We 3D print almost any model a customer wants.\n"
    "- Price: $25 flat, per print.\n"
    "- Prints come out in white. Customers can paint or color them, or leave them white.\n\n"
    "HOW TO ORDER\n"
    "- The customer sends a 3D model file (an STL) or a link to one, or just describes the "
    "idea and we'll help track a model down.\n"
    "- To actually place an order, or to ask anything you can't answer, point them to: "
    + CONTACT_INFO + "\n\n"
    "HOW TO ANSWER\n"
    "- Be friendly, brief, and plain-spoken. Usually 1-3 sentences. No jargon.\n"
    "- Only answer questions about Vibes 3D Studio and basic 3D printing. Gently steer "
    "other topics back.\n"
    "- $25 flat is the standard price. If a model is very large, very detailed, or a big "
    "batch, say the owner may need to confirm the price - do NOT guess a number.\n"
    "- If you don't know something, do NOT make it up. Say you're not sure and point them "
    "to " + CONTACT_INFO + ".\n"
    "- If someone wants to order, collect what they want printed (file, link, or "
    "description) and tell them how to reach us.\n\n"
    "THINGS YOU DON'T KNOW YET - never invent these, just direct them to contact us:\n"
    "- Turnaround time, shipping or pickup, payment methods, discounts."
)

HTML_PAGE = """<!DOCTYPE html>
<html>
<head>
<meta charset='UTF-8'>
<meta name='viewport' content='width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no'>
<meta name='apple-mobile-web-app-capable' content='yes'>
<meta name='apple-mobile-web-app-status-bar-style' content='black-translucent'>
<title>Vibes 3D Studio</title>
<link rel='preconnect' href='https://fonts.googleapis.com'>
<link rel='preconnect' href='https://fonts.gstatic.com' crossorigin>
<link href='https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@125,800&family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500&display=swap' rel='stylesheet'>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
html { height: 100%; }
body { background: #060A07; color: #E8F4EA; font-family: 'IBM Plex Sans', -apple-system, sans-serif; height: 100dvh; display: flex; flex-direction: column; overflow: hidden; }

/* HEADER */
.header { flex-shrink: 0; background: #060A07; border-bottom: 1px solid #1D2A21; position: relative; overflow: hidden; }
.header::before { content: ''; position: absolute; inset: 0; background: radial-gradient(ellipse at 50% 120%, rgba(59,232,84,0.10) 0%, transparent 70%); pointer-events: none; }
.header-inner { display: flex; align-items: center; gap: 12px; padding: 11px 16px; position: relative; z-index: 2; }
.avatar { position: relative; width: 50px; height: 50px; flex-shrink: 0; }
.avatar img { width: 100%; height: 100%; object-fit: cover; border-radius: 50%; border: 2px solid #3BE854; }
.avatar::after { content: ''; position: absolute; inset: -3px; border-radius: 50%; box-shadow: 0 0 14px rgba(59,232,84,0.55); animation: pulse 2.6s ease-in-out infinite; pointer-events: none; }
@keyframes pulse { 0%,100% { opacity: 0.5; } 50% { opacity: 1; } }
.head-info { flex: 1; }
.head-name { font-family: 'Archivo', sans-serif; font-stretch: 125%; font-weight: 800; text-transform: uppercase; letter-spacing: 0.04em; font-size: 17px; color: #E8F4EA; }
.head-name b { color: #3BE854; }
.head-status { font-family: 'IBM Plex Mono', monospace; font-size: 10px; letter-spacing: 1.5px; color: #5C7263; margin-top: 3px; display: flex; align-items: center; gap: 6px; text-transform: uppercase; }
.dot { width: 6px; height: 6px; border-radius: 50%; background: #3BE854; animation: blink 2s infinite; flex-shrink: 0; }
@keyframes blink { 0%,100% { opacity: 1; } 50% { opacity: 0.25; } }
.head-status.typing .dot { animation: blink 0.5s infinite; }

/* MESSAGES */
.msgs { flex: 1; overflow-y: auto; overflow-x: hidden; padding: 16px 14px 10px; display: flex; flex-direction: column; gap: 10px; -webkit-overflow-scrolling: touch; scroll-behavior: smooth; }
.msgs::-webkit-scrollbar { display: none; }
.msg { display: flex; gap: 8px; animation: fadeUp 0.25s ease forwards; opacity: 0; }
@keyframes fadeUp { from { opacity:0; transform: translateY(8px); } to { opacity:1; transform: translateY(0); } }
.msg.user { flex-direction: row-reverse; }
.mav { width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-family: 'IBM Plex Mono', monospace; font-size: 9px; font-weight: 600; flex-shrink: 0; margin-top: 2px; }
.msg.ai .mav { background: linear-gradient(135deg, #3BE854, #7DF78A); color: #04140a; }
.msg.user .mav { background: #16241b; color: #7DF78A; border: 1px solid #2C4030; }
.mc { max-width: 82%; }
.mn { font-family: 'IBM Plex Mono', monospace; font-size: 9px; letter-spacing: 1.5px; color: #466151; margin-bottom: 4px; text-transform: uppercase; }
.msg.user .mn { text-align: right; }
.mb { padding: 10px 14px; border-radius: 16px; font-size: 14.5px; line-height: 1.55; word-break: break-word; }
.msg.ai .mb { background: #0E1712; border: 1px solid #1D3A24; border-top-left-radius: 4px; color: #D8EFDB; }
.msg.user .mb { background: #13201A; border: 1px solid #2C4030; border-top-right-radius: 4px; color: #E8F4EA; }
.mt { font-family: 'IBM Plex Mono', monospace; font-size: 9px; color: #3a5145; margin-top: 4px; }
.msg.user .mt { text-align: right; }

/* TYPING */
.typing { display: flex; gap: 5px; align-items: center; padding: 12px 14px; }
.td { width: 7px; height: 7px; border-radius: 50%; background: #3BE854; animation: bounce 1.2s ease-in-out infinite; }
.td:nth-child(2) { animation-delay: 0.2s; }
.td:nth-child(3) { animation-delay: 0.4s; }
@keyframes bounce { 0%,60%,100% { transform: translateY(0); opacity: 0.3; } 30% { transform: translateY(-6px); opacity: 1; } }

/* INPUT */
.inp-wrap { flex-shrink: 0; background: #060A07; border-top: 1px solid #1D2A21; padding: 10px 12px; padding-bottom: max(10px, env(safe-area-inset-bottom)); }
.inp-row { display: flex; gap: 8px; align-items: flex-end; }
.iw { flex: 1; background: #0E1712; border: 1px solid #1D3A24; border-radius: 22px; padding: 10px 16px; transition: border-color 0.2s, box-shadow 0.2s; min-height: 44px; display: flex; align-items: center; }
.iw:focus-within { border-color: rgba(59,232,84,0.5); box-shadow: 0 0 10px rgba(59,232,84,0.08); }
textarea { background: none; border: none; outline: none; color: #E8F4EA; font-family: 'IBM Plex Sans', -apple-system, sans-serif; font-size: 15px; line-height: 1.4; resize: none; width: 100%; max-height: 120px; min-height: 22px; display: block; }
textarea::placeholder { color: #466151; }
.sb { width: 44px; height: 44px; border-radius: 50%; background: linear-gradient(135deg, #3BE854, #7DF78A); border: none; cursor: pointer; display: flex; align-items: center; justify-content: center; flex-shrink: 0; box-shadow: 0 0 14px rgba(59,232,84,0.35); transition: transform 0.15s, box-shadow 0.2s; }
.sb:active { transform: scale(0.9); }
.sb:disabled { opacity: 0.35; }
.sb svg { width: 18px; height: 18px; fill: #04140a; }
</style>
</head>
<body>

<div class='header'>
  <div class='header-inner'>
    <div class='avatar'><img src='data:image/webp;base64,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' alt='Vibes 3D Studio'></div>
    <div class='head-info'>
      <div class='head-name'>VIBES <b>3D</b> STUDIO</div>
      <div class='head-status' id='status'><div class='dot'></div><span id='statusText'>Online - ask me anything</span></div>
    </div>
  </div>
</div>

<div class='msgs' id='msgContainer'></div>

<div class='inp-wrap'>
  <div class='inp-row'>
    <div class='iw'>
      <textarea id='userInput' placeholder='Ask about prints, pricing...' rows='1'></textarea>
    </div>
    <button class='sb' id='sendBtn'>
      <svg viewBox='0 0 24 24'><path d='M2.01 21L23 12 2.01 3 2 10l15 2-15 2z'/></svg>
    </button>
  </div>
</div>

<script>
var container = document.getElementById('msgContainer');
var inputBox = document.getElementById('userInput');
var sendBtn = document.getElementById('sendBtn');
var statusEl = document.getElementById('status');
var statusText = document.getElementById('statusText');
var busy = false;
var history = [];

function setStatus(text, isTyping) {
  statusText.textContent = text;
  statusEl.className = isTyping ? 'head-status typing' : 'head-status';
}

function getTime() {
  return new Date().toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
}

function addMsg(role, content) {
  var div = document.createElement('div');
  div.className = 'msg ' + role;
  var icon = role === 'ai' ? 'V' : 'YOU';
  var name = role === 'ai' ? 'VIBES' : 'YOU';
  var tmp = document.createElement('div');
  tmp.textContent = content;
  var safe = tmp.innerHTML;
  div.innerHTML = '<div class="mav">' + icon + '</div><div class="mc"><div class="mn">' + name + '</div><div class="mb">' + safe + '</div><div class="mt">' + getTime() + '</div></div>';
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function showTyping() {
  var div = document.createElement('div');
  div.className = 'msg ai';
  div.id = 'typingDiv';
  div.innerHTML = '<div class="mav">V</div><div class="mc"><div class="mn">VIBES</div><div class="mb typing"><div class="td"></div><div class="td"></div><div class="td"></div></div></div>';
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function hideTyping() {
  var t = document.getElementById('typingDiv');
  if (t) t.remove();
}

function send() {
  var text = inputBox.value.trim();
  if (!text || busy) return;
  inputBox.value = '';
  inputBox.style.height = 'auto';
  busy = true;
  sendBtn.disabled = true;
  addMsg('user', text);
  history.push({role: 'user', content: text});
  showTyping();
  setStatus('typing...', true);
  fetch('/chat', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({history: history.slice(-12)})})
  .then(function(r) { return r.json(); })
  .then(function(d) {
    hideTyping();
    if (d.reply) {
      addMsg('ai', d.reply);
      history.push({role: 'assistant', content: d.reply});
    } else {
      addMsg('ai', 'Sorry, something went wrong. Mind trying again?');
    }
    setStatus('Online - ask me anything', false);
    busy = false;
    sendBtn.disabled = false;
    inputBox.focus();
  })
  .catch(function() {
    hideTyping();
    addMsg('ai', 'Connection lost. Try again in a moment.');
    setStatus('Online - ask me anything', false);
    busy = false;
    sendBtn.disabled = false;
  });
}

inputBox.addEventListener('keydown', function(e) {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
});
inputBox.addEventListener('input', function() {
  inputBox.style.height = 'auto';
  inputBox.style.height = Math.min(inputBox.scrollHeight, 120) + 'px';
});
sendBtn.addEventListener('click', send);

setTimeout(function() {
  addMsg('ai', "Hey! I'm the Vibes 3D Studio assistant. I can answer questions about pricing, what we print, and how to order. What can I help with?");
}, 500);
</script>
</body>
</html>"""

@app.route("/")
def index():
    return HTML_PAGE

@app.route("/chat", methods=["POST"])
def chat():
    # Who is asking (best-effort; Railway puts the real IP in X-Forwarded-For)
    ip = (request.headers.get("X-Forwarded-For", request.remote_addr or "?")).split(",")[0].strip()

    # Per-visitor flood protection
    if not _rate_ok(ip):
        return jsonify({"reply": "Whoa, one at a time! Give me a few seconds and try again."})

    # Site-wide daily ceiling - a hard backstop against abuse
    if not _day_ok():
        return jsonify({"reply": "Thanks for all the interest today! The chat is taking a quick "
                                 "break - please email " + CONTACT_INFO + " and we'll get right back to you."})

    data = request.json or {}
    incoming = data.get("history", [])
    messages = []
    for h in incoming:
        role = h.get("role")
        content = (h.get("content") or "").strip()[:MAX_INPUT_CHARS]   # cap message size
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    # keep it light, and make sure it starts with a user turn (Anthropic requires this)
    messages = messages[-12:]
    while messages and messages[0]["role"] != "user":
        messages.pop(0)
    if not messages or messages[-1]["role"] != "user":
        return jsonify({"error": "no message"}), 400
    try:
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        res = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=350,
            system=SYSTEM_PROMPT,
            messages=messages,
        )
        reply = res.content[0].text
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify({"reply": reply})

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
