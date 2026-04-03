# faster-whisper STT sidecar

OpenAI-compatible transcription endpoint for the Telegram voice bridge.

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r stt/requirements.txt
```

## Run

```bash
# optional hardening
export FW_API_KEY=replace-me

# runtime tuning
export FW_DEFAULT_MODEL=small
export FW_DEVICE=auto
export FW_COMPUTE_TYPE=int8
export FW_PORT=8788

python stt/faster_whisper_server.py
```

Endpoints:
- `GET /healthz`
- `POST /v1/audio/transcriptions`

If `FW_API_KEY` is set, send:

```http
Authorization: Bearer <FW_API_KEY>
```
