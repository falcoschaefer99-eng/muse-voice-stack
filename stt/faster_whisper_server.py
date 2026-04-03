#!/usr/bin/env python3
"""OpenAI-compatible transcription endpoint powered by faster-whisper.

Exposes:
  - GET  /healthz
  - POST /v1/audio/transcriptions

Designed as a drop-in STT backend for src/telegram-voice-bridge.ts.
"""

from __future__ import annotations

import hmac
import ipaddress
import os
import tempfile
from pathlib import Path
from typing import Any, Optional

import uvicorn
from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import PlainTextResponse
from faster_whisper import WhisperModel


def bool_env(name: str, fallback: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return fallback
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def int_env(name: str, fallback: int, *, minimum: int = 1) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return fallback
    try:
        value = int(raw)
    except ValueError:
        return fallback
    return value if value >= minimum else fallback


HOST = os.getenv("FW_HOST", "127.0.0.1")
PORT = int_env("FW_PORT", 8788)

DEFAULT_MODEL = os.getenv("FW_DEFAULT_MODEL", "small")
DEVICE = os.getenv("FW_DEVICE", "auto")
COMPUTE_TYPE = os.getenv("FW_COMPUTE_TYPE", "int8")
CPU_THREADS = int_env("FW_CPU_THREADS", 4)
BEAM_SIZE = int_env("FW_BEAM_SIZE", 5)
MAX_UPLOAD_MB = int_env("FW_MAX_UPLOAD_MB", 25)
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024

VAD_FILTER = bool_env("FW_VAD_FILTER", True)
PRELOAD_MODEL = bool_env("FW_PRELOAD_MODEL", True)

DOWNLOAD_ROOT = os.getenv("FW_DOWNLOAD_ROOT", "").strip() or None
LOCAL_FILES_ONLY = bool_env("FW_LOCAL_FILES_ONLY", False)

API_KEY = os.getenv("FW_API_KEY", "").strip() or None

MODEL_ALIASES: dict[str, str] = {
    "whisper-1": DEFAULT_MODEL,
}

ALLOWED_MODELS_RAW = os.getenv("FW_ALLOWED_MODELS", "").strip()
ALLOW_ANY_MODEL = ALLOWED_MODELS_RAW == "*"
if ALLOW_ANY_MODEL:
    ALLOWED_MODELS: set[str] = set()
elif ALLOWED_MODELS_RAW:
    ALLOWED_MODELS = {token.strip() for token in ALLOWED_MODELS_RAW.split(",") if token.strip()}
else:
    ALLOWED_MODELS = {DEFAULT_MODEL, "whisper-1", "tiny", "base", "small", "medium", "large-v3"}

MODEL_CACHE: dict[str, WhisperModel] = {}

app = FastAPI(title="faster-whisper OpenAI-compatible server", version="0.1.0")


def _is_loopback_host(host: str) -> bool:
    token = host.strip().lower()
    if token in {"localhost", "127.0.0.1", "::1"}:
        return True
    try:
        return ipaddress.ip_address(token).is_loopback
    except ValueError:
        return False


def _auth(authorization: Optional[str]) -> None:
    if not API_KEY:
        return
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    candidate = authorization.split(" ", 1)[1].strip()
    if not hmac.compare_digest(candidate, API_KEY):
        raise HTTPException(status_code=401, detail="Invalid bearer token")


def _resolve_model(requested: Optional[str]) -> str:
    if not requested or not requested.strip():
        resolved = DEFAULT_MODEL
    else:
        token = requested.strip()
        resolved = MODEL_ALIASES.get(token, token)

    if not ALLOW_ANY_MODEL and resolved not in ALLOWED_MODELS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported model '{resolved}'. Set FW_ALLOWED_MODELS to allow it.",
        )

    return resolved


def _get_model(model_name: str) -> WhisperModel:
    cached = MODEL_CACHE.get(model_name)
    if cached is not None:
        return cached

    kwargs: dict[str, Any] = {
        "device": DEVICE,
        "compute_type": COMPUTE_TYPE,
        "cpu_threads": CPU_THREADS,
        "local_files_only": LOCAL_FILES_ONLY,
    }
    if DOWNLOAD_ROOT:
        kwargs["download_root"] = DOWNLOAD_ROOT

    model = WhisperModel(model_name, **kwargs)
    MODEL_CACHE[model_name] = model
    return model


@app.on_event("startup")
def _startup() -> None:
    if not API_KEY and not _is_loopback_host(HOST):
        raise RuntimeError("FW_API_KEY is required when FW_HOST is non-loopback")
    if PRELOAD_MODEL:
        _get_model(DEFAULT_MODEL)


@app.get("/healthz")
def healthz() -> dict[str, Any]:
    return {
        "ok": True,
        "auth_required": bool(API_KEY),
        "default_model": DEFAULT_MODEL,
        "device": DEVICE,
        "compute_type": COMPUTE_TYPE,
        "allow_any_model": ALLOW_ANY_MODEL,
        "allowed_models": sorted(ALLOWED_MODELS) if not ALLOW_ANY_MODEL else ["*"],
        "preloaded_models": sorted(MODEL_CACHE.keys()),
    }


@app.post("/v1/audio/transcriptions")
async def transcriptions(
    file: UploadFile = File(...),
    model: Optional[str] = Form(None),
    language: Optional[str] = Form(None),
    prompt: Optional[str] = Form(None),
    response_format: str = Form("json"),
    authorization: Optional[str] = Header(default=None),
):
    _auth(authorization)
    tmp_path: Optional[str] = None
    try:
        suffix = Path(file.filename or "audio.ogg").suffix or ".ogg"
        with tempfile.NamedTemporaryFile(prefix="fw_", suffix=suffix, delete=False) as tmp:
            tmp_path = tmp.name
            total = 0
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_UPLOAD_BYTES:
                    raise HTTPException(status_code=413, detail=f"Uploaded file exceeds {MAX_UPLOAD_MB}MB limit")
                tmp.write(chunk)

        if total == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")

        resolved_model = _resolve_model(model)
        whisper = _get_model(resolved_model)

        transcribe_kwargs: dict[str, Any] = {
            "beam_size": BEAM_SIZE,
            "vad_filter": VAD_FILTER,
        }
        if language:
            transcribe_kwargs["language"] = language
        if prompt:
            transcribe_kwargs["initial_prompt"] = prompt

        segments_iter, info = whisper.transcribe(tmp_path, **transcribe_kwargs)
        segments = list(segments_iter)
        text = "".join(seg.text for seg in segments).strip()

        if response_format == "text":
            return PlainTextResponse(text)

        if response_format in {"json", "simple_json"}:
            return {"text": text}

        if response_format == "verbose_json":
            return {
                "task": "transcribe",
                "language": getattr(info, "language", language),
                "duration": getattr(info, "duration", None),
                "text": text,
                "segments": [
                    {
                        "id": idx,
                        "start": seg.start,
                        "end": seg.end,
                        "text": seg.text,
                        "avg_logprob": seg.avg_logprob,
                        "compression_ratio": seg.compression_ratio,
                        "no_speech_prob": seg.no_speech_prob,
                    }
                    for idx, seg in enumerate(segments)
                ],
            }

        raise HTTPException(
            status_code=400,
            detail="Unsupported response_format. Supported: text, json, simple_json, verbose_json",
        )
    finally:
        if tmp_path is not None:
            try:
                os.remove(tmp_path)
            except OSError:
                pass


if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")
