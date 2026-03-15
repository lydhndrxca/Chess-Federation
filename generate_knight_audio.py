#!/usr/bin/env python3
"""Generate ElevenLabs audio for the frozen-knight (Lame Knees) decree lines.

Usage:
    set ELEVENLABS_API_KEY=sk_your_key
    python generate_knight_audio.py
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


def generate_audio(text, output_path, retries=3):
    body = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": VOICE_SETTINGS,
    }
    for attempt in range(retries):
        try:
            resp = requests.post(TTS_URL, headers=HEADERS, json=body, timeout=30)
            if resp.status_code == 429:
                wait = 10 * (attempt + 1)
                print(f"    Rate limited — waiting {wait}s...")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(resp.content)
            return True
        except Exception as e:
            print(f"    Attempt {attempt+1} failed: {e}")
            time.sleep(3)
    return False


def build_line_list():
    sys.path.insert(0, '.')
    from app.services.dialogue import CUSTOM_KNIGHT_RULE
    from app.services.weekly_rule import RULE_ENOCH_ANNOUNCEMENT

    lines = []
    for i, text in enumerate(CUSTOM_KNIGHT_RULE):
        lines.append(('knight_frozen', i, text))
    lines.append(('knight_announce', 0, RULE_ENOCH_ANNOUNCEMENT))
    return lines


def main():
    lines = build_line_list()
    print(f"Generating {len(lines)} audio files...\n")

    manifest = {}
    if os.path.exists(MANIFEST_PATH):
        with open(MANIFEST_PATH) as f:
            manifest = json.load(f)

    generated = 0
    for category, idx, text in lines:
        folder = os.path.join(AUDIO_ROOT, category)
        filename = f"{idx:03d}.mp3"
        filepath = os.path.join(folder, filename)

        key = f"{category}/{filename}"
        if os.path.exists(filepath):
            print(f"  [skip] {key} (exists)")
            manifest[key] = text
            continue

        print(f"  [{generated+1}] {key}: {text[:60]}...")
        if generate_audio(text, filepath):
            manifest[key] = text
            generated += 1
            time.sleep(0.5)
        else:
            print(f"    FAILED: {key}")

    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"\nDone. Generated {generated} new files.")
    print(f"Manifest updated: {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
