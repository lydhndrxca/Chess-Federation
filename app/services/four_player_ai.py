"""Enoch AI for four-player chess (The Reckoning).

Mood-dependent strength (same mood system as 2-player):
  Chill   → mostly random moves, slight preference for captures
  Annoyed → capture-priority + basic material evaluation
  Angry   → 1-ply lookahead with material + activity heuristics
"""

import random

from app.services.four_player_engine import (
    get_legal_moves, make_move, get_material, get_piece_count,
    piece_color, piece_type, PIECE_VALUES, COLORS, color_prefix,
)
from app.services.enoch_ai import get_current_mood, MOOD_BY_KEY


_AI_PARAMS = {
    'chill':   {'capture_weight': 2, 'random_noise': 50, 'lookahead': False},
    'annoyed': {'capture_weight': 5, 'random_noise': 20, 'lookahead': False},
    'angry':   {'capture_weight': 8, 'random_noise': 8,  'lookahead': True},
}


def pick_reckoning_move(state, enoch_color, mood_key=None):
    """Choose a move for Enoch in a 4-player game.
    Returns (move_dict, commentary_line) or (None, None) if no legal moves."""
    if mood_key is None:
        mood_key = get_current_mood()['key']

    legal = get_legal_moves(state, enoch_color)
    if not legal:
        return None, None

    params = _AI_PARAMS.get(mood_key, _AI_PARAMS['chill'])
    board = state['board']

    scored = []
    for m in legal:
        score = random.uniform(0, params['random_noise'])
        tk = f"{m['to'][0]},{m['to'][1]}"
        target = board.get(tk)

        if target:
            cap_value = PIECE_VALUES.get(piece_type(target), 1)
            score += cap_value * params['capture_weight']
            if piece_type(target) == 'K':
                score += 100

        if m.get('promo'):
            score += PIECE_VALUES.get(m['promo'], 5) * 2

        if params['lookahead']:
            score += _evaluate_move(state, m, enoch_color)

        scored.append((score, m))

    scored.sort(key=lambda x: x[0], reverse=True)

    if mood_key == 'chill':
        pick = scored[0][1] if random.random() < 0.4 else random.choice(scored)[1]
    elif mood_key == 'annoyed':
        top_n = min(3, len(scored))
        pick = random.choice(scored[:top_n])[1]
    else:
        pick = scored[0][1]

    commentary = _pick_commentary(state, pick, enoch_color, board)
    return pick, commentary


def _evaluate_move(state, move, enoch_color):
    """Simple 1-ply lookahead: evaluate resulting position."""
    try:
        new_state, captured = make_move(
            state, move['from'][0], move['from'][1],
            move['to'][0], move['to'][1], move.get('promo')
        )
    except ValueError:
        return 0

    my_mat = get_material(new_state, enoch_color)
    threats = 0
    prefix = color_prefix(enoch_color)
    for c in COLORS:
        if c == enoch_color or c in new_state['eliminated']:
            continue
        opp_moves = get_legal_moves(new_state, c)
        for om in opp_moves:
            tk = f"{om['to'][0]},{om['to'][1]}"
            target = new_state['board'].get(tk)
            if target and target[0] == prefix:
                threats += PIECE_VALUES.get(piece_type(target), 1)

    return my_mat * 0.5 - threats * 0.3


def _pick_commentary(state, move, enoch_color, board):
    tk = f"{move['to'][0]},{move['to'][1]}"
    target = board.get(tk)

    if target and piece_type(target) == 'K':
        return random.choice(COMMENTARY['king_capture'])
    if target:
        return random.choice(COMMENTARY['enoch_captures'])
    return random.choice(COMMENTARY['general'])


COMMENTARY = {
    'game_start': [
        "Four chairs scrape across the stone. The Reckoning begins.",
        "I have lit all the candles. Sit down. No one leaves until there is a winner.",
        "The large table is ready. The spiders have already placed their bets.",
        "The damp is worse tonight. Good. It keeps you alert.",
        "I have sharpened all sixty-four… no, one hundred and twenty-eight edges. Sit.",
        "Welcome to the grand table. I have been waiting in the dark for all four of you.",
        "Four corners. Four heartbeats. I can hear them all from beneath the grate.",
        "The Reckoning table has not been used in some time. The wood remembers.",
    ],
    'enoch_captures': [
        "Mine now. I collect everything eventually.",
        "Another trinket for the drawer.",
        "The board grows thinner. My side does not.",
        "I heard the piece scream. You did not. That is the difference between us.",
        "Into the grate it goes. I will fish it out later.",
        "One fewer obstacle between me and your king.",
        "I add it to the pile. The pile grows warm.",
        "Your army shrinks. My ledger entry for you grows longer.",
        "A piece falls. The sub-basement echoes with its landing.",
        "I have taken what was yours. The ink dries on the receipt.",
    ],
    'player_captures': [
        "Blood on the board. How theatrical.",
        "A capture. The table shudders.",
        "You take from the board what you cannot keep in life.",
        "Noted. I have updated the ledger in damp ink.",
        "So you have teeth after all. Show me more.",
        "A clean strike. The wood remembers the impact.",
        "You devour each other while I watch from below. Continue.",
        "The captured piece rolls across the stone floor. I will retrieve it later.",
    ],
    'elimination': [
        "One fewer. The air clears slightly.",
        "Eliminated. I will sweep their remains into the grate.",
        "Their pieces go into the furnace. The warmth is… acceptable.",
        "Another seat empties. The wood still holds their warmth.",
        "The table loses a voice. Three remain. The silence is almost pleasant.",
        "Gone. I have already crossed their name from the ledger.",
    ],
    'enoch_eliminated': [
        "You have removed me from my own table. Bold. Recorded.",
        "I shall observe from the shadows now. Do not think I have gone.",
        "A temporary setback. The ledger remembers everything.",
        "Fine. I will watch from the grate. My notes will be thorough.",
    ],
    'enoch_wins': [
        "Was there ever any doubt? The sub-basement always wins.",
        "I remain. You do not. This is the natural order.",
        "The Reckoning is mine. Clean the table. Leave the candles.",
        "Four sat down. One walks away. That one is always me.",
        "The grand table belongs to Enoch. It always has.",
    ],
    'king_capture': [
        "The king falls. How delicious.",
        "I have taken your sovereign. The crown is mine now.",
        "A king, toppled. I will mount it on the wall.",
        "Regicide at the grand table. The spiders applaud.",
        "Your king kneels in the dust. The Reckoning claims another crown.",
    ],
    'general': [
        "Interesting. Very interesting. I have made a note.",
        "The board speaks to me in ways it does not speak to you.",
        "Four minds, four failures, one table.",
        "Do not rush. The Reckoning has no clock, only consequences.",
        "I can feel the tension through the floorboards.",
        "The candles flicker when you hesitate. I have trained them.",
        "Your breathing has changed. I hear everything down here.",
        "The spiders are restless. They smell a winner.",
        "Every move echoes in the sub-basement. I record the echoes too.",
        "The large board drinks the light. Be careful where you step.",
        "The walls are damp. The walls are always damp.",
        "I wonder which of you will break first. I have placed my own bet.",
        "Three humans and one Steward. The odds have never been in your favor.",
        "The cross-shaped board stretches in every direction. So does my patience. Barely.",
        "Someone is sweating. I can smell it through the iron grate.",
        "You move, and the sub-basement groans. Everything here is connected.",
        "One hundred and sixty squares. I have memorized every grain of every one.",
        "The candlelight makes your shadows fight before you do.",
        "Tick. Tick. Tick. That is not a clock. That is my quill on the parchment.",
        "Do not look at each other. Look at the board. The board is what matters.",
        "Four armies on a cross of stone. The metaphor writes itself.",
        "I keep a tally of hesitations. Yours is the longest so far.",
        "The grand table was built for exactly this. Ruin on four fronts.",
    ],
    'player_eliminated': [
        "And then there were fewer.",
        "The chair scrapes back. One less voice in the dark.",
        "Eliminated. The spiders will dismantle their corner.",
        "Another soul departs the sub-basement. The door does not open for them.",
        "Removed from the Reckoning. I will file their remains under 'miscellaneous.'",
    ],
}

