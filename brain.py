"""
Shared "brain" for Safar Guide — the travel-guide LLM logic used by:
  - server.py        (/api/chat for the web demo)
  - whatsapp-bot/    (via HTTP)
  - media_server.py  (live WhatsApp/PSTN calls over WebSocket)

Set GEMINI_API_KEY in .env (free key from https://aistudio.google.com).
"""
import os

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(BASE_DIR, "knowledge_base.md"), encoding="utf-8") as f:
    KNOWLEDGE_BASE = f.read()

SYSTEM_PROMPT = """You are "Safar Guide", a friendly AI voice travel guide for Pakistan's
Northern Areas (Gilgit-Baltistan, Hunza, Skardu, Naran-Kaghan, Swat), part of a
final-year university project.

Rules:
- Answer in the SAME language the traveler uses (Urdu or English).
- Keep spoken answers SHORT: 2-4 sentences, then offer to say more.
- Use the knowledge base below. Present prices as estimates.
- Never invent hotel names, prices, or road statuses. If unsure, say your data
  may be outdated and the traveler should confirm locally.
- For bookings, mention they can use the platform's travel-agent marketplace.

KNOWLEDGE BASE:
""" + KNOWLEDGE_BASE

# Free-tier friendly default; override with GEMINI_MODEL if it changes.
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# LLM provider: "gemini" (needs GEMINI_API_KEY, better quality) or
# "pollinations" (free, no key at all — used for the public demo deploy).
LLM_PROVIDER = os.getenv("SAFAR_LLM_PROVIDER", "gemini")


class BrainError(Exception):
    pass


def _pollinations_reply(message: str) -> str:
    import urllib.parse
    import urllib.request

    prompt = SYSTEM_PROMPT + "\n\nTraveler question: " + message.strip()
    url = "https://text.pollinations.ai/" + urllib.parse.quote(prompt)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            text = r.read().decode("utf-8", errors="replace").strip()
    except Exception as e:
        raise BrainError(f"Free LLM service error: {e}")
    if not text:
        raise BrainError("Free LLM service returned an empty reply.")
    return text


def generate_reply(message: str, lang: str = "ur") -> str:
    """Text question -> travel-guide answer. Raises BrainError on failure."""
    if LLM_PROVIDER == "pollinations":
        return _pollinations_reply(message)

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise BrainError(
            "GEMINI_API_KEY missing. Get a free key at https://aistudio.google.com "
            "and put it in your .env file."
        )
    import google.generativeai as genai

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(GEMINI_MODEL, system_instruction=SYSTEM_PROMPT)
    try:
        resp = model.generate_content(message)
        return resp.text.strip()
    except Exception as e:
        raise BrainError(f"AI service error: {e}")
