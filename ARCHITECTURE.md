# Chess Federation — Architecture

## Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Backend | Python 3 / Flask | Lightweight; good chess library ecosystem |
| Database | SQLite via Flask-SQLAlchemy | Zero-config, file-based, portable |
| Chess logic | python-chess | Mature library; handles legal moves, PGN, FEN |
| Frontend | Jinja2 templates + vanilla JS + CSS | No build step; server-rendered |
| Board UI | Chessground (vendored) | Drag-and-drop, SVG pieces, animations |
| Auth | Flask-Login + werkzeug password hashing | Simple session-based auth |
| Deployment | Render.com free tier | Auto-deploy from GitHub; persistent disk for SQLite |

## Run Entrypoint

```
run.bat        (Windows — double-click to launch locally)
```

The run file:
1. Checks for Python
2. Creates/activates `.venv`
3. Installs dependencies from `requirements.txt`
4. Creates `data/` directory
5. Launches Flask dev server on port 5000

## Directory Layout

```
Chess Federation/
├── run.bat                    # Windows launch entrypoint
├── requirements.txt           # Python dependencies (pinned)
├── Procfile                   # Render/Heroku process definition
├── render.yaml                # Render.com service config
├── app/
│   ├── __init__.py            # Flask app factory + DB migrations
│   ├── config.py              # Environment-based configuration
│   ├── models.py              # SQLAlchemy models (16 tables)
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py            # Login / register / logout
│   │   ├── main.py            # Home, standings, archive, turn API
│   │   ├── game.py            # Game board, moves, practice, wagers
│   │   ├── players.py         # Player profiles, stats, match history
│   │   ├── admin.py           # Match scheduling, forfeit checks
│   │   ├── hall.py            # Chat room (reactions, replies, images)
│   │   ├── decree.py          # Power Position decree submission
│   │   ├── challenge.py       # Casual match challenge system
│   │   ├── crypt.py           # The Crypt solo wave defense mode
│   │   └── four_player.py     # The Reckoning 4-player mode
│   ├── services/
│   │   ├── __init__.py
│   │   ├── chess_engine.py    # ChessEngine wrapper (python-chess)
│   │   ├── rating.py          # Federation rating (Elo + material + tiers)
│   │   ├── matchmaking.py     # Weekly all-play-all pairing + forfeit
│   │   ├── power.py           # Power Position rotation logic
│   │   ├── material.py        # Season material stat tracking
│   │   ├── weekly_rule.py     # Custom rule engine (decree modifications)
│   │   ├── sequences.py       # Named openings/variations system
│   │   ├── collectibles.py    # Post-match game-analysis collectible triggers
│   │   ├── collectibles_catalog.py  # Master catalog (170 items, 12 collections)
│   │   ├── collectibles_engagement.py  # Engagement/milestone triggers
│   │   ├── enoch.py           # Enoch NPC core logic + mood system
│   │   ├── enoch_ai.py        # Enoch chess AI (minimax, 3 difficulty tiers)
│   │   ├── enoch_chat.py      # Chat engine, quirks, announcements
│   │   ├── dialogue.py        # Enoch general + chat dialogue pools
│   │   ├── practice_dialogue.py  # Practice match dialogue pools
│   │   ├── wager_dialogue.py  # Wager system dialogue pools
│   │   ├── login_greetings.py # Per-user custom login greetings
│   │   ├── crypt_logic.py     # Crypt wave generation, cascade AI
│   │   ├── crypt_dialogue.py  # Crypt-specific dialogue (~100+ lines)
│   │   ├── four_player_engine.py  # 4-player chess engine (14x14 board)
│   │   └── four_player_ai.py  # Reckoning AI + commentary
│   ├── templates/
│   │   ├── base.html          # Shared layout with nav + unread badge
│   │   ├── macros.html        # Jinja2 reusable macros (avatar helper)
│   │   ├── home.html          # Landing page (Enoch welcome letter)
│   │   ├── standings.html     # Dashboard: games, chat, practice, decrees
│   │   ├── game.html          # Chess board + move interface
│   │   ├── players.html       # Player listing
│   │   ├── profile.html       # Player profile + collectible drawer
│   │   ├── archive.html       # Season archive
│   │   ├── chronicle.html     # Match chronicle/history
│   │   ├── hall.html          # Federation Hall (full chat room)
│   │   ├── decree.html        # Power Position decree page
│   │   ├── scrapbook.html     # Enoch practice match history
│   │   ├── account.html       # Account settings
│   │   ├── crypt.html         # The Crypt (solo wave defense)
│   │   ├── four_player.html   # The Reckoning (4-player board)
│   │   └── auth/
│   │       ├── login.html
│   │       └── register.html
│   └── static/
│       ├── css/
│       │   ├── style.css          # Dark theme, responsive
│       │   └── chessground-theme.css  # Chessground board theme
│       ├── js/
│       │   ├── board.js           # Chess board controller (Chessground)
│       │   ├── app.js             # Nav, notifications, timers, badge
│       │   ├── hall.js            # Federation Hall chat JS
│       │   ├── crypt.js           # Crypt mode UI, audio, cascade logic
│       │   ├── four_player.js     # Reckoning board, timer, zombie intro
│       │   ├── audio-cache.js     # Service Worker audio cache
│       │   └── chessground.min.js # Vendored Chessground library
│       ├── audio/
│       │   ├── chess/             # Move, capture, win/lose sounds
│       │   ├── crypt/             # Ambient loop, thunder, cascade music
│       │   ├── enoch/             # ~2,789 ElevenLabs TTS mp3s + manifest
│       │   └── reckoning/         # Zombie horn sounds
│       └── img/
│           └── enoch.png          # Enoch avatar image
├── data/
│   └── chess_federation.db    # SQLite database (created at runtime)
├── PROJECT.md
├── SPEC.md
├── ARCHITECTURE.md
├── DECISIONS.md
├── TASKS.md
├── README.md
└── AGENT_RULES.md
```

## Data Model (SQLite — 16 tables)

### User
- id, username, password_hash, rating (default 200), wins, losses, draws,
  forfeits, avatar_filename, is_active_player, can_name_openings, bio,
  is_bot, enoch_points, enoch_wager_wins/losses/draws, last_seen, created_at

### Game
- id, white_id, black_id, week_number, season, status, result, result_type,
  pgn, fen_current, fen_final, material_white, material_black,
  rating_change_white, rating_change_black, current_turn, move_count,
  rule_snapshot, custom_rule_name, game_type (weekly/casual/practice/wager),
  power_holder_id, is_practice, started_at, completed_at, deadline

### Move
- id, game_id, move_number, color, move_san, move_uci, fen_after, timestamp

### WeeklySchedule
- id, week_number, season, power_position_holder_id, rule_declaration,
  created_at

### Challenge
- id, sender_id, receiver_id, game_id, status (pending/accepted/declined),
  created_at

### ChatMessage
- id, user_id, content, is_bot, bot_name, reply_to_id, image_filename,
  edited, timestamp

### ChatReaction
- id, message_id, user_id, emoji, created_at
- UNIQUE(message_id, user_id, emoji)

### PowerRotationOrder
- id, user_id, position

### Commendation
- id, game_id, author_id, subject_id, kind (commend/condemn), text,
  created_at

### NamedSequence
- id, creator_id, name, moves, half_moves, category, created_at

### SeasonMaterialStat
- id, user_id, season_year, season_month, total_diff, games_count, avg_diff

### PlayerCollectible
- id, user_id, item_id, game_id, acquired_at

### EnochWager
- id, user_id, game_id, mood, wager_amount, is_anomaly, result,
  points_change, created_at

### CryptGame
- id, user_id, wave, phase, score, gold, fen_current, inventory,
  rating_entry, rating_result, cashed_out, cascade_tick, cascade_max_ticks,
  created_at, completed_at

### FourPlayerGame
- id, south_id, west_id, north_id, east_id, board_state, status,
  eliminated, result_order, scores, week_number, season, move_count,
  current_turn, turn_started_at, created_at, started_at, completed_at,
  deadline

### FourPlayerMove
- id, game_id, move_number, color, move_str, captured, commentary, timestamp

## Deployment

### Local Dev
`run.bat` → Flask dev server on `localhost:5000`

### Production (Render.com)
1. Push to GitHub
2. Connect repo on Render.com
3. `render.yaml` auto-configures: web service, persistent disk for SQLite,
   generated SECRET_KEY
4. Gunicorn serves the app via `Procfile`

### Alternative: PythonAnywhere
Free tier with persistent filesystem. Upload code, set WSGI config to
`from app import create_app; application = create_app()`.

## Chess Engine Abstraction (v1 → v2 path)

v1 uses `python-chess` directly for standard chess. The `chess_engine.py`
service wraps it behind an interface:

```
ChessEngine
  .new_game() → starting FEN
  .get_legal_moves(fen) → [{uci, san, from, to, promotion}]
  .make_move(fen, uci) → {fen, san, move_number, turn}
  .is_game_over(fen) → (bool, result_type)
  .get_material(fen) → {white: int, black: int}
  .get_board_state(fen) → {pieces, turn, in_check, fen}
  .build_pgn(moves, game) → PGN string
```

v2 replaces the internals with a configurable rules engine while keeping
the same interface.
