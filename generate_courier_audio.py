#!/usr/bin/env python3
"""Generate ElevenLabs audio for all Courier Run dialogue lines.

Creates mp3 files in app/static/audio/enoch/courier_*/ and updates manifest.json.

Usage:
    python generate_courier_audio.py
    python generate_courier_audio.py --force   # regenerate all
"""

import json
import os
import sys
import time

import requests

API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "9Vz82zdsVrUAmqOZoUIj")
TTS_URL = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"

if not API_KEY:
    print("ERROR: Set ELEVENLABS_API_KEY environment variable")
    print("  Windows:  set ELEVENLABS_API_KEY=sk_your_key_here")
    print("  Linux:    export ELEVENLABS_API_KEY=sk_your_key_here")
    sys.exit(1)

AUDIO_ROOT = os.path.join("app", "static", "audio", "enoch")
MANIFEST_PATH = os.path.join(AUDIO_ROOT, "manifest.json")

HEADERS = {
    "xi-api-key": API_KEY,
    "Content-Type": "application/json",
    "Accept": "audio/mpeg",
}

VOICE_SETTINGS = {
    "stability": 0.35,
    "similarity_boost": 0.78,
    "style": 0.15,
    "use_speaker_boost": True,
}


def load_manifest():
    if os.path.exists(MANIFEST_PATH):
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_manifest(manifest):
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)


def generate_audio(text, output_path, retries=3):
    payload = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": VOICE_SETTINGS,
    }
    for attempt in range(retries):
        try:
            resp = requests.post(TTS_URL, headers=HEADERS, json=payload, timeout=30)
            if resp.status_code == 200:
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, "wb") as f:
                    f.write(resp.content)
                return True
            elif resp.status_code == 429:
                wait = 30 * (attempt + 1)
                print(f"  Rate limited, waiting {wait}s...")
                time.sleep(wait)
            else:
                print(f"  ERROR {resp.status_code}: {resp.text[:200]}")
                if attempt < retries - 1:
                    time.sleep(5)
        except Exception as e:
            print(f"  Exception: {e}")
            if attempt < retries - 1:
                time.sleep(5)
    return False


def build_line_list():
    from app.services.courier_dialogue import (
        COURIER_GAME_START, COURIER_SELECTION, COURIER_PLAYER_ADVANCE,
        COURIER_AI_ADVANCE, COURIER_PLAYER_THREAT, COURIER_AI_THREAT,
        COURIER_CAPTURE, COURIER_CAPTURED_BY_PLAYER, COURIER_DELIVERY_WIN,
        COURIER_DELIVERY_LOSS, COURIER_TIEBREAK, COURIER_DRAW,
        COURIER_IDLE, COURIER_ANNOUNCE,
    )

    categories = [
        ("courier_game_start", COURIER_GAME_START),
        ("courier_selection", COURIER_SELECTION),
        ("courier_player_advance", COURIER_PLAYER_ADVANCE),
        ("courier_ai_advance", COURIER_AI_ADVANCE),
        ("courier_player_threat", COURIER_PLAYER_THREAT),
        ("courier_ai_threat", COURIER_AI_THREAT),
        ("courier_capture", COURIER_CAPTURE),
        ("courier_captured_by_player", COURIER_CAPTURED_BY_PLAYER),
        ("courier_delivery_win", COURIER_DELIVERY_WIN),
        ("courier_delivery_loss", COURIER_DELIVERY_LOSS),
        ("courier_tiebreak", COURIER_TIEBREAK),
        ("courier_draw", COURIER_DRAW),
        ("courier_idle", COURIER_IDLE),
        ("courier_announce", [COURIER_ANNOUNCE]),
    ]

    result = []
    for cat, lines in categories:
        for i, text in enumerate(lines):
            result.append((cat, i + 1, text))
    return result


def main():
    force = "--force" in sys.argv
    manifest = load_manifest()
    lines = build_line_list()

    total = len(lines)
    generated = 0
    skipped = 0
    failed = 0

    print(f"Total courier lines: {total}")
    print(f"Manifest has {len(manifest)} existing entries")
    if force:
        print("FORCE mode: regenerating all lines")
    print()

    for cat, idx, text in lines:
        key = f"{cat}/{idx:03d}"
        file_rel = f"{cat}/{idx:03d}.mp3"
        file_abs = os.path.join(AUDIO_ROOT, file_rel)

        if not force and key in manifest and manifest[key].get("text") == text and os.path.exists(file_abs):
            skipped += 1
            continue

        print(f"[{generated + skipped + failed + 1}/{total}] {key}: {text[:60]}...")
        ok = generate_audio(text, file_abs)
        if ok:
            manifest[key] = {"text": text, "file": file_rel}
            generated += 1
            save_manifest(manifest)
            time.sleep(0.5)
        else:
            print(f"  FAILED: {key}")
            failed += 1

    print()
    print(f"Done!  Generated: {generated}  Skipped: {skipped}  Failed: {failed}")
    print(f"Manifest now has {len(manifest)} entries")


if __name__ == "__main__":
    main()
