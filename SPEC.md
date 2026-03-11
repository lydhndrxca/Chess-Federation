# Chess Federation — Specification

## Product Overview

A private, link-access online correspondence chess platform for a small group
of players. Users create simple accounts, play one scheduled match per week,
and complete games asynchronously within a 7-day deadline. Every match is
stored permanently with notation, result, stats, and rating updates. Players
have persistent profiles, federation ratings, and custom 10-tier rank titles.
A rotating "Power Position" gives one player per week the authority to
introduce a new rule or game modification, allowing the federation to
gradually evolve from standard chess into a custom ruleset over time.

---

## 1. Access Model

- Private link-access only (not public, not commercial)
- Anyone with the link can reach the site
- Users create an account with a username and password
- Security: basic account separation, not enterprise-grade
- Each user owns: identity, active games, history, rating/stats
- Deployment: GitHub-based, free hosting, generic/free URL

## 2. User Accounts

- Username + password registration
- Login / logout
- Session-based authentication
- Each account has:
  - unique username
  - federation rating (numeric)
  - federation tier (derived from rating)
  - win / loss / draw / forfeit counts
  - match history
  - active game status

## 3. Match Structure — Weekly Federation Cycle

- Every active federation player is matched against every other player
  each week (all-play-all round-robin)
- Each match is a turn-based correspondence game (asynchronous)
- Weekly match window: Sunday 5 PM CST to next Sunday 5 PM CST
- A player opens the game, makes a move, state saves automatically
- Opponent is then up next
- Game continues until: checkmate, resignation, draw, timeout/forfeit,
  or custom rule outcome (future)

### Deadline & Forfeit

- Match must finish within the week
- If not finished by deadline: the player who failed to move forfeits
- Opponent awarded the win
- No extra material modifier on forfeit results

## 4. Dashboard / League View

Weekly overview page showing:

- All active federation players
- Current week number or season/week label
- Who is matched against whom
- Game status per match: not started / in progress / completed / forfeited
- Whose turn it is (per active game)
- Deadline remaining
- Once completed: result, rating change, link to game record

## 5. Match History

Every game permanently recorded with:

- Players involved
- Date / week
- Winner / loser / draw
- Full move notation (PGN or equivalent)
- Result type: checkmate, resignation, draw, timeout/forfeit, custom
- Final material state
- Rating changes for both players
- Active weekly rule / variant info (snapshot of rule set in effect)

## 6. Player Profiles & Stats

Each player has a persistent federation profile:

- Username
- Federation rating (numeric)
- Federation tier name
- Wins / losses / draws / forfeits
- Completed match count
- Active game status
- Full match history
- Win streak / loss streak (optional)
- Total material differential over lifetime (optional)
- Current season record (optional)

## 7. Rating System

Custom Chess Federation rating, inspired by Elo but modified.

### Scale

- 10-tier system
- Tier 1 starts around 200
- Tier 10 tops out around 4000
- Continuous numeric rating maps to one of 10 named federation tiers

### Rating Formula

```
Rating change = base result value
              + matchup expectation adjustment
              + material modifier
```

- **Base result**: win / loss / draw
- **Expectation adjustment**: stronger player gains less for beating weaker;
  weaker player gains more for upset
- **Material modifier**: contextual bonus/penalty based on final material
  imbalance

### Material Modifier Logic

| Outcome | Material state | Effect |
|---------|---------------|--------|
| Win while behind in material | More impressive win | bonus |
| Lose while ahead in material | Worse loss | penalty |
| Win while ahead in material | Expected outcome | no extra bonus |
| Lose while behind in material | Expected outcome | slight softening |
| Forfeit (either side) | N/A | no material modifier |

**Balancing principle:** Material is a modifier, not the main determinant.
Players must not be able to game ratings by farming material instead of
playing for mate.

## 8. Federation Tiers

10 named tiers mapped to rating bands.

- Custom ceremonial / federation-specific names (not standard chess titles)
- Exact names and rating boundaries to be defined by user
- Placeholder structure:
  - Tier 1: ~200–399
  - Tier 2: ~400–699
  - Tier 3: ~700–999
  - Tier 4: ~1000–1399
  - Tier 5: ~1400–1799
  - Tier 6: ~1800–2199
  - Tier 7: ~2200–2599
  - Tier 8: ~2600–2999
  - Tier 9: ~3000–3499
  - Tier 10: ~3500–4000

## 9. Power Position System (v2+)

### Core Rule

Each week, one federation member holds the Power Position by rotation.
That player may introduce one change to the game for that week.

### Possible Changes

- Add a new custom chess piece
- Change how an existing piece moves
- Change board dimensions
- Change win conditions
- Change starting layouts
- Add special rules
- Alter movement behavior
- Introduce novel mechanics

### Rotation

- Power Position rotates weekly to the next player in federation order
- System tracks: current holder, declared rule, start/end dates, full archive

### Architecture Implication

The game engine must be designed with variant support from the start.
Even if v1 is standard chess only, the architecture must anticipate:
configurable board size, configurable pieces, configurable movement rules,
configurable setup, configurable per-week rule packages.

## 10. Chess Engine Requirements

### v1 (MVP)

- Standard 8×8 chess with all standard rules
- Legal move validation
- Check / checkmate / stalemate detection
- En passant, castling, pawn promotion
- Move notation (algebraic)
- Board state persistence (save/load per move)

### v2+ (Variant Support)

Data-driven rules engine separating:

- Board representation (configurable dimensions)
- Piece definitions (configurable movement patterns)
- Move rules (configurable legality)
- Match rules (configurable win/draw conditions)
- Weekly rule overrides (Power Position declarations)

## 11. Game State & Move Persistence

- Every move: validate legality → update board → save immediately →
  update notation → switch turn → update deadline state
- Reliable save/load for asynchronous play
- No data loss on disconnect or browser close
- Move history preserved for every game

## 12. UI / UX Requirements

### Visual

- Modern, clean, polished but not overbuilt
- Attractive board and pieces
- Responsive layout: desktop and mobile

### Mobile (critical)

- Clean board scaling
- Readable pieces
- Tap-to-select / tap-to-move
- Visible: move history, whose turn, time remaining
- Easy switching: board / standings / history / profile / weekly rule

### UX Flow

- Easy login
- Immediately see current match
- Easy to make a move
- Moves auto-save
- Clear turn status and deadline visibility
- Easy access to standings, history, rules

## 13. Deployment

- GitHub-based development
- Free-tier hosting (auto-deploy from repo)
- Generic/free URL
- Lightweight, low-maintenance

---

## MVP Scope

### Version 1 (build first)

- User accounts (register / login)
- Weekly match scheduling with auto-pairing
- Standard chess gameplay (asynchronous, correspondence-style)
- Auto-save on every move
- 7-day deadline with forfeit on timeout
- Result recording with full notation
- Federation rating system with material modifier
- 10-tier ranking display
- Weekly dashboard with match statuses
- Player profiles with stats and history
- Mobile-responsive UI

### Version 2+ (build later)

- Variant-capable rules engine
- Custom pieces / board changes / federation mutations

## 14. Casual Matches

- Players can challenge each other to normal chess games outside the weekly cycle
- No weekly limit; unlimited casual games
- Casual games count toward standard ratings and stats
- Only one active casual game allowed per player pair
- Color assignment randomized with a running tally for fairness
- Challenge flow: send challenge → opponent accepts or declines
- Listed below the weekly "Game of the Week" on the standings page

## 15. The Crypt (Solo Wave Defense)

- Solo mode: player defends against waves of AI-controlled enemy pieces
- Player starts with limited pieces and earns gold by capturing enemies
- Shop system between waves: buy Queen, Rook, Bishop, Knight, Pawn
- Waves increase in difficulty (more enemies, stronger AI per wave)
- Cascade mode: every 3rd wave (3, 6, 9, ...) is a real-time survival round
  - Enemies auto-move toward the player's king every ~1.5 seconds
  - New enemies continuously spawn from back ranks
  - Player moves in real-time without waiting for turns
  - Player receives bonus pieces (Queen, Knight, Bishop) before cascade
- King-hunting AI prioritizes the player's king during cascade
- Dark crypt theme with ambient horror music, lightning/thunder effects
- Dedicated cascade music track with crossfade audio looping
- ~100+ Enoch dialogue lines specific to crypt events
- High scores tracked per player and visible on profiles

## 16. The Reckoning (4-Player Mode)

- Custom 14x14 board with 4 players (south, west, north, east)
- Enoch occupies the north seat as an AI opponent
- Zombie pawns: 9 green pawns spawn in the center, move one square any direction after each player's turn
- 4-hour turn timer with live countdown next to active player's name
- If a player is idle for 4 hours, Enoch auto-moves a random legal piece for them
- 5 voiced taunt lines play when the idle player returns
- Dying horn sounds accompany the zombie intro animation
- Elimination: when a player's king is captured, they are removed
- Last player standing wins

## 17. Chat System (Federation Hall)

- Persistent chat room accessible from the navigation and a compact widget on the standings page
- Emoji reactions: hold/long-press a message to react (heart, laugh, shocked, sad, angry, thumbs up, or custom)
- Reply threading: hold a message to reply directly to it
- Edit and delete own messages via long-press context menu
- Image posting: upload via file picker or paste
- Long messages (>4 lines) auto-collapse with expand/collapse toggle
- Compact chat on the home page mirrors all features of the full chat hall
- Enoch chat quirks:
  - Late-night murmurings (12 AM–4 AM CT)
  - Rare daytime oddities (e.g., accidental DM followed by save-face message)
  - 99 Theses musings (~30% chance during daytime quirks)
  - @Enoch slash commands

## 18. Web Push Notifications

- Browser notification prompt (Enoch-themed modal with randomized in-character lines)
- Notifications fire when the browser tab is not focused:
  - Turn alerts: "Your turn! It's your move against [opponent]"
  - Chat mentions: "You were mentioned in the Hall"
- Preference stored in localStorage; user can dismiss or allow

## 19. Board Enhancements

- Last-move animation: when returning to a game, the opponent's most recent move animates on the board
- Decree board theme: weekly custom-rule games have a unique iridescent board (cream/purple squares, rainbow glow border)
- Move destination highlights: thick white outlines on legal move squares
- Move confirmation bar: confirm or cancel a move before committing (positioned for mobile visibility)
- Chess move sounds for captures, moves, check, win, and loss

## 20. Power Position System (Implemented)

- Weekly rotation among active players
- Decree holder can submit a custom rule at any time before the deadline
- Custom rules modify piece behavior (e.g., extended knight movement: 3 forward, 2 sideways)
- Rules apply only to weekly PvP games (not Enoch practice or casual)
- Rule snapshot stored with each game for historical accuracy
- 25 custom Enoch commentary lines generated per active rule
