"""
Shared audio helpers for Safar Guide — used by server.py (REST) and
media_server.py (live WebSocket calls).

  - transcribe_audio(wav_bytes_16k, lang) : faster-whisper, free, local
  - synthesize_speech(text, lang)         : Edge TTS (free, no key) -> MP3 bytes
  - pcmu_to_wav16k / wav16k_to_pcmu       : G.711 u-law <-> 16 kHz PCM helpers
    for the telephony WebSocket (Zernio-style: PCMU @ 8 kHz both ways)
"""
import audioop
import io
import os
import wave

# Edge-TTS voices (free, no API key). ur-PK voices speak Urdu naturally.
VOICES = {
    "ur": "ur-PK-UzmaNeural",    # female Urdu (Pakistan)
    "ur_male": "ur-PK-AsadNeural",
    "en": "en-US-AvaNeural",     # female English
}

_whisper_model = None


def _sanitize_proxy_env():
    # huggingface_hub's vendored URL parser chokes on bracketed IPv6 entries
    # like [::1] in no_proxy (seen on some proxied VMs/containers). Strip them
    # so the model download / cache check doesn't crash.
    for key in ("no_proxy", "NO_PROXY"):
        val = os.environ.get(key)
        if val and "[" in val:
            os.environ[key] = ",".join(p for p in val.split(",") if "[" not in p)


def get_whisper():
    global _whisper_model
    if _whisper_model is None:
        _sanitize_proxy_env()
        from faster_whisper import WhisperModel
        # "base" is a good speed/accuracy trade for short utterances on CPU.
        # First run downloads ~150 MB from Hugging Face (one time).
        _whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
    return _whisper_model


def transcribe_pcm16k(pcm_bytes: bytes, lang: str = "ur") -> str:
    """16-bit mono PCM @ 16 kHz -> transcript. Tries `lang`, falls back to English."""
    import numpy as np

    model = get_whisper()
    audio = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
    for attempt in (lang, "en"):
        segments, _ = model.transcribe(audio, language=attempt, beam_size=5)
        text = " ".join(s.text.strip() for s in segments).strip()
        if text:
            return text
    return ""


def synthesize_speech(text: str, lang: str = "ur") -> bytes:
    """Text -> MP3 bytes via Edge TTS (free, no key)."""
    import asyncio
    import edge_tts

    # Test hook: SAFAR_TTS_PROVIDER=gtts uses Google Translate TTS instead
    # (only for environments where Edge TTS is unreachable).
    if os.getenv("SAFAR_TTS_PROVIDER") == "gtts":
        return _synthesize_gtts(text, lang)

    voice = VOICES.get(lang, VOICES["ur"])
    text = text.strip()[:2000]
    if not text:
        raise ValueError("Empty text.")

    async def _synthesize():
        communicate = edge_tts.Communicate(text, voice)
        audio = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio += chunk["data"]
        return audio

    return asyncio.run(_synthesize())


def _synthesize_gtts(text: str, lang: str = "ur") -> bytes:
    import urllib.parse
    import urllib.request

    q = urllib.parse.quote(text[:200])
    tl = "ur" if lang == "ur" else "en"
    url = (f"https://translate.google.com/translate_tts?ie=UTF-8&q={q}"
           f"&tl={tl}&client=tw-ob")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def audio_to_pcm16k(audio_bytes: bytes) -> bytes:
    """Any audio (mp3/ogg/wav) -> 16-bit mono PCM @ 16 kHz (for Whisper)."""
    import av

    container = av.open(io.BytesIO(audio_bytes))
    resampler = av.AudioResampler(format="s16", layout="mono", rate=16000)
    out = io.BytesIO()
    for frame in container.decode(audio=0):
        for rframe in resampler.resample(frame):
            out.write(rframe.to_ndarray().tobytes())
    return out.getvalue()


def mp3_to_pcmu8k(mp3_bytes: bytes) -> bytes:
    """MP3 -> G.711 u-law mono @ 8 kHz (telephony wire format)."""
    import av

    container = av.open(io.BytesIO(mp3_bytes))
    resampler = av.AudioResampler(format="s16", layout="mono", rate=8000)
    pcm = io.BytesIO()
    for frame in container.decode(audio=0):
        for rframe in resampler.resample(frame):
            pcm.write(rframe.to_ndarray().tobytes())
    return audioop.lin2ulaw(pcm.getvalue(), 2)


def pcmu8k_to_pcm16k(pcmu: bytes) -> bytes:
    """G.711 u-law @ 8 kHz -> 16-bit mono PCM @ 16 kHz (for Whisper)."""
    linear8k = audioop.ulaw2lin(pcmu, 2)
    pcm16k, _ = audioop.ratecv(linear8k, 2, 1, 8000, 16000, None)
    return pcm16k


def pcm16k_to_wav(pcm_bytes: bytes) -> bytes:
    """16-bit mono PCM @ 16 kHz -> WAV bytes (handy for debugging)."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(pcm_bytes)
    return buf.getvalue()
