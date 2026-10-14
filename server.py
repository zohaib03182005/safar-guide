"""
Northern Areas AI Voice Guide — backend (Module 1 of the FYP travel platform).

100% free stack:
  - Brain : Google Gemini free tier (user supplies a free API key from AI Studio)
  - Voice : Microsoft Edge TTS (free, no key; has ur-PK voices)
  - Ears   : browser Web Speech API (free, built into Chrome/Edge) — see static/index.html
            /api/stt (faster-whisper, local) for the WhatsApp voice-note bot

Run:
    pip install -r requirements.txt
    copy .env.example to .env and add GEMINI_API_KEY
    uvicorn server:app --host 0.0.0.0 --port 8000
Then open http://localhost:8000
"""
import os
import tempfile

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from brain import GEMINI_MODEL, BrainError, generate_reply
from voice import audio_to_pcm16k, get_whisper, synthesize_speech, transcribe_pcm16k

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = FastAPI(title="Safar Guide — AI Voice Travel Agent")


class ChatRequest(BaseModel):
    message: str
    lang: str = "ur"  # "ur" or "en"


class TtsRequest(BaseModel):
    text: str
    lang: str = "ur"


@app.post("/api/chat")
def chat(req: ChatRequest):
    """Text in -> travel-guide answer out. The browser handles speech in/out."""
    try:
        return {"reply": generate_reply(req.message, req.lang)}
    except BrainError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/tts")
def tts(req: TtsRequest):
    """Text in -> MP3 audio out (Edge TTS, free, no key)."""
    try:
        audio = synthesize_speech(req.text, req.lang)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"TTS error: {e}")
    return Response(content=audio, media_type="audio/mpeg")


@app.get("/api/health")
def health():
    return {
        "ok": True,
        "llm_provider": os.getenv("SAFAR_LLM_PROVIDER", "gemini"),
        "gemini_key_set": bool(os.getenv("GEMINI_API_KEY")),
        "model": GEMINI_MODEL,
    }


@app.post("/api/stt")
async def stt(file: UploadFile = File(...), lang: str = "ur"):
    """Audio file (ogg/mp3/wav, e.g. a WhatsApp voice note) in -> transcript out."""
    data = await file.read()
    if not data or len(data) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Empty or too large file (max 10 MB).")
    suffix = os.path.splitext(file.filename or "")[1] or ".ogg"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(data)
        path = tmp.name
    try:
        with open(path, "rb") as f:
            raw = f.read()
        pcm16k = audio_to_pcm16k(raw)
        return {"text": transcribe_pcm16k(pcm16k, lang)}
    except ImportError:
        # Slim cloud build ships without faster-whisper/av; the web demo's
        # mic uses the browser's built-in speech recognition instead.
        raise HTTPException(
            status_code=501,
            detail="Voice-note transcription isn't enabled on the cloud demo "
                   "(available in the full local setup).",
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"STT error: {e}")
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


app.mount("/", StaticFiles(directory=os.path.join(BASE_DIR, "static"), html=True), name="static")
