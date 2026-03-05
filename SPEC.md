# Specification

## Features

### Public Pages

1. **Home** (`/`) — Atmospheric landing page introducing the Federation.
2. **Sacred Hierarchy** (`/hierarchy`) — Interactive vertical display of all 10 ranks with player positions.
3. **Players** (`/players`) — Card grid of all Federation members with links to profiles.
4. **Player Profile** (`/player/<id>`) — Individual bio, rank badge, win/loss record, game history.
5. **Chronicles** (`/chronicles`) — Full lore rendered as a scrollable parchment document.

### Admin Panel

6. **Admin** (`/admin`) — Password-protected page for:
   - Recording match results (winner's rank +1, loser's rank −1, capped 1–10).
   - Editing player bios.
   - Adding / removing players.

### Ranking Rules

- Win → rank increases by 1 (max 10).
- Loss → rank decreases by 1 (min 1).
- Matches are recorded through the admin panel.

### Data

- All data stored in `data/players.json`.
- Players have: id, name, title, rank, wins, losses, bio, status, portrait filename.
- Games have: id, white, black, result, pgn, lore_title, lore_description.

### Visual

- Old-world parchment aesthetic evoking a 1500s secret society.
- Responsive — works on both desktop and mobile.
- Serif typography (Cinzel headings, EB Garamond body).
