# Chess Federation — Architecture

## Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Backend | Python 3 / Flask | Lightweight; good chess library ecosystem |
| Database | SQLite via Flask-SQLAlchemy | Zero-config, file-based, portable |
| Chess logic | python-chess | Mature library; handles legal moves, PGN, FEN |
| Frontend | Jinja2 templates + vanilla JS + CSS | No build step; server-rendered |
| Board UI | Custom JS with Unicode pieces | Tap-to-move; mobile-friendly; no external deps |
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
├── requirements.txt           # Python dependencies
├── Procfile                   # Render/Heroku process definition
├── render.yaml                # Render.com service config
├── app/
│   ├── __init__.py            # Flask app factory
│   ├── config.py              # Environment-based configuration
│   ├── models.py              # SQLAlchemy models (User, Game, Move, WeeklySchedule)
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py            # Login / register / logout
│   │   ├── main.py            # Home, dashboard
│   │   ├── game.py            # Game board, moves API, state polling, resign
│   │   ├── players.py         # Player profiles, stats, match history
│   │   └── admin.py           # Match scheduling, forfeit checks
│   ├── services/
│   │   ├── __init__.py
│   │   ├── chess_engine.py    # ChessEngine wrapper (python-chess for v1)
│   │   ├── rating.py          # Federation rating (Elo + material modifier + tiers)
│   │   └── matchmaking.py     # Weekly pairing + forfeit detection
│   ├── templates/
│   │   ├── base.html          # Shared layout with nav
│   │   ├── home.html          # Landing page
│   │   ├── dashboard.html     # Weekly league overview
│   │   ├── game.html          # Chess board + move interface
│   │   ├── players.html       # Player listing
│   │   ├── profile.html       # Individual player profile
│   │   ├── history.html       # Match history (paginated)
│   │   └── auth/
│   │       ├── login.html
│   │       └── register.html
│   └── static/
│       ├── css/style.css      # Dark theme, responsive
│       └── js/
│           ├── board.js       # Chess board rendering + interaction
│           └── app.js         # Nav toggle, flash dismiss, deadline timer
├── data/
│   └── chess_federation.db    # SQLite database (created at runtime)
├── PROJECT.md
├── SPEC.md
├── ARCHITECTURE.md
├── DECISIONS.md
├── TASKS.md
└── AGENT_RULES.md
```

## Data Model (SQLite)

### Users
- id, username, password_hash, rating (default 800), wins, losses, draws,
  forfeits, is_active_player, created_at

### Games
- id, white_id, black_id, week_number, season, status (pending/active/
  completed/forfeited), result, result_type, pgn, fen_current, fen_final,
  material_white, material_black, rating_change_white, rating_change_black,
  current_turn, move_count, rule_snapshot, started_at, completed_at, deadline

### Moves
- id, game_id, move_number, color, move_san, move_uci, fen_after, timestamp

### WeeklySchedule
- id, week_number, season, power_position_holder_id, rule_declaration,
  created_at

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
