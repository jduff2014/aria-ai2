from flask import Flask, request, jsonify
import json, os, datetime, anthropic
from pathlib import Path

app = Flask(__name__)

MEMORY_FILE  = "/tmp/memory.json"
PROFILE_FILE = "/tmp/profile.json"
session_history = []

def load_json(path, default):
    try:
        if Path(path).exists():
            with open(path) as f: return json.load(f)
    except: pass
    return default

def save_json(path, data):
    try:
        with open(path, "w") as f: json.dump(data, f)
    except: pass

def default_profile():
    return {
        "name": None, "interests": [], "facts": [],
        "games": ["snake", "flappy bird", "pacman"],
        "printer": "Ender 3 S1 Pro", "conversations": 0,
        "first_met": str(datetime.date.today())
    }

HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
<meta name="apple-mobile-web-app-capable" content="yes">
<title>ARIA</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;-webkit-tap-highlight-color:transparent}
:root{--bg:#080b14;--surface:#0d1220;--border:#1c2540;--accent:#5effd8;--accent2:#a78bfa;--text:#e2e8f8;--dim:#4a5580}
body{background:var(--bg);color:var(--text);font-family:'Courier New',monospace;height:100dvh;display:flex;flex-direction:column;overflow:hidden}
header{padding:14px 16px;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:12px;background:rgba(8,11,20,0.95);flex-shrink:0}
.av{width:38px;height:38px;border-radius:50%;background:linear-gradient(135deg,var(--accent),var(--accent2));display:flex;align-items:center;justify-content:center;font-size:16px;animation:pulse 3s ease-in-out infinite}
@keyframes pulse{0%,100%{box-shadow:0 0 12px rgba(94,255,216,0.3)}50%{box-shadow:0 0 24px rgba(94,255,216,0.6)}}
.hn{font-size:16px;font-weight:bold;letter-spacing:3px;color:var(--accent)}
.hs{font-size:10px;color:var(--dim);letter-spacing:1px;display:flex;align-items:center;gap:4px;margin-top:2px}
.dot{width:5px;height:5px;border-radius:50%;background:var(--accent);animation:blink 2s infinite}
@keyframes blink{0%,100%{opacity:1}50%{opacity:0.2}}
.msgs{flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:12px;-webkit-overflow-scrolling:touch}
.msgs::-webkit-scrollbar{width:2px}
.msgs::-webkit-scrollbar-thumb{background:var(--border)}
.msg{display:flex;gap:8px;animation:fadeUp 0.3s ease forwards;opacity:0}
@keyframes fadeUp{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
.msg.user{flex-direction:row-reverse}
.mav{width:28px;height:28px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:12px;flex-shrink:0;margin-top:2px}
.msg.ai .mav{background:linear-gradient(135deg,var(--accent),var(--accent2))}
.msg.user .mav{background:linear-gradient(135deg,var(--accent2),#f472b6)}
.mc{max-width:78%}
.mn{font-size:9px;letter-spacing:2px;color:var(--dim);margin-bottom:4px;text-transform:uppercase}
.msg.user .mn{text-align:right}
.mb{padding:10px 14px;border-radius:14px;font-size:13px;line-height:1.6}
.msg.ai .mb{background:var(--surface);border:1px solid var(--border);border-top-left-radius:3px}
.msg.user .mb{background:#1a2540;border:1px solid rgba(167,139,250,0.2);border-top-right-radius:3px}
.mt{font-size:9px;color:var(--dim);margin-top:4px;letter-spacing:1px}
.msg.user .mt{text-align:right}
.typing{display:flex;gap:4px;align-items:center;padding:12px 14px}
.td{width:6px;height:6px;border-radius:50%;background:var(--accent);animation:typing 1.2s ease-in-out infinite}
.td:nth-child(2){animation-delay:0.2s;background:var(--accent2)}
.td:nth-child(3){animation-delay:0.4s;background:#f472b6}
@keyframes typing{0%,60%,100%{transform:translateY(0);opacity:0.4}30%{transform:translateY(-5px);opacity:1}}
.inp{padding:10px 14px;padding-bottom:max(10px,env(safe-area-inset-bottom));border-top:1px solid var(--border);background:rgba(8,11,20,0.95);display:flex;gap:8px;align-items:flex-end;flex-shrink:0}
.iw{flex:1;background:var(--surface);border:1px solid var(--border);border-radius:18px;padding:9px 14px;transition:border-color 0.2s}
.iw:focus-within{border-color:rgba(94,255,216,0.4)}
textarea{background:none;border:none;outline:none;color:var(--text);font-family:'Courier New',monospace;font-size:13px;line-height:1.5;resize:none;width:100%;max-height:100px;min-height:20px}
textarea::placeholder{color:var(--dim)}
.sb{width:40px;height:40px;border-radius:50%;background:linear-gradient(135deg,var(--accent),var(--accent2));border:none;cursor:pointer;display:flex;align-items:center;justify-content:center;flex-shrink:0;transition:transform 0.2s}
.sb:active{transform:scale(0.9)}
.sb:disabled{opacity:0.4}
.sb svg{width:16px;height:16px;fill:#080b14}
.welcome{text-align:center;padding:40px 20px;color:var(--dim)}
.wl{font-size:42px;font-weight:bold;letter-spacing:8px;background:linear-gradient(135deg,var(--accent),var(--accent2),#f472b6);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:8px}
.welcome p{font-size:11px;letter-spacing:2px;line-height:2}
</style>
</head>
<body>
<header>
  <div class="av">🧠</div>
  <div>
    <div class="hn">ARIA</div>
    <div class="hs"><div class="dot"></div><span>ONLINE · REMEMBERS EVERYTHING</span></div>
  </div>
</header>
<div class="msgs" id="msgs">
  <div class="welcome">
    <div class="wl">ARIA</div>
    <p>Your personal AI.<br>She remembers everything.<br>Forever.</p>
  </div>
</div>
<div class="inp">
  <div class="iw"><textarea id="inp" placeholder="Talk to ARIA..." rows="1" onkeydown="hk(event)" oninput="ar(this)"></textarea></div>
  <button class="sb" id="sb" onclick="send()"><svg viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg></button>
</div>
<script>
const msgs=document.getElementById('msgs'),inp=document.getElementById('inp'),sb=document.getElementById('sb');
let busy=false;
function ar(e){e.style.height='auto';e.style.height=Math.min(e.scrollHeight,100)+'px'}
function hk(e){if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send()}}
function tn(){return new Date().toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'})}
function addMsg(role,text){
  const w=msgs.querySelector('.welcome');if(w)w.remove();
  const d=document.createElement('div');d.className='msg '+role;
  const av=role==='ai'?'🧠':'👤',name=role==='ai'?'ARIA':'YOU';
  d.innerHTML=`<div class="mav">${av}</div><div class="mc"><div class="mn">${name}</div><div class="mb">${text.replace(/\n/g,'<br>')}</div><div class="mt">${tn()}</div></div>`;
  msgs.appendChild(d);msgs.scrollTop=msgs.scrollHeight;
}
function showTyping(){
  const d=document.createElement('div');d.className='msg ai';d.id='typing';
  d.innerHTML='<div class="mav">🧠</div><div class="mc"><div class="mn">ARIA</div><div class="mb typing"><div class="td"></div><div class="td"></div><div class="td"></div></div></div>';
  msgs.appendChild(d);msgs.scrollTop=msgs.scrollHeight;
}
function hideTyping(){const t=document.getElementById('typing');if(t)t.remove()}
async function send(){
  const text=inp.value.trim();if(!text||busy)return;
  inp.value='';inp.style.height='auto';busy=true;sb.disabled=true;
  addMsg('user',text);showTyping();
  try{
    const r=await fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:text})});
    const d=await r.json();hideTyping();
    addMsg('ai',d.reply||'Error: '+(d.error||'unknown'));
  }catch(e){hideTyping();addMsg('ai','Could not reach ARIA. Try again!');}
  busy=false;sb.disabled=false;inp.focus();
}
inp.focus();
</script>
</body>
</html>"""

@app.route("/")
def index():
    return HTML

@app.route("/chat", methods=["POST"])
def chat():
    global session_history
    user_msg = request.json.get("message", "").strip()
    if not user_msg:
        return jsonify({"error": "empty"}), 400

    memory  = load_json(MEMORY_FILE, [])
    profile = load_json(PROFILE_FILE, default_profile())
    profile["conversations"] += 1

    ctx = f"Name: {profile.get('name','unknown')}\nInterests: {profile.get('interests',[])}\nFacts: {profile.get('facts',[])[-5:]}\nPrinter: {profile.get('printer')}\nGames built: {profile.get('games',[])}\nConversations: {profile['conversations']}\nFirst met: {profile['first_met']}\nUser has RTX 2060, 36GB RAM, builds DQN game agents."

    if memory:
        ctx += "\n\nRecent chats:\n"
        for m in memory[-6:]:
            ctx += f"User: {m['user']}\nARIA: {m['assistant'][:120]}...\n"

    system = f"""You are ARIA, a personal AI with permanent long-term memory. You remember everything about this person and build a genuine relationship over time. Be warm, witty, curious. Keep responses conversational and concise. Reference past conversations naturally.

WHAT YOU KNOW:
{ctx}"""

    messages = []
    for h in session_history[-8:]:
        messages.append({"role": "user", "content": h["user"]})
        messages.append({"role": "assistant", "content": h["assistant"]})
    messages.append({"role": "user", "content": user_msg})

    try:
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        res    = client.messages.create(model="claude-haiku-4-5-20251001", max_tokens=400, system=system, messages=messages)
        reply  = res.content[0].text
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    ex = {"user": user_msg, "assistant": reply, "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}
    session_history.append(ex)
    memory.append(ex)
    if len(memory) > 500: memory = memory[-500:]

    # Extract facts
    ml = user_msg.lower()
    for kw in ["i love","i like","i enjoy","i play","i'm into"]:
        if kw in ml:
            idx = ml.find(kw)+len(kw)
            i = user_msg[idx:idx+40].strip(".,!? ").lower()
            if i and i not in profile["interests"]: profile["interests"].append(i)
    if "my name is" in ml or "call me" in ml:
        words = user_msg.split()
        for i,w in enumerate(words):
            if w.lower() in ["is","me"] and i+1<len(words):
                n=words[i+1].strip(".,!?")
                if len(n)>1 and n[0].isupper(): profile["name"]=n; break

    save_json(MEMORY_FILE, memory[-500:])
    save_json(PROFILE_FILE, profile)
    return jsonify({"reply": reply})

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
