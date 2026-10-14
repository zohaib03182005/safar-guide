# Safar Guide — voice agent site (slim cloud build).
# Uses requirements-cloud.txt: NO torch/faster-whisper/av, so the image is
# small (~150 MB) and fits free-tier RAM. Chat runs on the free pollinations.ai
# API (no key); mic uses the browser's Web Speech API; TTS uses Edge TTS with
# browser speech-synthesis fallback.
FROM python:3.12-slim

WORKDIR /app

COPY requirements-cloud.txt .
RUN pip install --no-cache-dir -r requirements-cloud.txt

COPY brain.py voice.py server.py knowledge_base.md ./
COPY static ./static

# Free LLM for the public demo (no API key needed).
# Set SAFAR_LLM_PROVIDER=gemini + GEMINI_API_KEY for better quality.
ENV SAFAR_LLM_PROVIDER=pollinations

EXPOSE 8000
# Render (and most hosts) inject $PORT; default to 8000 locally.
CMD uvicorn server:app --host 0.0.0.0 --port ${PORT:-8000}
