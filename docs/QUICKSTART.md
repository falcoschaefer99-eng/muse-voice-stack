# Quickstart

## 1) Install deps

```bash
npm install
```

## 2) Configure env

```bash
cp .env.example .env
# fill TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, BRAIN_URL, BRAIN_API_KEY
```

## 3) Optional: bootstrap MUSE TTS repo

```bash
./scripts/setup-voice-stack.sh
```

## 4) Start STT sidecar

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r stt/requirements.txt
python stt/faster_whisper_server.py
```

## 5) Start Telegram voice bridge

```bash
npm run build
node dist/telegram-voice-bridge.js
```

## 6) Send one demo notification (+ voice note if enabled)

```bash
npm run demo:notify
```
