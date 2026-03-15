#!/usr/bin/env python3
"""Generate ElevenLabs audio for all Denarius Exchange (market) dialogue lines.

Creates mp3 files in app/static/audio/enoch/market_*/ and updates manifest.json.

Usage:
    python generate_market_audio.py
    python generate_market_audio.py --force   # regenerate all
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
    """Build the full list of (category, index, text) tuples."""
    from app.services.market_dialogue import (
        MARKET_ENTER, MARKET_BUY, MARKET_SELL, MARKET_PROFIT,
        MARKET_LOSS, MARKET_IDLE, MARKET_LIMIT_SET, MARKET_LIMIT_FILLED,
        MARKET_COIN_QUIPS, MARKET_ANNOUNCE,
    )

    categories = [
        ("market_enter", MARKET_ENTER),
        ("market_buy", MARKET_BUY),
        ("market_sell", MARKET_SELL),
        ("market_profit", MARKET_PROFIT),
        ("market_loss", MARKET_LOSS),
        ("market_idle", MARKET_IDLE),
        ("market_limit_set", MARKET_LIMIT_SET),
        ("market_limit_filled", MARKET_LIMIT_FILLED),
        ("market_coin_quips", MARKET_COIN_QUIPS),
        ("market_announce", [MARKET_ANNOUNCE]),
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

    print(f"Total market lines: {total}")
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
