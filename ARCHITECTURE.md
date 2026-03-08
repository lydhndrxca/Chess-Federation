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
│   ├── models.py              # SQLAlchemy models (11 tables)
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py            # Login / register / logout
│   │   ├── main.py            # Home, standings dashboard, season archive
│   │   ├── game.py            # Game board, moves, practice, wagers
│   │   ├── players.py         # Player profiles, stats, match history
│   │   ├── admin.py           # Match scheduling, forfeit checks
│   │   ├── hall.py            # Federation Hall chat room
│   │   └── decree.py          # Power Position decree submission
│   ├── services/
│   │   ├── __init__.py
│   │   ├── chess_engine.py    # ChessEngine wrapper (python-chess)
│   │   ├── rating.py          # Federation rating (Elo + material + tiers)
│   │   ├── matchmaking.py     # Weekly all-play-all pairing + forfeit
│   │   ├── power.py           # Power Position rotation logic
│   │   ├── material.py        # Season material stat tracking
│   │   ├── sequences.py       # Named openings/variations system
│   │   ├── collectibles.py    # Post-match game-analysis collectible triggers
│   │   ├── collectibles_catalog.py  # Master catalog (170 items, 12 collections)
│   │   ├── collectibles_engagement.py  # Engagement/milestone triggers
│   │   ├── enoch.py           # Enoch NPC core logic
│   │   ├── enoch_ai.py        # Enoch chess AI + mood + wager generation
│   │   ├── enoch_chat.py      # Enoch chat engine + lurk detection
│   │   ├── dialogue.py        # Enoch general chat dialogue pools
│   │   ├── practice_dialogue.py  # Practice match dialogue pools
│   │   └── wager_dialogue.py  # Wager system dialogue pools
│   ├── templates/
│   │   ├── base.html          # Shared layout with nav
│   │   ├── macros.html        # Jinja2 reusable macros
│   │   ├── home.html          # Landing page (Enoch greeting)
│   │   ├── standings.html     # Weekly standings + matchups + practice
│   │   ├── game.html          # Chess board + move interface
│   │   ├── players.html       # Player listing
│   │   ├── profile.html       # Player profile + collectible drawer
│   │   ├── archive.html       # Season archive
│   │   ├── chronicle.html     # Match chronicle/history
│   │   ├── hall.html          # Federation Hall chat room
│   │   ├── decree.html        # Power Position decree page
│   │   ├── scrapbook.html     # Enoch practice match history
│   │   ├── account.html       # Account settings
│   │   └── auth/
│   │       ├── login.html
│   │       └── register.html
│   └── static/
│       ├── css/
│       │   ├── style.css          # Dark theme, responsive
│       │   └── chessground-theme.css  # Chessground board theme
│       ├── js/
│       │   ├── board.js           # Chess board controller (Chessground)
│       │   ├── app.js             # Nav, flash dismiss, timers
│       │   ├── hall.js            # Federation Hall chat JS
│       │   └── chessground.min.js # Vendored Chessground library
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

## Data Model (SQLite — 11 tables)

### User
- id, username, password_hash, rating (default 200), wins, losses, draws,
  forfeits, avatar_filename, is_active_player, can_name_openings, bio,
  is_bot, enoch_points, enoch_wager_wins/losses/draws, created_at

### Game
- id, white_id, black_id, week_number, season, status, result, result_type,
  pgn, fen_current, fen_final, material_white, material_black,
  rating_change_white, rating_change_black, current_turn, move_count,
  rule_snapshot, power_holder_id, is_practice, started_at, completed_at,
  deadline

### Move
- id, game_id, move_number, color, move_san, move_uci, fen_after, timestamp

### WeeklySchedule
- id, week_number, season, power_position_holder_id, rule_declaration,
  created_at

### ChatMessage
- id, user_id, content, is_bot, bot_name, timestamp

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
