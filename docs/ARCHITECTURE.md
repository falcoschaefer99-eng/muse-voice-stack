# Architecture

## Components

1. **Telegram notifier** (`src/telegram-notifier.ts`)
   - Sends text notifications.
   - Optionally synthesizes and sends voice notes via `VOICE_TTS_URL`.
   - Default persona map:
     - `rainer -> lewis`
     - `companion -> onyx`

2. **Telegram voice bridge** (`src/telegram-voice-bridge.ts`)
   - Polls Telegram `getUpdates` for inbound voice messages.
   - Downloads voice note file.
   - Sends audio to OpenAI-compatible STT endpoint.
   - Persists transcript into brain via `mind_observe` in whisper mode.

3. **STT sidecar** (`stt/faster_whisper_server.py`)
   - OpenAI-compatible `/v1/audio/transcriptions` endpoint.
   - Backed by `faster-whisper`.

## Data flow

Telegram voice note -> bridge -> STT -> transcript text -> `mind_observe` -> brain memory
