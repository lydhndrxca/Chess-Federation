#!/usr/bin/env python3
"""Generate ElevenLabs audio for all Crypt dialogue lines.

Creates mp3 files in app/static/audio/enoch/crypt_*/ and updates manifest.json.

Usage:
    python generate_crypt_audio.py
"""

import json
import os
import sys
import time

import requests

API_KEY = "sk_33435639f469f48ea44796e33e99bc356d342b31ff9ee114"
VOICE_ID = "9Vz82zdsVrUAmqOZoUIj"
TTS_URL = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"

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
    from app.services.crypt_dialogue import (
        WAVE_START, PIECES_ENTERING, PLAYER_CAPTURES, ENEMY_CAPTURES,
        PLAYER_CHECKS, ENEMY_CHECKS, WAVE_COMPLETE, SHOPPING, BUY_PIECE,
        GAME_OVER, NEW_HIGH_SCORE, BATTLE_IDLE, LATE_WAVE, FIRST_WAVE,
        WAVE_SPECIFIC, MILESTONE_REACHED, CASHOUT_LINES,
        BOSS_BATTLE, BOSS_VICTORY, BOSS_DEFEAT,
    )

    categories = [
        ("crypt_wave_start", WAVE_START),
        ("crypt_pieces_entering", PIECES_ENTERING),
        ("crypt_player_captures", PLAYER_CAPTURES),
        ("crypt_enemy_captures", ENEMY_CAPTURES),
        ("crypt_player_checks", PLAYER_CHECKS),
        ("crypt_enemy_checks", ENEMY_CHECKS),
        ("crypt_wave_complete", WAVE_COMPLETE),
        ("crypt_shopping", SHOPPING),
        ("crypt_game_over", GAME_OVER),
        ("crypt_high_score", NEW_HIGH_SCORE),
        ("crypt_battle_idle", BATTLE_IDLE),
        ("crypt_late_wave", LATE_WAVE),
        ("crypt_first_wave", FIRST_WAVE),
        ("crypt_cashout", CASHOUT_LINES),
        ("crypt_boss_battle", BOSS_BATTLE),
        ("crypt_boss_victory", BOSS_VICTORY),
        ("crypt_boss_defeat", BOSS_DEFEAT),
    ]

    for piece_key, lines in BUY_PIECE.items():
        categories.append((f"crypt_buy_{piece_key.lower()}", lines))

    for wave_num in sorted(WAVE_SPECIFIC):
        categories.append((f"crypt_wave_{wave_num}", WAVE_SPECIFIC[wave_num]))

    for milestone_wave in sorted(MILESTONE_REACHED):
        categories.append((f"crypt_milestone_{milestone_wave}", MILESTONE_REACHED[milestone_wave]))

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

    print(f"Total crypt lines: {total}")
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
