# muse-voice-stack

Standalone voice layer for MUSE Brain:

- Telegram notifications
- Optional Telegram voice-note TTS
- Telegram inbound voice-note transcription
- Transcript persistence to brain memory (`mind_observe` whisper mode)

Default voice persona mapping:
- `rainer -> lewis`
- `companion -> onyx`

## Quick start

```bash
cp .env.example .env
npm install
npm run build
```

Start STT sidecar:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r stt/requirements.txt
python stt/faster_whisper_server.py
```

Start bridge:

```bash
npm run bridge
```

Send demo message:

```bash
npm run demo:notify
```

For the full setup flow see `docs/QUICKSTART.md`.
