# Chess Federation

**Status:** Active development — well beyond MVP.

## Overview

A private, link-access online correspondence chess platform for a small group
of players. Features weekly scheduled all-play-all matches, persistent
federation ratings with a custom 10-tier ceremonial ranking system, a rotating
Power Position authority that can modify game rules, a fully realized NPC
opponent (Enoch) with mood-based AI and a wager system, 170 collectible items,
a Federation Hall chat room, named opening/variation discovery, and post-match
commendations.

## Current Phase

Core systems are implemented and live:
- Accounts, weekly matchmaking, correspondence play, interactive board
- Ratings with material modifier, 10-tier ceremonial hierarchy
- Power Position rotation with weekly decrees
- Enoch NPC: practice mode, mood system (Chill/Annoyed/Angry), daily wagers
- 170 collectible items across 12 collections (game-analysis + engagement triggers)
- Federation Hall chat room with Enoch lurking
- Named openings/variations system
- Season archive, player profiles, commendations/condemnations

## Stack

Python 3 / Flask / SQLite / Jinja2 + vanilla JS / Chessground

## Run

```
double-click run.bat
```

## Deploy

Push to GitHub, connect to Render.com. Uses `render.yaml` for auto-config.
