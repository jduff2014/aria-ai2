# 🧠 ARIA — Personal AI Setup Guide

## What you're building
ARIA is your personal AI that:
- Remembers every conversation forever
- Runs on your home PC
- Accessible from your iPhone anywhere via ngrok
- Gets smarter and more personal over time

---

## Step 1 — Install packages

```
pip install flask anthropic colorama
```

---

## Step 2 — Get an Anthropic API Key

1. Go to: https://console.anthropic.com
2. Sign up for a free account
3. Go to "API Keys" → Create a new key
4. Copy your key (starts with sk-ant-...)

Set it in PowerShell:
```
$env:ANTHROPIC_API_KEY="sk-ant-your-key-here"
```

---

## Step 3 — Install ngrok (lets iPhone connect)

1. Go to: https://ngrok.com
2. Sign up for a free account
3. Download ngrok for Windows
4. Extract it to your project folder
5. Connect your account:
```
ngrok config add-authtoken YOUR_NGROK_TOKEN
```
(Find your token at: https://dashboard.ngrok.com)

---

## Step 4 — Run ARIA

Open TWO PowerShell windows:

**Window 1 — Start ARIA server:**
```
$env:ANTHROPIC_API_KEY="your-key-here"
python aria_server.py
```

**Window 2 — Start ngrok tunnel:**
```
ngrok http 5000
```

ngrok will show you a URL like:
```
Forwarding  https://abc123.ngrok-free.app -> http://localhost:5000
```

---

## Step 5 — Open on iPhone

1. Copy the ngrok URL (https://abc123.ngrok-free.app)
2. Open Safari on your iPhone
3. Paste the URL and go
4. ARIA chat opens!

**Pro tip:** Add to Home Screen!
- Tap the Share button in Safari
- Tap "Add to Home Screen"
- Now ARIA is on your home screen like an app 📱

---

## How ARIA remembers

Everything is saved in two files on your PC:
- `ai_memory.json` — every conversation ever
- `ai_profile.json` — what she's learned about you

These are permanent — even if you restart the server, she remembers everything.

---

## File structure
```
📁 Your folder
├── aria_server.py      ← main server
├── ai_memory.json      ← created automatically
├── ai_profile.json     ← created automatically
└── aria_web/
    └── index.html      ← iPhone chat UI
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `ANTHROPIC_API_KEY not set` | Set the env variable in PowerShell |
| iPhone can't connect | Make sure ngrok is running in second window |
| ngrok URL expired | Free ngrok URLs change each restart — copy new one |
| `flask not found` | Run `pip install flask` |
| Memory not saving | Make sure script has write permission in folder |

---

## Make ngrok URL permanent (optional)

Free ngrok gives a random URL each time. To get a fixed URL:
- Upgrade to ngrok free plan (still free, just needs account)
- Or use a custom domain

---

## Future upgrades we can add
- Voice input/output 🎤
- Connect to your game agents 🎮
- Connect to 3D printer 🖨️
- Camera/vision 👁️
- Robot body 🤖
