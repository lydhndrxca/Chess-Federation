# Health Report

| Field | Value |
|-------|-------|
| Report ID | `20260310_235035` |
| Date | 2026-03-10 |
| Overall Health | **RED** |
| Primary Issue Type | Hygiene |

---

## Scoring

### RED Triggers

1. **Secret in source code** — `generate_crypt_audio.py:17` contains a full ElevenLabs API key (`sk_3343...e114`). This file is tracked in git and has been pushed to the remote. The key is exposed in the full commit history.

### YELLOW Triggers

1. **Text file > 100 KB** — 3 text files exceed 100 KB:
   - `app/static/audio/enoch/manifest.json` (400 KB)
   - `app/services/dialogue.py` (172 KB)
   - `app/static/css/style.css` (142 KB)
2. **Doc drift** — Multiple features implemented since last doc update are not reflected in `SPEC.md` or `ARCHITECTURE.md` (casual matches, Reckoning zombies, cascade mode, chat reactions, image upload, notifications, turn timer).
3. **Portability warning** — `requirements.txt` lists `chess==1.11.2` which has been known to fail on PythonAnywhere. The actual deployed package is `python-chess`.

---

## Top 3 Risks

1. **Exposed API key** — The ElevenLabs key in `generate_crypt_audio.py` is in the git history. Even if removed now, it remains recoverable. Key should be rotated immediately.
2. **Monolithic growth** — `dialogue.py` (172 KB, ~2,555 LOC), `style.css` (142 KB, ~4,986 LOC), and `standings.html` (~1,160 LOC) are large and growing. Changes become error-prone.
3. **No automated tests** — Zero test files exist. All validation is manual. Regressions are caught only by users.

---

## Top 3 Recommended Actions

1. **Rotate the ElevenLabs API key immediately.** Remove it from `generate_crypt_audio.py`, load from `.env` instead. Consider `git filter-branch` or BFG to scrub history.
2. **Split `dialogue.py`** — It contains thousands of string literals for 8+ game modes. Extract each mode's dialogue into its own module.
3. **Add basic smoke tests** — A `pytest` suite that imports the app factory and hits each route with a test client would catch import errors and crashes.

---

## Findings

### 1. Governance

All 7 governance documents exist and are well-structured. `AGENT_RULES.md` explicitly forbids committing secrets (rule 6), which is currently violated.

### 2. Drift & Bloat

| File | Size | LOC | Concern |
|------|------|-----|---------|
| `dialogue.py` | 172 KB | ~2,555 | All Enoch dialogue for all modes in one file |
| `style.css` | 142 KB | ~4,986 | All CSS for all pages/modes in one file |
| `manifest.json` | 400 KB | 11,038 | Audio manifest; auto-generated, acceptable |
| `standings.html` | ~48 KB | ~1,160 | Template with embedded JS for compact chat |

### 3. Doc Drift

| Feature | In Code | In SPEC.md | In ARCHITECTURE.md |
|---------|---------|------------|-------------------|
| Casual matches | Yes (`challenge.py`) | No | No |
| Chat reactions/replies | Yes (`hall.py`) | No | No |
| Chat image upload | Yes (`hall.py`) | No | No |
| Crypt cascade mode | Yes (`crypt.py`) | No | No |
| Reckoning zombies | Yes (`four_player.py`) | No | No |
| Reckoning turn timer | Yes (`four_player.py`) | No | No |
| Web push notifications | Yes (`app.js`) | No | No |
| Last-move animation | Yes (`board.js`) | No | No |
| Decree board theme | Yes (`style.css`) | No | No |

**Doc drift count: 9**

### 4. Cleanup Candidates

| Item | Path | Action |
|------|------|--------|
| Exposed API key | `generate_crypt_audio.py` | Move to `.env`, rotate key |
| Unused generation scripts | `generate_crypt_audio.py`, `setup_rotation.py` | Move to `scripts/` or remove |
| DB in repo | `data/chess_federation.db` | Gitignored but path referenced |
| Screenshots dir | `screenshots/` | Gitignored, fine |

### 5. Growth & Trajectory

The repo has grown substantially since the previous audit (`20260307_231723`). Major additions:
- Crypt cascade mode (new routes, dialogue, audio)
- Reckoning turn timer + auto-move system
- Full chat feature set (reactions, replies, images, edit/delete)
- Web notification system
- 5 new ElevenLabs audio files (auto-move taunts)

Audio assets dominate storage (~252 MB total, vast majority is `app/static/audio/enoch/`).

### 6. Prompt & Template Surface

The largest multi-line string literals are in:
- `app/services/dialogue.py` — Thousands of Enoch dialogue lines across 20+ pools
- `app/services/crypt_dialogue.py` — Crypt-specific dialogue (~100+ lines)
- `app/services/practice_dialogue.py` — Practice mode dialogue
- `app/services/wager_dialogue.py` — Wager mode dialogue
- `app/services/login_greetings.py` — Per-user greeting lines

No near-duplicate prompts detected (each dialogue pool serves a distinct game context).

---

## Proposed Cleanup Plan

1. **P0 (Immediate):** Rotate ElevenLabs API key. Remove from `generate_crypt_audio.py`. Load from env var.
2. **P1 (This week):** Update `SPEC.md` and `ARCHITECTURE.md` to reflect all new features.
3. **P1 (This week):** Split `dialogue.py` into per-mode modules.
4. **P2 (Next sprint):** Add `pytest` smoke tests for route imports and basic GET requests.
5. **P2 (Next sprint):** Consider extracting compact chat JS from `standings.html` into a shared module.
