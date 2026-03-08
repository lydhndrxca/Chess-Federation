"""Enoch AI — a moody chess engine whose strength shifts throughout the day.

Moods (rotate every ~4-6 hours, deterministically):
  Chill    → ~500 Elo   — distracted, clumsy, blunder-heavy
  Annoyed  → ~800 Elo   — sharper, fewer blunders, still sloppy
  Angry    → ~1200 Elo  — focused, tactical, genuinely dangerous
"""

import hashlib
import random
from datetime import datetime, timezone

import chess


# ── Mood System ─────────────────────────────────────────────────

MOODS = [
    {'key': 'chill',   'label': 'Chill',   'rating': 500,  'icon': '\U0001f56f\ufe0f'},
    {'key': 'annoyed', 'label': 'Annoyed', 'rating': 800,  'icon': '\U0001f610'},
    {'key': 'angry',   'label': 'Angry',   'rating': 1200, 'icon': '\U0001f525'},
]

MOOD_BY_KEY = {m['key']: m for m in MOODS}

def get_current_mood():
    """Return the current Enoch mood dict based on time of day.

    The day is split into 6 segments (~4 hours each). A daily seed
    creates a shuffled mood schedule that guarantees at least one
    appearance of each mood and changes a few times throughout the day.
    """
    now = datetime.now(timezone.utc)
    day_key = now.strftime('%Y-%m-%d')
    segment = now.hour // 4

    seed = int(hashlib.md5(f'enoch-mood-{day_key}'.encode()).hexdigest(), 16)
    rng = random.Random(seed)
    schedule = list(MOODS) * 2
    rng.shuffle(schedule)
    schedule = schedule[:6]

    return schedule[segment]


# ── Wager System ─────────────────────────────────────────────────

WAGER_BANDS = {
    'chill':   {'min': 5,  'max': 10},
    'annoyed': {'min': 10, 'max': 15},
    'angry':   {'min': 15, 'max': 25},
}

ANOMALY_CHANCE = 0.01
ANOMALY_WAGER_RANGE = (30, 50)
ANOMALY_ELO = 1500


def generate_wager_offer():
    """Generate today's wager parameters based on current mood.

    Returns a dict:
        mood_key, mood_label, mood_icon, elo, wager, is_anomaly, dialogue
    """
    from app.services.wager_dialogue import WAGER_OFFER_BY_MOOD

    mood = get_current_mood()

    is_anomaly = random.random() < ANOMALY_CHANCE
    if is_anomaly:
        wager = random.randint(*ANOMALY_WAGER_RANGE)
        elo = ANOMALY_ELO
        pool = WAGER_OFFER_BY_MOOD['anomaly']
        mood_label = 'Unhinged'
        mood_icon = '\U0001f480'
        mood_key = mood['key']
    else:
        band = WAGER_BANDS[mood['key']]
        wager = random.randint(band['min'], band['max'])
        elo = mood['rating']
        pool = WAGER_OFFER_BY_MOOD[mood['key']]
        mood_label = mood['label']
        mood_icon = mood['icon']
        mood_key = mood['key']

    line = random.choice(pool).replace('[Wager]', str(wager))

    return {
        'mood_key': mood_key,
        'mood_label': mood_label,
        'mood_icon': mood_icon,
        'elo': elo,
        'wager': wager,
        'is_anomaly': is_anomaly,
        'dialogue': line,
    }


# ── Mood-dependent AI parameters ────────────────────────────────

_MOOD_PARAMS = {
    'chill': {
        'blunder_early': 0.15, 'blunder_mid': 0.35, 'blunder_late': 0.25,
        'sharp_chance': 0.08,
        'noise_sigma': 80,
        'top_n': 5,
        'depth': 1,
    },
    'annoyed': {
        'blunder_early': 0.06, 'blunder_mid': 0.15, 'blunder_late': 0.10,
        'sharp_chance': 0.20,
        'noise_sigma': 45,
        'top_n': 4,
        'depth': 1,
    },
    'angry': {
        'blunder_early': 0.02, 'blunder_mid': 0.05, 'blunder_late': 0.04,
        'sharp_chance': 0.40,
        'noise_sigma': 20,
        'top_n': 3,
        'depth': 2,
    },
}


PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 0,
}

CENTER_SQUARES = {chess.D4, chess.D5, chess.E4, chess.E5}
EXTENDED_CENTER = {chess.C3, chess.C4, chess.C5, chess.C6,
                   chess.D3, chess.D4, chess.D5, chess.D6,
                   chess.E3, chess.E4, chess.E5, chess.E6,
                   chess.F3, chess.F4, chess.F5, chess.F6}


def _material(board, color):
    total = 0
    for sq, piece in board.piece_map().items():
        if piece.color == color:
            total += PIECE_VALUES.get(piece.piece_type, 0)
    return total


def _evaluate_board(board, engine_color):
    if board.is_checkmate():
        return -99999 if board.turn == engine_color else 99999
    if board.is_stalemate() or board.is_insufficient_material():
        return 0

    my_mat = _material(board, engine_color)
    opp_mat = _material(board, not engine_color)
    score = my_mat - opp_mat

    for sq in CENTER_SQUARES:
        p = board.piece_at(sq)
        if p and p.color == engine_color:
            score += 15
        elif p and p.color != engine_color:
            score -= 10

    for sq in EXTENDED_CENTER:
        if board.is_attacked_by(engine_color, sq):
            score += 3

    if board.has_castling_rights(engine_color):
        score += 20

    return score


def _score_move(board, move, engine_color, noise_sigma=80, depth=1):
    """Score a single move for Enoch's selection heuristic."""
    score = 0.0

    piece = board.piece_at(move.from_square)
    if not piece:
        return random.uniform(-50, 50)

    captured = board.piece_at(move.to_square)
    if board.is_en_passant(move):
        score += 80
    elif captured:
        score += PIECE_VALUES.get(captured.piece_type, 0) - PIECE_VALUES.get(piece.piece_type, 0) * 0.1

    if move.to_square in CENTER_SQUARES and piece.piece_type in (chess.PAWN, chess.KNIGHT):
        score += 25

    if piece.piece_type in (chess.KNIGHT, chess.BISHOP) and chess.square_rank(move.from_square) in (0, 7):
        score += 30

    if move.promotion:
        score += PIECE_VALUES.get(move.promotion, 0) - 100

    board.push(move)

    if board.is_checkmate():
        score += 50000
    elif board.is_check():
        score += 40

    if depth >= 2 and not board.is_game_over():
        best_reply = -99999
        for reply in board.legal_moves:
            board.push(reply)
            val = _evaluate_board(board, engine_color)
            board.pop()
            opp_val = -val
            if opp_val > best_reply:
                best_reply = opp_val
        score -= best_reply * 0.3

    board.pop()

    score += random.gauss(0, noise_sigma)

    return score


def _is_blunder_turn(move_number, params):
    if move_number < 6:
        return random.random() < params['blunder_early']
    elif move_number < 20:
        return random.random() < params['blunder_mid']
    else:
        return random.random() < params['blunder_late']


def _is_sharp_turn(params):
    return random.random() < params['sharp_chance']


def pick_move(fen, mood_key=None):
    """Select Enoch's next move given a FEN string.

    mood_key: 'chill', 'annoyed', or 'angry' (defaults to current mood).

    Returns (chess.Move or None, move_mood_str).
    move_mood_str is one of: 'blunder', 'sharp', 'normal', 'capture', 'check', 'checkmate', 'none'
    """
    if mood_key is None:
        mood_key = get_current_mood()['key']
    params = _MOOD_PARAMS[mood_key]

    board = chess.Board(fen)
    legal = list(board.legal_moves)
    if not legal:
        return None, 'none'

    if len(legal) == 1:
        board.push(legal[0])
        mv_mood = 'check' if board.is_check() else 'normal'
        board.pop()
        return legal[0], mv_mood

    engine_color = board.turn
    move_number = board.fullmove_number

    if _is_blunder_turn(move_number, params) and not _is_sharp_turn(params):
        chosen = random.choice(legal)

        is_hanging = False
        board.push(chosen)
        if board.is_attacked_by(not engine_color, chosen.to_square):
            piece = board.piece_at(chosen.to_square)
            if piece and PIECE_VALUES.get(piece.piece_type, 0) >= 300:
                is_hanging = True
        board.pop()

        if is_hanging and random.random() < 0.6:
            return chosen, 'blunder'
        else:
            return chosen, 'blunder'

    scored = []
    for move in legal:
        s = _score_move(board, move, engine_color,
                        noise_sigma=params['noise_sigma'],
                        depth=params['depth'])
        scored.append((s, move))

    scored.sort(key=lambda x: -x[0])

    if _is_sharp_turn(params):
        chosen = scored[0][1]
        mv_mood = 'sharp'
    else:
        top_n = min(params['top_n'], len(scored))
        weights = [max(1, 100 - i * 25) for i in range(top_n)]
        chosen = random.choices([s[1] for s in scored[:top_n]], weights=weights, k=1)[0]
        mv_mood = 'normal'

    is_cap = board.is_capture(chosen)
    board.push(chosen)
    if board.is_checkmate():
        mv_mood = 'checkmate'
    elif board.is_check():
        mv_mood = 'check'
    elif is_cap:
        mv_mood = 'capture'
    board.pop()

    return chosen, mv_mood


def get_practice_commentary(player_san, enoch_san, enoch_mood, board_fen,
                            move_number, game_over=False, result=None):
    """Select an appropriate Enoch commentary line for the practice match.

    Returns a string or None."""
    import random as _r
    from app.services.practice_dialogue import (
        PRACTICE_IDLE, PRACTICE_PLAYER_CAPTURES, PRACTICE_ENOCH_CAPTURES,
        PRACTICE_PLAYER_BLUNDERS, PRACTICE_ENOCH_BLUNDERS,
        PRACTICE_PLAYER_CHECKS, PRACTICE_ENOCH_CHECKS,
        PRACTICE_PLAYER_WINNING, PRACTICE_ENOCH_WINNING,
        PRACTICE_PLAYER_WINS, PRACTICE_ENOCH_WINS, PRACTICE_DRAW,
        PRACTICE_RARE_IDLE,
    )

    if game_over:
        if result == 'player_win':
            return _r.choice(PRACTICE_PLAYER_WINS)
        elif result == 'enoch_win':
            return _r.choice(PRACTICE_ENOCH_WINS)
        else:
            return _r.choice(PRACTICE_DRAW)

    if _r.random() < 0.01:
        return _r.choice(PRACTICE_RARE_IDLE)

    if enoch_mood == 'blunder':
        return _r.choice(PRACTICE_ENOCH_BLUNDERS)

    if enoch_mood == 'check':
        return _r.choice(PRACTICE_ENOCH_CHECKS)

    if enoch_mood == 'capture':
        return _r.choice(PRACTICE_ENOCH_CAPTURES)

    if player_san and 'x' in player_san:
        return _r.choice(PRACTICE_PLAYER_CAPTURES)

    if player_san and ('+' in player_san or '#' in player_san):
        return _r.choice(PRACTICE_PLAYER_CHECKS)

    try:
        board = chess.Board(board_fen)
        my_mat = _material(board, chess.BLACK)
        opp_mat = _material(board, chess.WHITE)
        diff = opp_mat - my_mat
        if diff > 400:
            if _r.random() < 0.4:
                return _r.choice(PRACTICE_PLAYER_WINNING)
        elif diff < -400:
            if _r.random() < 0.4:
                return _r.choice(PRACTICE_ENOCH_WINNING)
    except Exception:
        pass

    if _r.random() < 0.3:
        return _r.choice(PRACTICE_IDLE)

    return None
