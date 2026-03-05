# Architecture

## Stack

- **Language**: Python 3
- **Framework**: Flask
- **Templating**: Jinja2
- **Data store**: JSON file (`data/players.json`)
- **Frontend**: Vanilla HTML / CSS / JS (no build step)

## Run Command

```
python run.py
```

`run.py` creates a local virtual environment (if needed), installs dependencies from `requirements.txt`, and launches the Flask development server on `http://localhost:5000`.

## Directory Layout

```
Chess Federation/
  run.py                    # Entrypoint
  requirements.txt          # Python dependencies
  app/
    __init__.py             # Flask app factory
    routes.py               # All page and admin routes
    auth.py                 # Admin authentication helpers
    data.py                 # JSON read/write helpers
    templates/
      base.html             # Shared layout
      index.html            # Home
      hierarchy.html        # Rank display
      players.html          # Player grid
      player_detail.html    # Player profile
      chronicles.html       # Lore
      admin.html            # Admin panel
    static/
      css/style.css         # All styles
      js/main.js            # Client-side interactions
      img/                  # Images and textures
  data/
    players.json            # Player and game data
```

## Key Modules

| Module | Responsibility |
|--------|---------------|
| `app/__init__.py` | App factory, secret key, blueprint registration |
| `app/routes.py` | All Flask routes |
| `app/data.py` | Load / save `data/players.json` |
| `app/auth.py` | Admin login session management |
