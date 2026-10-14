# 🏔️ Safar Guide — AI Voice Travel Agent (FYP Module 1)

A **100% free** voice guide for Pakistan's Northern Areas. Talk to it in Urdu or
English; it answers from a curated knowledge base (`knowledge_base.md`).

## 🌐 Site ko internet pe LIVE karo (2 tareeqe)

**Tareeqa 1 — Instant link (2 minute, koi account nahi):**
```bash
cd voice-agent
SAFAR_LLM_PROVIDER=pollinations .venv/bin/uvicorn server:app --host 0.0.0.0 --port 8000
# doosri terminal mein:
~/workspace/bin/cloudflared tunnel --url http://localhost:8000
# (Windows pe: cloudflared.exe cloudflare.com se download karo)
```
Jo `https://....trycloudflare.com` link mile wo public hai — phone se kholo,
mic dabao, Safar Guide se baat karo. Jab tak tunnel chalta hai, link live hai.

**Tareeqa 2 — Permanent link (Render, free):**
1. Is `voice-agent` folder ko GitHub repo banao (push karo).
2. render.com pe free signup → New → Blueprint → repo ka URL paste karo.
3. `render.yaml` sab kuch khud set kar lega. Behtar jawabon ke liye baad mein
   `GEMINI_API_KEY` env var add kar dena (optional).

Dono tareeqon mein site **bina kisi API key** ke chalti hai (free LLM provider).

## Free stack (no paid service anywhere)

| Piece | What we use | Cost |
|---|---|---|
| Ears (speech → text) | Browser Web Speech API (built into Chrome/Edge) | Free |
| Brain (answers) | Google Gemini free tier (or Pollinations, free, no key) | Free |
| Voice (text → speech) | Microsoft Edge TTS (`ur-PK` / `en-US` voices) | Free, no key |
| Server | FastAPI on your own laptop | Free |

> A real Pakistani **phone number** (+92) cannot be free — PTA-regulated DIDs
> start ~$36/month. For the FYP demo this web version does the same job: the
> jury talks to the agent live. A Twilio **trial** account also gives a free US
> number + $15 credit if you want a real phone-call demo (optional, see below).

## Setup (5 minutes)

1. **Get a free Gemini key** (optional, behtar jawabon ke liye) — go to
   https://aistudio.google.com → "Get API key" → create one (no credit card
   needed). Key ke baghair bhi chalega: `SAFAR_LLM_PROVIDER=pollinations`
   set karo to free no-key LLM use hoga.

2. **Install & run:**
   ```bash
   cd voice-agent
   cp .env.example .env
   # open .env and paste your GEMINI_API_KEY
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   .venv/bin/uvicorn server:app --host 0.0.0.0 --port 8000
   ```

3. **Talk to it** — open http://localhost:8000 in **Chrome**, tap 🎤, ask e.g.
   *"Hunza ka best time kab hai?"* or *"How much does a 5-day Skardu trip cost?"*

4. No mic? Just type in the box — text mode works as a fallback.

## How it works

```
 mic → Web Speech API (browser, free) → transcript
     → POST /api/chat → Gemini + knowledge_base.md → answer text
     → POST /api/tts → Edge-TTS MP3 → played in browser
```

- `server.py` — FastAPI app: `/api/chat`, `/api/tts`, `/api/health`, serves the page.
- `static/index.html` — the call UI (mic button, Urdu/English toggle, transcript).
- `knowledge_base.md` — destinations, routes, seasons, budget formulas, safety.
  **Edit this file to improve the guide's answers** — no code changes needed.

## WhatsApp voice-note bot (also free)

Live WhatsApp **calls** with an AI agent aren't possible with free tools, but
**voice notes** are — and for a travel guide that's just as good:

```
You: 🎤 voice note  →  bot transcribes (faster-whisper, on your machine)
                   →  Safar Guide answers (Gemini)
                   →  bot replies with a 🎤 voice note (Edge TTS)
```

**Run it:**
```bash
cd voice-agent
.venv/bin/pip install -r requirements.txt   # adds faster-whisper (STT)
.venv/bin/uvicorn server:app --host 0.0.0.0 --port 8000   # terminal 1

cd whatsapp-bot
npm install        # first time only
node bot.js        # terminal 2 -> QR code prints
```
Scan the QR with **WhatsApp → Linked devices → Link a device**. Then send a
voice note to that WhatsApp account (message yourself, or ask a friend to
message it). First voice note also downloads the Whisper model (~150 MB, once).

- Text messages get text replies; voice notes get voice-note replies.
- Session is saved in `whatsapp-bot/auth/` — you scan only once.
- This uses Baileys (unofficial WhatsApp library). Fine for an FYP demo; a
  production service should use the official WhatsApp Cloud API instead.

## Apna number connect karo — LIVE WhatsApp voice calls 📞

Is mein do hisse hain. **Pehla hissa SIRF tum kar sakte ho** (OTP tumhare
phone pe aata hai — ye Meta/carrier ka rule hai, koi developer tumhare liye
nahi kar sakta). **Doosra hissa (AI agent) maine bana diya hai.**

### Tumhara hissa (10 minute, ek dafa)
1. **Zernio** pe free account banao (pehle 2 accounts free, card nahi chahiye).
2. WhatsApp section mein **apna number add karo** (+92 wala). OTP SMS/call
   tumhare phone pe aayegi — verify karo. (Naya number bhi le sakte ho ~$3/mo,
   lekin apna existing number bhi register ho jata hai.)
3. Us number pe **voice calling enable** karo.
4. Number ki voice setting mein `forwardTo` = `wss://TUMHARA-SERVER/ws/voice`
   set karo. Demo ke liye: `ngrok http 8001` chalao, jo `https://...` URL mile
   usko `wss://...` bana ke yahan paste karo.

### AI agent ka hissa (already built ✅)
```bash
cd voice-agent
.venv/bin/uvicorn media_server:app --host 0.0.0.0 --port 8001
```
Ye `/ws/voice` pe Zernio-style WebSocket media server hai: dono taraf G.711
u-law @ 8 kHz audio. Call aate hi Safar Guide greeting bolta hai, tumhari baat
sunta hai (VAD se jumla khatam hone ka pata chalta hai), faster-whisper se
samajhta hai, Gemini se jawab banata hai, Edge TTS se bolta hai.

**Tested:** `test_call.py` poori simulated live call chalata hai —
greeting (13s) → caller (3s) → VAD → STT → reply (8.6s), aur reply ka transcript
verify hota hai. Chalane ke liye:
```bash
SAFAR_FAKE_REPLY=1 SAFAR_TTS_PROVIDER=gtts \
  .venv/bin/uvicorn media_server:app --host 127.0.0.1 --port 8126 &
.venv/bin/python test_call.py
```

**Limitations (v1):** half-duplex hai — agent bolte waqt caller ki awaz ignore
hoti hai (beech mein tokna/ barge-in future work). JSON control events
(`start`/`stop`) tolerate kiye jate hain; provider ke exact event naam live
karne se pehle Zernio ki "AI voice agents" guide se match kar lena.

## Optional: real phone-call demo (still free, via Twilio trial)

1. Sign up at twilio.com/try-twilio → you get **$15 free credit** + a free US number.
2. Point the number's voice webhook at a `/twilio-voice` endpoint (not yet
   implemented — ~40 lines using Twilio Media Streams; ask me and I'll add it).
3. Call the number from your phone and talk to Safar Guide. Trial credit covers
   roughly 1,000+ minutes of demo calls.

## FYP notes (for the report)

- Module 1 pipeline: STT → LLM → TTS, exactly as proposed in the synopsis.
- All figures in the knowledge base are labeled estimates; the agent is
  instructed never to invent prices or road statuses.
- Swap Gemini for any OpenAI-compatible API later without touching the UI.
