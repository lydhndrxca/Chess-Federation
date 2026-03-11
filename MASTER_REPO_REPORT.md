# Master Repo Report

| Field | Value |
|-------|-------|
| Project root | `D:\dev\Chess Federation` |
| Generated at | 2026-03-10 23:50:35 |
| Includes | Snapshot + Health Audit + Comprehensive Repo Report + TASKS |
| Health | **Red** (report_id: `20260310_235035`) |

---

## Repo Snapshot

# Repo Snapshot

| Field | Value |
|-------|-------|
| Report ID | `20260310_235035` |
| Generated | 2026-03-10 23:50:35 |
| Repo root | `D:\dev\Chess Federation` |
| Git branch | `main` |
| Last commit | `b7bac2f` — 2026-03-10 23:49:14 by lydhndrxca |

---

### Folder Tree (depth 4)

```
.
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── models.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── auth.py
│   │   ├── challenge.py
│   │   ├── crypt.py
│   │   ├── decree.py
│   │   ├── four_player.py
│   │   ├── game.py
│   │   ├── hall.py
│   │   ├── main.py
│   │   └── players.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── chess_engine.py
│   │   ├── collectibles.py
│   │   ├── collectibles_catalog.py
│   │   ├── collectibles_engagement.py
│   │   ├── crypt_dialogue.py
│   │   ├── crypt_logic.py
│   │   ├── dialogue.py          ← 171 KB, largest .py
│   │   ├── enoch.py
│   │   ├── enoch_ai.py
│   │   ├── enoch_chat.py
│   │   ├── four_player_ai.py
│   │   ├── four_player_engine.py
│   │   ├── login_greetings.py
│   │   ├── matchmaking.py
│   │   ├── material.py
│   │   ├── power.py
│   │   ├── practice_dialogue.py
│   │   ├── rating.py
│   │   ├── sequences.py
│   │   ├── wager_dialogue.py
│   │   └── weekly_rule.py
│   ├── static/
│   │   ├── audio/
│   │   │   ├── chess/          (7 sound effects)
│   │   │   ├── crypt/          (7 ambient/thunder clips)
│   │   │   ├── enoch/          (~2,789 TTS mp3s + manifest.json)
│   │   │   └── reckoning/      (6 horn sounds)
│   │   ├── css/
│   │   │   ├── chessground-theme.css
│   │   │   └── style.css       ← 142 KB
│   │   ├── img/
│   │   │   └── enoch.png
│   │   └── js/
│   │       ├── app.js
│   │       ├── audio-cache.js
│   │       ├── board.js
│   │       ├── crypt.js
│   │       ├── four_player.js
│   │       └── hall.js
│   └── templates/
│       ├── account.html, archive.html, base.html, chronicle.html
│       ├── crypt.html, decree.html, four_player.html, game.html
│       ├── hall.html, home.html, macros.html, players.html
│       ├── profile.html, scrapbook.html, standings.html
│       └── auth/
│           ├── login.html
│           └── register.html
├── data/
│   └── chess_federation.db     (gitignored)
├── docs/
│   └── undercroft-exchange-design.md
├── screenshots/live/           (gitignored)
├── .gitignore
├── AGENT_RULES.md
├── ARCHITECTURE.md
├── DECISIONS.md
├── generate_crypt_audio.py
├── Procfile
├── PROJECT.md
├── README.md
├── render.yaml
├── requirements.txt
├── run.bat
├── setup_rotation.py
├── SPEC.md
└── TASKS.md
```

### Governance Docs

| Document | Status |
|----------|--------|
| PROJECT.md | EXISTS (1,341 B) |
| SPEC.md | EXISTS (8,183 B) |
| ARCHITECTURE.md | EXISTS (7,809 B) |
| DECISIONS.md | EXISTS (4,275 B) |
| TASKS.md | EXISTS (2,496 B) |
| README.md | EXISTS (1,451 B) |
| AGENT_RULES.md | EXISTS (2,609 B) |

### Dependencies

**requirements.txt**
```
Flask==3.1.3
Flask-SQLAlchemy==3.1.1
Flask-Login==0.6.3
chess==1.11.2
gunicorn==25.1.0
tzdata==2025.3
```

### LOC by Language

| Extension | Files | LOC |
|-----------|------:|----:|
| .py | 38 | 14,119 |
| .json | 1 | 11,038 |
| .css | 2 | 4,986 |
| .js | 6 | 4,077 |
| .html | 17 | 3,344 |
| .md | 8 | 1,221 |
| .yaml | 1 | 13 |
| .txt | 1 | 6 |
| **Total** | **74** | **38,804** |

### Stats

| Metric | Value |
|--------|-------|
| Total files (all types) | 2,863 |
| Total bytes | 264,474,159 (~252 MB) |
| Audio files (mp3/wav) | ~2,789 |
| Text files | 74 |
| Largest text file | `app/static/audio/enoch/manifest.json` (400 KB / 11,038 LOC) |

### Secrets Detected

| File | Line | Type | Redacted |
|------|------|------|----------|
| `generate_crypt_audio.py` | 17 | ElevenLabs API key | `sk_3343...e114` |

---

## Health Report

# Health Report

| Field | Value |
|-------|-------|
| Report ID | `20260310_235035` |
| Date | 2026-03-10 |
| Overall Health | **RED** |
| Primary Issue Type | Hygiene |

### Scoring

#### RED Triggers

1. **Secret in source code** — `generate_crypt_audio.py:17` contains a full ElevenLabs API key (`sk_3343...e114`). This file is tracked in git and has been pushed to the remote. The key is exposed in the full commit history.

#### YELLOW Triggers

1. **Text file > 100 KB** — 3 text files exceed 100 KB:
   - `app/static/audio/enoch/manifest.json` (400 KB)
   - `app/services/dialogue.py` (172 KB)
   - `app/static/css/style.css` (142 KB)
2. **Doc drift** — Multiple features implemented since last doc update are not reflected in `SPEC.md` or `ARCHITECTURE.md` (casual matches, Reckoning zombies, cascade mode, chat reactions, image upload, notifications, turn timer).
3. **Portability warning** — `requirements.txt` lists `chess==1.11.2` which has been known to fail on PythonAnywhere. The actual deployed package is `python-chess`.

### Top 3 Risks

1. **Exposed API key** — The ElevenLabs key in `generate_crypt_audio.py` is in the git history. Even if removed now, it remains recoverable. Key should be rotated immediately.
2. **Monolithic growth** — `dialogue.py` (172 KB, ~2,555 LOC), `style.css` (142 KB, ~4,986 LOC), and `standings.html` (~1,160 LOC) are large and growing. Changes become error-prone.
3. **No automated tests** — Zero test files exist. All validation is manual. Regressions are caught only by users.

### Top 3 Recommended Actions

1. **Rotate the ElevenLabs API key immediately.** Remove it from `generate_crypt_audio.py`, load from `.env` instead. Consider `git filter-branch` or BFG to scrub history.
2. **Split `dialogue.py`** — It contains thousands of string literals for 8+ game modes. Extract each mode's dialogue into its own module.
3. **Add basic smoke tests** — A `pytest` suite that imports the app factory and hits each route with a test client would catch import errors and crashes.

### Findings

#### 1. Governance

All 7 governance documents exist and are well-structured. `AGENT_RULES.md` explicitly forbids committing secrets (rule 6), which is currently violated.

#### 2. Drift & Bloat

| File | Size | LOC | Concern |
|------|------|-----|---------|
| `dialogue.py` | 172 KB | ~2,555 | All Enoch dialogue for all modes in one file |
| `style.css` | 142 KB | ~4,986 | All CSS for all pages/modes in one file |
| `manifest.json` | 400 KB | 11,038 | Audio manifest; auto-generated, acceptable |
| `standings.html` | ~48 KB | ~1,160 | Template with embedded JS for compact chat |

#### 3. Doc Drift

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

#### 4. Cleanup Candidates

| Item | Path | Action |
|------|------|--------|
| Exposed API key | `generate_crypt_audio.py` | Move to `.env`, rotate key |
| Unused generation scripts | `generate_crypt_audio.py`, `setup_rotation.py` | Move to `scripts/` or remove |
| DB in repo | `data/chess_federation.db` | Gitignored but path referenced |
| Screenshots dir | `screenshots/` | Gitignored, fine |

#### 5. Growth & Trajectory

The repo has grown substantially since the previous audit (`20260307_231723`). Major additions:
- Crypt cascade mode (new routes, dialogue, audio)
- Reckoning turn timer + auto-move system
- Full chat feature set (reactions, replies, images, edit/delete)
- Web notification system
- 5 new ElevenLabs audio files (auto-move taunts)

Audio assets dominate storage (~252 MB total, vast majority is `app/static/audio/enoch/`).

#### 6. Prompt & Template Surface

The largest multi-line string literals are in:
- `app/services/dialogue.py` — Thousands of Enoch dialogue lines across 20+ pools
- `app/services/crypt_dialogue.py` — Crypt-specific dialogue (~100+ lines)
- `app/services/practice_dialogue.py` — Practice mode dialogue
- `app/services/wager_dialogue.py` — Wager mode dialogue
- `app/services/login_greetings.py` — Per-user greeting lines

No near-duplicate prompts detected (each dialogue pool serves a distinct game context).

### Proposed Cleanup Plan

1. **P0 (Immediate):** Rotate ElevenLabs API key. Remove from `generate_crypt_audio.py`. Load from env var.
2. **P1 (This week):** Update `SPEC.md` and `ARCHITECTURE.md` to reflect all new features.
3. **P1 (This week):** Split `dialogue.py` into per-mode modules.
4. **P2 (Next sprint):** Add `pytest` smoke tests for route imports and basic GET requests.
5. **P2 (Next sprint):** Consider extracting compact chat JS from `standings.html` into a shared module.

---

## Tasks

# Chess Federation — Tasks

## Now

(none)

## Health Audit Cleanup

- [ ] Rotate ElevenLabs API key; remove from `generate_crypt_audio.py`, load from `.env`
- [ ] Update `SPEC.md` with all new features (casual matches, chat reactions, cascade, zombies, notifications, turn timer)
- [ ] Update `ARCHITECTURE.md` with new models and routes
- [ ] Split `dialogue.py` into per-mode dialogue modules
- [ ] Add `pytest` smoke tests for route imports and basic requests
- [ ] Extract compact chat JS from `standings.html` into shared module

## Next

- [ ] Variant-capable rules engine (Power Position v2)
- [ ] Custom pieces / board changes / federation mutations
- [ ] Draw by agreement (offer/accept flow)
- [ ] User-customizable federation tier names
- [ ] Email or push notifications for turn alerts
- [ ] Adopt Alembic for DB migrations (replace inline ALTER TABLE)
- [ ] Add automated test suite

## Done

- [x] Health audit report generated (report_id: 20260310_235035)
- [x] Health audit report generated (report_id: 20260307_231723)
- [x] Health audit cleanup: update all governance docs, pin deps, gitignore
- [x] Add 15 Enoch gambling collectibles (The Gambling Debts collection)
- [x] Enoch wager system: daily rated gambling with mood-based stakes and anomaly events
- [x] Enoch mood system: Chill/Annoyed/Angry with deterministic daily schedule
- [x] Enoch Practice Mode: playable NPC opponent with scrapbook archive
- [x] Enoch collectibles system: 170 items across 12 collections
- [x] Enoch chat engine with lurk detection and @Enoch commands
- [x] Federation Hall persistent chat room
- [x] Named openings/variations system
- [x] Post-match commendation/condemnation system
- [x] Automated all-play-all matchmaking with forfeit detection
- [x] Power Position rotation with weekly decree system
- [x] Dark ominous color scheme with ceremonial tone
- [x] Season archive page with monthly data
- [x] Match/decree countdown timers
- [x] Chessground board integration (replaced custom Unicode board)
- [x] Player bio field on registration and profile
- [x] Federation week boundary: Sunday 5 PM CST
- [x] Season start gate: March 8 2026 5 PM CST
- [x] Create governance structure
- [x] Create run.bat entrypoint
- [x] Populate SPEC.md with full feature specification
- [x] Define architecture and tech stack
- [x] TASK-001 through TASK-011 (Flask app, Auth, Chess engine, Board UI, Matchmaking, Rating, Dashboard, Profiles, Match history, Mobile polish, Deployment)

---

## Comprehensive Repo Report

# Chess Federation — Comprehensive Repo Report

### 1. Repo Metadata

| Field | Value |
|-------|-------|
| **Repo root** | `D:\dev\Chess Federation` |
| **Git branch** | `main` |
| **Last commit** | `b7bac2f` (2026-03-10 23:49:14 by lydhndrxca) |
| **Total files** | 2,863 (mostly audio mp3s), 74 text files |
| **Total size** | ~252 MB |
| **Total LOC** | 38,804 across text files |

### 2. What This Repo Is

A private correspondence chess platform built with Python/Flask. Features include:

- **Ceremonial 10-tier ranking system** — from "Ordained Laborer" to "Lord of Schools"
- **Weekly all-play-all matches** — turn-based correspondence chess
- **Rotating Power Position authority** — weekly rule decrees
- **NPC named "Enoch"** — lives in the sub-basement, provides AI opponents and narrative flavor

**Stack:** Python 3 / Flask 3.1, SQLite via Flask-SQLAlchemy, python-chess for move validation, Jinja2 + vanilla JS + CSS frontend, Chessground board library (vendored), Flask-Login for auth, ElevenLabs for TTS audio generation.

### 3. How to Run

**Windows (quick start):** Double-click `run.bat`
**Manual:** `python -m venv .venv && pip install -r requirements.txt && python -c "from app import create_app; create_app().run(debug=True, port=5000)"`
**Production:** PythonAnywhere

### 4–9. Feature Inventory

**Core Chess:** PvP correspondence, casual matches, Chessground board, move confirmation, custom weekly rules, decree board theme, last-move animation.

**Enoch (NPC):** Practice mode, wager mode (3/day), minimax AI (3 difficulty levels), ~2,789 voiced TTS lines, per-user greetings, mood system.

**The Crypt (Solo):** Wave defense, shop system, cascade mode (real-time survival), king-hunting AI, dark theme with horror audio, lightning/thunder effects.

**The Reckoning (4-Player):** Custom 14x14 board, zombie pawns, Enoch AI opponent, 4-hour turn timer, auto-move with taunt lines.

**Chat (Federation Hall):** Reactions, replies, edit/delete, image upload, long message collapse, compact home page chat, Enoch quirks (late-night murmurings, 99 Theses).

**Collectibles:** 170 items across 12 collections, post-match evaluation, Enoch Drawer UI, stacking duplicates.

**Other:** 10-tier ranking, Elo rating, named openings, commendation/condemnation, season archive, web push notifications, player profiles.

### 10. Architecture

Flask app factory pattern. Single SQLite database. Inline migrations in `__init__.py`. 10 route blueprints. 18 service modules. Server-rendered Jinja2 + vanilla JS. State polling via `setInterval` + `fetch`.

Data flow: Browser → Flask routes → Service layer → SQLAlchemy → SQLite.

### 11. External Dependencies

| Type | Details |
|------|---------|
| Runtime | Flask, Flask-SQLAlchemy, Flask-Login, python-chess, gunicorn, tzdata |
| Dev/Build | ElevenLabs API (TTS, offline) |
| CDN | None (self-hosted) |

### 12. Risks & Open Questions

| # | Risk | Location |
|---|------|----------|
| 1 | SECRET — ElevenLabs API key exposed | `generate_crypt_audio.py:17` |
| 2 | MONOLITH — Large single files | `dialogue.py` (172KB), `style.css` (142KB) |
| 3 | NO TESTS | Entire repo |
| 4 | DOC DRIFT — 9 features undocumented | `SPEC.md`, `ARCHITECTURE.md` |
| 5 | INLINE MIGRATIONS — fragile, no rollback | `app/__init__.py` |

**Open Questions:** Is the ElevenLabs key rotated? Is Render.com still used alongside PythonAnywhere? Should root scripts move to `scripts/`?

---

## Master Index

* Snapshot: `.repo_snapshot/repo_snapshot.md`
* Snapshot JSON: `.repo_snapshot/repo_snapshot.json`
* Health Report: `HEALTH_REPORT.md`
* Health Metrics: `.repo_snapshot/health_reports/health_metrics__20260310_235035.json`
* Tasks: `TASKS.md`
* Comprehensive Report: `.repo_snapshot/repo_comprehensive_report.md`
* Master Report: `MASTER_REPO_REPORT.md`
