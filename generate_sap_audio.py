#!/usr/bin/env python3
"""Generate ElevenLabs audio for Spectacle Lake Enoch lines.

Usage:
    set ELEVENLABS_API_KEY=sk_your_key
    python generate_sap_audio.py
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

# Enoch's harvest fury lines (short, shouted)
HARVEST_FURY = [
    "NO!", "MINE!", "That sap is MINE!", "GET AWAY FROM MY TREE!",
    "STOP TOUCHING IT!", "I PLANTED THAT!", "THIEF!", "Little RAT!",
    "HANDS OFF!", "You DARE?!", "I'LL DROWN YOU IN MAPLE!",
    "The forest HATES you!", "Every drop is MINE!",
    "I can SMELL your greed!", "You'll PAY for that!",
    "The roots remember!", "GET OUT!", "VERMIN!", "My PRECIOUS sap!",
    "I waited YEARS for this!", "The trees SCREAM!", "Leave! LEAVE!",
    "I'll BURY you here!", "WRETCHED tapper!", "Not ONE drop!",
    "The bark weeps!", "BACK! BACK!", "From the BASEMENT I send them!",
    "My minions! SWARM!", "Choke on amber!",
]

HARVEST_SURVIVED = [
    "No... no no no no no...",
    "You got one. Fine. FINE. It won't happen again.",
    "Enjoy that bucket. It's the last one you'll ever fill.",
    "The forest will remember this theft.",
    "One tree. ONE. The next won't be so easy.",
]

HARVEST_DEFEATED = [
    "HA! Yes! YES! The forest RECLAIMS!",
    "Down you go. Into the roots. Where you BELONG.",
    "Did you really think you could steal from ME?",
    "The sap stays in the bark. AS IT SHOULD.",
    "Another little thief, consumed by the forest.",
]

ANNOUNCEMENT = [
    "I found a door behind the boiler that leads outside. Not outside-outside. Forest-outside. There are maple trees. Hundreds of them. The sap runs thick and golden and it is MINE.",
]

CATEGORIES = [
    ("sap_fury", HARVEST_FURY),
    ("sap_survived", HARVEST_SURVIVED),
    ("sap_defeated", HARVEST_DEFEATED),
    ("sap_announce", ANNOUNCEMENT),
]


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


def main():
    manifest = load_manifest()
    total = sum(len(lines) for _, lines in CATEGORIES)
    generated = 0
    skipped = 0
    failed = 0

    print(f"Total sap lines: {total}")
    print(f"Manifest has {len(manifest)} existing entries")
    print()

    for cat, lines in CATEGORIES:
        for i, text in enumerate(lines):
            idx = i + 1
            key = f"{cat}/{idx:03d}"
            file_rel = f"{cat}/{idx:03d}.mp3"
            file_abs = os.path.join(AUDIO_ROOT, file_rel)

            if key in manifest and manifest[key].get("text") == text and os.path.exists(file_abs):
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
