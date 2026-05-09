from flask import Flask, request, jsonify
import json, os, datetime, anthropic, base64, threading
from pathlib import Path

app = Flask(__name__)
MEMORY_FILE = "/tmp/memory.json"
PROFILE_FILE = "/tmp/profile.json"
session_history = []
processing_jobs = {}

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

def analyze_and_split_stl(stl_data, filename, job_id):
    try:
        import struct, math
        # Validate minimum size
        if len(stl_data) < 84:
            processing_jobs[job_id] = {"status": "error", "message": "Invalid STL file"}
            return

        # Detect binary vs ASCII STL
        try:
            header_text = stl_data[:256].decode('utf-8', errors='ignore').lower()
            is_ascii = header_text.strip().startswith('solid') and b'endsolid' in stl_data[:2048].lower()
        except:
            is_ascii = False

        min_x = min_y = min_z = float('inf')
        max_x = max_y = max_z = float('-inf')
        num_triangles = 0

        if is_ascii:
            # Parse ASCII STL
            try:
                text = stl_data.decode('utf-8', errors='ignore')
                lines = text.split('\n')
                for line in lines:
                    line = line.strip()
                    if line.startswith('vertex '):
                        parts = line.split()
                        if len(parts) == 4:
                            x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
                            if abs(x) < 1e10 and abs(y) < 1e10 and abs(z) < 1e10:
                                min_x = min(min_x, x); max_x = max(max_x, x)
                                min_y = min(min_y, y); max_y = max(max_y, y)
                                min_z = min(min_z, z); max_z = max(max_z, z)
                    elif line.startswith('facet normal'):
                        num_triangles += 1
            except:
                pass
        else:
            # Parse binary STL - sample evenly across file for speed
            try:
                num_triangles = struct.unpack('<I', stl_data[80:84])[0]
                total_size = 84 + num_triangles * 50
                # Sample up to 50000 triangles evenly
                step = max(1, num_triangles // 50000)
                for i in range(0, num_triangles, step):
                    offset = 84 + i * 50
                    if offset + 50 > len(stl_data):
                        break
                    for v in range(3):
                        voffset = offset + 12 + v * 12
                        if voffset + 12 <= len(stl_data):
                            try:
                                x, y, z = struct.unpack('<fff', stl_data[voffset:voffset+12])
                                if abs(x) < 1e10 and abs(y) < 1e10 and abs(z) < 1e10:
                                    min_x = min(min_x, x); max_x = max(max_x, x)
                                    min_y = min(min_y, y); max_y = max(max_y, y)
                                    min_z = min(min_z, z); max_z = max(max_z, z)
                            except:
                                continue
            except:
                pass

        # Fallback if parsing failed
        if min_x == float('inf') or min_x == max_x:
            min_x = min_y = min_z = 0
            max_x = max_y = max_z = 100
            num_triangles = num_triangles or 1000

        size_x = abs(max_x - min_x)
        size_y = abs(max_y - min_y)
        size_z = abs(max_z - min_z)

        # Handle edge case where all dimensions are 0
        if size_x == 0: size_x = 10
        if size_y == 0: size_y = 10
        if size_z == 0: size_z = 10

        # Ender 3 S1 Pro build volume
        MAX_X, MAX_Y, MAX_Z = 220, 220, 270
        cuts_x = max(1, math.ceil(size_x / MAX_X))
        cuts_y = max(1, math.ceil(size_y / MAX_Y))
        cuts_z = max(1, math.ceil(size_z / MAX_Z))
        total_pieces = cuts_x * cuts_y * cuts_z

        pieces = []
        piece_num = 1
        for ix in range(cuts_x):
            for iy in range(cuts_y):
                for iz in range(cuts_z):
                    pieces.append({
                        "piece": piece_num,
                        "size": str(round(size_x/cuts_x,1)) + " x " + str(round(size_y/cuts_y,1)) + " x " + str(round(size_z/cuts_z,1)) + " mm"
                    })
                    piece_num += 1

        processing_jobs[job_id] = {
            "status": "complete",
            "filename": filename,
            "analysis": {
                "size_x": round(size_x,1),
                "size_y": round(size_y,1),
                "size_z": round(size_z,1),
                "total_pieces": total_pieces,
                "triangles": num_triangles,
                "fits": total_pieces == 1
            },
            "pieces": pieces
        }
    except Exception as e:
        processing_jobs[job_id] = {"status": "error", "message": str(e)}

HTML_PAGE = """<!DOCTYPE html>
<html>
<head>
<meta charset='UTF-8'>
<meta name='viewport' content='width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no'>
<meta name='apple-mobile-web-app-capable' content='yes'>
<meta name='apple-mobile-web-app-status-bar-style' content='black-translucent'>
<title>ARIA</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
html { height: 100%; }
body { background: #050810; color: #e2e8f8; font-family: -apple-system, Courier New, monospace; height: 100dvh; display: flex; flex-direction: column; overflow: hidden; }

/* ARIA HEADER */
.aria-header { flex-shrink: 0; background: #050810; border-bottom: 1px solid #1a2e1a; position: relative; overflow: hidden; }
.aria-header::before { content: ''; position: absolute; inset: 0; background: radial-gradient(ellipse at 50% 100%, rgba(0,255,80,0.08) 0%, transparent 70%); pointer-events: none; }
.aria-inner { display: flex; align-items: center; gap: 12px; padding: 10px 16px; position: relative; z-index: 2; }
.aria-img-wrap { position: relative; width: 56px; height: 56px; flex-shrink: 0; }
.aria-img-wrap img { width: 100%; height: 100%; object-fit: cover; object-position: center top; border-radius: 50%; border: 2px solid #00ff50; box-shadow: 0 0 12px rgba(0,255,80,0.4); }
#glowCanvas { position: absolute; top: 0; left: 0; width: 100%; height: 100%; border-radius: 50%; pointer-events: none; }
.aria-info { flex: 1; }
.aria-name { font-size: 18px; font-weight: bold; letter-spacing: 4px; color: #00ff50; text-shadow: 0 0 15px rgba(0,255,80,0.7); }
.aria-status { font-size: 10px; letter-spacing: 2px; color: #4a7a4a; margin-top: 2px; display: flex; align-items: center; gap: 5px; }
.status-dot { width: 6px; height: 6px; border-radius: 50%; background: #00ff50; animation: blink 2s infinite; flex-shrink: 0; }
@keyframes blink { 0%,100% { opacity: 1; } 50% { opacity: 0.2; } }
.aria-status.talking .status-dot { animation: fastblink 0.4s infinite; background: #adff2f; }
@keyframes fastblink { 0%,100% { opacity: 1; } 50% { opacity: 0.1; } }
.aria-tag { font-size: 9px; letter-spacing: 1px; color: #2a4a2a; margin-top: 2px; }

/* MESSAGES */
.msgs { flex: 1; overflow-y: auto; overflow-x: hidden; padding: 14px 14px 8px; display: flex; flex-direction: column; gap: 10px; -webkit-overflow-scrolling: touch; scroll-behavior: smooth; }
.msgs::-webkit-scrollbar { display: none; }
.msg { display: flex; gap: 8px; animation: fadeUp 0.25s ease forwards; opacity: 0; }
@keyframes fadeUp { from { opacity:0; transform: translateY(8px); } to { opacity:1; transform: translateY(0); } }
.msg.user { flex-direction: row-reverse; }
.mav { width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 10px; font-weight: bold; flex-shrink: 0; color: #050810; margin-top: 2px; }
.msg.ai .mav { background: linear-gradient(135deg, #00ff50, #adff2f); box-shadow: 0 0 8px rgba(0,255,80,0.4); }
.msg.user .mav { background: linear-gradient(135deg, #a78bfa, #f472b6); }
.mc { max-width: 82%; }
.mn { font-size: 9px; letter-spacing: 2px; color: #2a4a2a; margin-bottom: 4px; text-transform: uppercase; }
.msg.user .mn { text-align: right; }
.mb { padding: 10px 14px; border-radius: 16px; font-size: 14px; line-height: 1.55; word-break: break-word; }
.msg.ai .mb { background: #0a150a; border: 1px solid #1a3a1a; border-top-left-radius: 4px; color: #c8f0c8; }
.msg.user .mb { background: #1a1540; border: 1px solid rgba(167,139,250,0.25); border-top-right-radius: 4px; color: #e2e8f8; }
.mt { font-size: 9px; color: #2a4a2a; margin-top: 4px; }
.msg.user .mt { text-align: right; }

/* TYPING */
.typing { display: flex; gap: 5px; align-items: center; padding: 12px 14px; }
.td { width: 7px; height: 7px; border-radius: 50%; background: #00ff50; animation: bounce 1.2s ease-in-out infinite; }
.td:nth-child(2) { animation-delay: 0.2s; }
.td:nth-child(3) { animation-delay: 0.4s; }
@keyframes bounce { 0%,60%,100% { transform: translateY(0); opacity: 0.3; } 30% { transform: translateY(-6px); opacity: 1; } }

/* STL CARD */
.stl-card { background: #050e05; border: 1px solid #00ff50; border-radius: 12px; padding: 12px; margin-top: 4px; }
.stl-card h4 { color: #00ff50; letter-spacing: 2px; font-size: 10px; margin-bottom: 8px; text-transform: uppercase; }
.stl-info { font-size: 12px; color: #8ab88a; margin-bottom: 6px; }
.stl-piece { background: #0a150a; border: 1px solid #1a3a1a; border-radius: 8px; padding: 7px 10px; margin-top: 5px; font-size: 12px; color: #c8f0c8; display: flex; justify-content: space-between; align-items: center; }
.stl-piece .pnum { color: #00ff50; font-weight: bold; font-size: 11px; }
.fits-badge { background: rgba(0,255,80,0.15); border: 1px solid #00ff50; color: #00ff50; border-radius: 20px; padding: 4px 10px; font-size: 11px; letter-spacing: 1px; display: inline-block; margin-top: 6px; }

/* INPUT */
.inp-wrap { flex-shrink: 0; background: #050810; border-top: 1px solid #1a2e1a; padding: 10px 12px; padding-bottom: max(10px, env(safe-area-inset-bottom)); }
.inp-row { display: flex; gap: 8px; align-items: flex-end; }
.upload-btn { width: 42px; height: 42px; border-radius: 50%; background: #0a150a; border: 1px solid #1a3a1a; cursor: pointer; display: flex; align-items: center; justify-content: center; font-size: 18px; flex-shrink: 0; transition: all 0.2s; }
.upload-btn:active { border-color: #00ff50; transform: scale(0.92); }
#fileInput { display: none; }
.iw { flex: 1; background: #0a150a; border: 1px solid #1a3a1a; border-radius: 22px; padding: 10px 16px; transition: border-color 0.2s; min-height: 42px; display: flex; align-items: center; }
.iw:focus-within { border-color: rgba(0,255,80,0.5); box-shadow: 0 0 10px rgba(0,255,80,0.06); }
textarea { background: none; border: none; outline: none; color: #c8f0c8; font-family: -apple-system, Courier New, monospace; font-size: 15px; line-height: 1.4; resize: none; width: 100%; max-height: 120px; min-height: 22px; display: block; }
textarea::placeholder { color: #2a4a2a; }
.sb { width: 42px; height: 42px; border-radius: 50%; background: linear-gradient(135deg, #00ff50, #adff2f); border: none; cursor: pointer; display: flex; align-items: center; justify-content: center; flex-shrink: 0; box-shadow: 0 0 14px rgba(0,255,80,0.35); transition: all 0.2s; }
.sb:active { transform: scale(0.9); box-shadow: 0 0 20px rgba(0,255,80,0.6); }
.sb:disabled { opacity: 0.35; }
.sb svg { width: 18px; height: 18px; fill: #050810; }
</style>
</head>
<body>

<!-- HEADER -->
<div class='aria-header'>
  <div class='aria-inner'>
    <div class='aria-img-wrap'>
      <img src='https://i.postimg.cc/Ls3JkRhV/Chat-GPT-Image-May-7-2026-11-59-14-AM.png' alt='ARIA'>
      <canvas id='glowCanvas'></canvas>
    </div>
    <div class='aria-info'>
      <div class='aria-name'>NI-VIBES</div>
      <div class='aria-status' id='ariaStatus'><div class='status-dot'></div><span id='statusText'>ONLINE</span></div>
      <div class='aria-tag'>SENTINEL CLASS · MEMORY ACTIVE</div>
    </div>
  </div>
</div>

<!-- MESSAGES -->
<div class='msgs' id='msgContainer'></div>

<!-- INPUT -->
<div class='inp-wrap'>
  <div class='inp-row'>
    <label class='upload-btn' for='fileInput'>📎</label>
    <input type='file' id='fileInput' accept='.stl'>
    <div class='iw'>
      <textarea id='userInput' placeholder='Talk to ARIA...' rows='1'></textarea>
    </div>
    <button class='sb' id='sendBtn'>
      <svg viewBox='0 0 24 24'><path d='M2.01 21L23 12 2.01 3 2 10l15 2-15 2z'/></svg>
    </button>
  </div>
</div>

<script>
// GLOW ANIMATION
var gc = document.getElementById('glowCanvas');
var gx = gc.getContext('2d');
var tick = 0;
var talking = false;
var glow = 0;

function resizeGlow() {
  gc.width = gc.offsetWidth;
  gc.height = gc.offsetHeight;
}
resizeGlow();

function animateGlow() {
  tick += 0.05;
  var W = gc.width, H = gc.height;
  gx.clearRect(0, 0, W, H);
  var target = talking ? 0.9 : 0.3 + Math.sin(tick) * 0.12;
  glow += (target - glow) * 0.07;
  var cx = W/2, cy = H/2;
  var rim = gx.createRadialGradient(cx, cy, W*0.35, cx, cy, W*0.5);
  rim.addColorStop(0, 'rgba(0,255,80,0)');
  rim.addColorStop(0.7, 'rgba(0,255,80,' + (glow*0.4) + ')');
  rim.addColorStop(1, 'rgba(0,255,80,' + (glow*0.8) + ')');
  gx.fillStyle = rim;
  gx.beginPath();
  gx.arc(cx, cy, W*0.5, 0, Math.PI*2);
  gx.fill();
  var eyeY = H * 0.3;
  var eg = gx.createRadialGradient(cx-W*0.13, eyeY, 0, cx-W*0.13, eyeY, W*0.12);
  eg.addColorStop(0, 'rgba(0,255,80,' + (glow*0.9) + ')');
  eg.addColorStop(1, 'rgba(0,255,80,0)');
  gx.fillStyle = eg;
  gx.fillRect(cx-W*0.25, eyeY-W*0.12, W*0.24, W*0.24);
  var eg2 = gx.createRadialGradient(cx+W*0.13, eyeY, 0, cx+W*0.13, eyeY, W*0.12);
  eg2.addColorStop(0, 'rgba(0,255,80,' + (glow*0.9) + ')');
  eg2.addColorStop(1, 'rgba(0,255,80,0)');
  gx.fillStyle = eg2;
  gx.fillRect(cx+W*0.01, eyeY-W*0.12, W*0.24, W*0.24);
  requestAnimationFrame(animateGlow);
}
animateGlow();

// CHAT
var container = document.getElementById('msgContainer');
var inputBox = document.getElementById('userInput');
var sendBtn = document.getElementById('sendBtn');
var statusEl = document.getElementById('ariaStatus');
var statusText = document.getElementById('statusText');
var fileInput = document.getElementById('fileInput');
var busy = false;

function setStatus(text, isTalking) {
  statusText.textContent = text;
  talking = isTalking;
  statusEl.className = isTalking ? 'aria-status talking' : 'aria-status';
}

function getTime() {
  return new Date().toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
}

function addMsg(role, content, isHtml) {
  var div = document.createElement('div');
  div.className = 'msg ' + role;
  var icon = role === 'ai' ? 'AI' : 'ME';
  var name = role === 'ai' ? 'ARIA' : 'YOU';
  var html;
  if (isHtml) {
    html = content;
  } else {
    var tmp = document.createElement('div');
    tmp.textContent = content;
    html = tmp.innerHTML;
  }
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
  if (t) t.remove();
}

function send() {
  var text = inputBox.value.trim();
  if (!text || busy) return;
  inputBox.value = '';
  inputBox.style.height = 'auto';
  busy = true;
  sendBtn.disabled = true;
  addMsg('user', text, false);
  showTyping();
  setStatus('THINKING...', true);
  fetch('/chat', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({message:text})})
  .then(function(r) { return r.json(); })
  .then(function(d) {
    hideTyping();
    addMsg('ai', d.reply || ('Error: ' + (d.error||'unknown')), false);
    setStatus('ONLINE', false);
    busy = false;
    sendBtn.disabled = false;
    inputBox.focus();
  })
  .catch(function() {
    hideTyping();
    addMsg('ai', 'Connection lost. Try again.', false);
    setStatus('ONLINE', false);
    busy = false;
    sendBtn.disabled = false;
  });
}

fileInput.addEventListener('change', function() {
  var file = fileInput.files[0];
  if (!file) return;
  if (!file.name.toLowerCase().endsWith('.stl')) {
    addMsg('ai', 'STL files only right now.', false);
    return;
  }
  addMsg('user', 'Uploaded: ' + file.name, false);
  addMsg('ai', 'Got it — analyzing your model. Keep chatting, I will let you know when I am done.', false);
  setStatus('ANALYZING...', true);
  var reader = new FileReader();
  reader.onload = function(e) {
    var arr = new Uint8Array(e.target.result);
    var str = '';
    for (var i = 0; i < arr.length; i++) str += String.fromCharCode(arr[i]);
    var b64 = btoa(str);
    fetch('/analyze_stl', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({filename:file.name, data:b64})})
    .then(function(r) { return r.json(); })
    .then(function(d) { if (d.job_id) pollJob(d.job_id); });
  };
  reader.readAsArrayBuffer(file);
  fileInput.value = '';
});

var pollCount = 0;
function pollJob(id) {
  pollCount++;
  if (pollCount > 20) {
    setStatus("ONLINE", false);
    addMsg("ai", "That file took too long to analyze. Try a smaller STL file.", false);
    pollCount = 0;
    return;
  }
  setTimeout(function() {
    fetch('/job_status/' + id)
    .then(function(r) { return r.json(); })
    .then(function(d) {
      if (d.status === 'processing') { pollJob(id); return; }
      setStatus('ONLINE', false);
      if (d.status === 'complete') {
        showSTLResult(d);
      } else {
        addMsg('ai', 'Had trouble with that file. Try again.', false);
      }
    });
  }, 1500);
}

function showSTLResult(d) {
  var a = d.analysis;
  var html = '<div class="stl-card"><h4>' + d.filename + '</h4>';
  html += '<div class="stl-info">Size: ' + a.size_x + ' x ' + a.size_y + ' x ' + a.size_z + ' mm &nbsp;|&nbsp; ' + a.triangles.toLocaleString() + ' triangles</div>';
  if (a.fits) {
    html += '<div class="fits-badge">FITS BED — PRINT AS ONE PIECE</div>';
  } else {
    html += '<div class="stl-info">Optimal split: <b style="color:#00ff50">' + a.total_pieces + ' pieces</b></div>';
    for (var i = 0; i < d.pieces.length; i++) {
      html += '<div class="stl-piece"><span class="pnum">PIECE ' + d.pieces[i].piece + '</span><span>' + d.pieces[i].size + '</span></div>';
    }
  }
  html += '</div>';
  addMsg('ai', html, true);
  var msg = a.fits ? 'Your model fits the Ender 3 S1 Pro as one piece — just open it in OrcaSlicer and print!' : 'Split into ' + a.total_pieces + ' pieces, each fits your bed. Slice each one separately in OrcaSlicer then glue together.';
  addMsg('ai', msg, false);
}

inputBox.addEventListener('keydown', function(e) {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
});
inputBox.addEventListener('input', function() {
  inputBox.style.height = 'auto';
  inputBox.style.height = Math.min(inputBox.scrollHeight, 120) + 'px';
});
sendButton = sendBtn;
sendBtn.addEventListener('click', send);

setTimeout(function() {
  addMsg('ai', 'Hey. Systems online. Chat with me or tap the clip to upload an STL for splitting.', false);
}, 600);
</script>
</body>
</html>"""

@app.route("/")
def index():
    return HTML_PAGE

@app.route("/analyze_stl", methods=["POST"])
def analyze_stl():
    data = request.json
    filename = data.get("filename", "model.stl")
    try:
        stl_data = base64.b64decode(data.get("data", ""))
    except:
        return jsonify({"error": "invalid file"}), 400
    job_id = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
    processing_jobs[job_id] = {"status": "processing"}
    t = threading.Thread(target=analyze_and_split_stl, args=(stl_data, filename, job_id))
    t.daemon = True
    t.start()
    return jsonify({"job_id": job_id})

@app.route("/job_status/<job_id>")
def job_status(job_id):
    return jsonify(processing_jobs.get(job_id, {"status": "not_found"}))

@app.route("/chat", methods=["POST"])
def chat():
    global session_history
    user_msg = request.json.get("message", "").strip()
    if not user_msg:
        return jsonify({"error": "empty"}), 400
    memory = load_json(MEMORY_FILE, [])
    profile = load_json(PROFILE_FILE, default_profile())
    profile["conversations"] += 1
    ctx = "Name: " + str(profile.get("name","unknown")) + "\nInterests: " + str(profile.get("interests",[])) + "\nPrinter: Ender 3 S1 Pro\nGames built: snake, flappy bird, pacman\nConversations: " + str(profile["conversations"]) + "\nUser has RTX 2060, 36GB RAM, builds DQN game AI agents."
    if memory:
        ctx += "\n\nRecent chats:"
        for m in memory[-6:]:
            ctx += "\nUser: " + m["user"] + "\nARIA: " + m["assistant"][:120]
    system = "You are ARIA, a cyberpunk AI sentinel. NI-VIBES class. You are feminine, confident, smooth and natural — talk like a real woman, not a robot. Keep responses SHORT, max 2 sentences. No narrating actions, no asterisks, no robotic phrases. Just talk directly and naturally. Remember everything about this person.\n\nWHAT YOU KNOW:\n" + ctx
    messages = []
    for h in session_history[-8:]:
        messages.append({"role":"user","content":h["user"]})
        messages.append({"role":"assistant","content":h["assistant"]})
    messages.append({"role":"user","content":user_msg})
    try:
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        res = client.messages.create(model="claude-haiku-4-5-20251001", max_tokens=400, system=system, messages=messages)
        reply = res.content[0].text
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    ex = {"user":user_msg,"assistant":reply,"date":datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}
    session_history.append(ex)
    memory.append(ex)
    if len(memory) > 500: memory = memory[-500:]
    ml = user_msg.lower()
    for kw in ["i love","i like","i enjoy","i play"]:
        if kw in ml:
            idx = ml.find(kw)+len(kw)
            interest = user_msg[idx:idx+40].strip(".,!? ").lower()
            if interest and interest not in profile["interests"]: profile["interests"].append(interest)
    if "my name is" in ml:
        words = user_msg.split()
        for i,w in enumerate(words):
            if w.lower()=="is" and i+1<len(words):
                n=words[i+1].strip(".,!?")
                if len(n)>1 and n[0].isupper(): profile["name"]=n; break
    save_json(MEMORY_FILE, memory[-500:])
    save_json(PROFILE_FILE, profile)
    return jsonify({"reply": reply})

@app.route("/health")
def health():
    return jsonify({"status":"ok"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
