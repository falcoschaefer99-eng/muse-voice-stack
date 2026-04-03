# Architecture

## Components

1. **Telegram notifier** (`src/telegram-notifier.ts`)
   - Sends text notifications.
   - Optionally synthesizes and sends voice notes via `VOICE_TTS_URL`.
   - Includes optional default persona mapping in env (you can override).

2. **Telegram voice bridge** (`src/telegram-voice-bridge.ts`)
   - Polls Telegram `getUpdates` for inbound voice messages.
   - Downloads voice note file.
   - Sends audio to OpenAI-compatible STT endpoint.
   - Defaults to chat allowlist mode via `TELEGRAM_CHAT_ID`.
   - Persists transcript via configurable memory sink.

3. **Memory sink adapter** (`src/memory-sink.ts`)
   - `file` mode: append transcript records to local NDJSON.
   - `webhook` mode: POST transcript records to your endpoint.
   - `mcp` mode: optional MUSE Brain adapter via `mind_observe`.

4. **STT sidecar** (`stt/faster_whisper_server.py`)
   - OpenAI-compatible `/v1/audio/transcriptions` endpoint.
   - Backed by `faster-whisper`.

## Data flow

Telegram voice note -> bridge -> STT -> transcript text -> selected memory sink (`file` | `webhook` | `mcp`)
