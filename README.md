# Chess Federation

A private correspondence chess platform with a ceremonial 10-tier ranking
system, weekly all-play-all matches, a rotating Power Position authority,
and an NPC opponent named Enoch who lives in the sub-basement.

## Quick Start (Windows)

```
double-click run.bat
```

This creates a virtual environment, installs dependencies, and starts the
Flask dev server at [http://localhost:5000](http://localhost:5000).

## Quick Start (Manual)

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
mkdir data
python -c "from app import create_app; create_app().run(debug=True, port=5000)"
```

## Stack

| Layer | Tech |
|-------|------|
| Backend | Python 3 / Flask 3.1 |
| Database | SQLite via Flask-SQLAlchemy |
| Chess logic | python-chess |
| Frontend | Jinja2 + vanilla JS + CSS |
| Board | Chessground (vendored) |
| Auth | Flask-Login |
| Deploy | Render.com |

## Deploy

Push to GitHub → Render.com auto-deploys via `render.yaml`.

## Governance Docs

| Document | Purpose |
|----------|---------|
| `PROJECT.md` | Project status and overview |
| `SPEC.md` | Feature specification |
| `ARCHITECTURE.md` | Tech stack, directory layout, data model |
| `DECISIONS.md` | Architectural decision records |
| `TASKS.md` | Task tracking |
| `AGENT_RULES.md` | AI agent governance contract |
