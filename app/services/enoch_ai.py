"""Enoch AI — a moody chess engine whose strength shifts throughout the day.

Moods (rotate every ~4-6 hours, deterministically):
  Chill    → ~500 Elo   — distracted, clumsy, blunder-heavy
  Annoyed  → ~800 Elo   — sharper, fewer blunders, still sloppy
  Angry    → ~1200 Elo  — focused, tactical, genuinely dangerous

Engine: minimax with alpha-beta pruning, piece-square tables, and
mood-dependent depth/noise/blunder rates calibrated against real Elo.
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
# depth: minimax plies; noise: centipawn gaussian noise added to eval;
# blunder_chance: probability of playing a random (bad) move;
# top_n: number of top moves to consider when not playing the absolute best.

_MOOD_PARAMS = {
    'chill': {
        'depth': 2,
        'noise': 120,
        'blunder_chance': 0.20,
        'top_n': 6,
    },
    'annoyed': {
        'depth': 3,
        'noise': 50,
        'blunder_chance': 0.06,
        'top_n': 3,
    },
    'angry': {
        'depth': 4,
        'noise': 15,
        'blunder_chance': 0.01,
        'top_n': 2,
    },
}


# ── Piece values (centipawns) ────────────────────────────────────

PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 20000,
}


# ── Piece-square tables (from White's perspective; mirrored for Black) ──
# Values in centipawns, added to piece value for positional evaluation.

_PST_PAWN = [
     0,  0,  0,  0,  0,  0,  0,  0,
    50, 50, 50, 50, 50, 50, 50, 50,
    10, 10, 20, 30, 30, 20, 10, 10,
     5,  5, 10, 25, 25, 10,  5,  5,
     0,  0,  0, 20, 20,  0,  0,  0,
     5, -5,-10,  0,  0,-10, -5,  5,
     5, 10, 10,-20,-20, 10, 10,  5,
     0,  0,  0,  0,  0,  0,  0,  0,
]

_PST_KNIGHT = [
    -50,-40,-30,-30,-30,-30,-40,-50,
    -40,-20,  0,  0,  0,  0,-20,-40,
    -30,  0, 10, 15, 15, 10,  0,-30,
    -30,  5, 15, 20, 20, 15,  5,-30,
    -30,  0, 15, 20, 20, 15,  0,-30,
    -30,  5, 10, 15, 15, 10,  5,-30,
    -40,-20,  0,  5,  5,  0,-20,-40,
    -50,-40,-30,-30,-30,-30,-40,-50,
]

_PST_BISHOP = [
    -20,-10,-10,-10,-10,-10,-10,-20,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -10,  0, 10, 10, 10, 10,  0,-10,
    -10,  5,  5, 10, 10,  5,  5,-10,
    -10,  0,  5, 10, 10,  5,  0,-10,
    -10, 10, 10, 10, 10, 10, 10,-10,
    -10,  5,  0,  0,  0,  0,  5,-10,
    -20,-10,-10,-10,-10,-10,-10,-20,
]

_PST_ROOK = [
     0,  0,  0,  0,  0,  0,  0,  0,
     5, 10, 10, 10, 10, 10, 10,  5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
     0,  0,  0,  5,  5,  0,  0,  0,
]

_PST_QUEEN = [
    -20,-10,-10, -5, -5,-10,-10,-20,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -10,  0,  5,  5,  5,  5,  0,-10,
     -5,  0,  5,  5,  5,  5,  0, -5,
      0,  0,  5,  5,  5,  5,  0, -5,
    -10,  5,  5,  5,  5,  5,  0,-10,
    -10,  0,  5,  0,  0,  0,  0,-10,
    -20,-10,-10, -5, -5,-10,-10,-20,
]

_PST_KING_MG = [
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -20,-30,-30,-40,-40,-30,-30,-20,
    -10,-20,-20,-20,-20,-20,-20,-10,
     20, 20,  0,  0,  0,  0, 20, 20,
     20, 30, 10,  0,  0, 10, 30, 20,
]

_PST_KING_EG = [
    -50,-40,-30,-20,-20,-30,-40,-50,
    -30,-20,-10,  0,  0,-10,-20,-30,
    -30,-10, 20, 30, 30, 20,-10,-30,
    -30,-10, 30, 40, 40, 30,-10,-30,
    -30,-10, 30, 40, 40, 30,-10,-30,
    -30,-10, 20, 30, 30, 20,-10,-30,
    -30,-30,  0,  0,  0,  0,-30,-30,
    -50,-30,-30,-30,-30,-30,-30,-50,
]

_PST = {
    chess.PAWN:   _PST_PAWN,
    chess.KNIGHT: _PST_KNIGHT,
    chess.BISHOP: _PST_BISHOP,
    chess.ROOK:   _PST_ROOK,
    chess.QUEEN:  _PST_QUEEN,
}


def _mirror_sq(sq):
    """Mirror a square index vertically (for Black's PST lookup)."""
    return sq ^ 56  # flips rank: rank 0↔7, 1↔6, etc.


def _is_endgame(board):
    queens = len(board.pieces(chess.QUEEN, chess.WHITE)) + len(board.pieces(chess.QUEEN, chess.BLACK))
    minors_majors = (
        len(board.pieces(chess.ROOK, chess.WHITE)) + len(board.pieces(chess.ROOK, chess.BLACK))
        + len(board.pieces(chess.KNIGHT, chess.WHITE)) + len(board.pieces(chess.KNIGHT, chess.BLACK))
        + len(board.pieces(chess.BISHOP, chess.WHITE)) + len(board.pieces(chess.BISHOP, chess.BLACK))
    )
    return queens == 0 or (queens <= 2 and minors_majors <= 4)


def _material(board, color):
    total = 0
    for sq, piece in board.piece_map().items():
        if piece.color == color:
            total += PIECE_VALUES.get(piece.piece_type, 0)
    return total


def _evaluate_board(board, engine_color):
    """Full evaluation: material + piece-square tables + mobility + king safety."""
    if board.is_checkmate():
        return -99999 if board.turn == engine_color else 99999
    if board.is_stalemate() or board.is_insufficient_material():
        return 0
    if board.can_claim_draw():
        return 0

    endgame = _is_endgame(board)
    score = 0

    for sq, piece in board.piece_map().items():
        val = PIECE_VALUES.get(piece.piece_type, 0)
        pst_table = _PST.get(piece.piece_type)

        if piece.color == chess.WHITE:
            pst_bonus = 0
            if piece.piece_type == chess.KING:
                pst_bonus = _PST_KING_EG[_mirror_sq(sq)] if endgame else _PST_KING_MG[_mirror_sq(sq)]
            elif pst_table:
                pst_bonus = pst_table[_mirror_sq(sq)]
            score += val + pst_bonus
        else:
            pst_bonus = 0
            if piece.piece_type == chess.KING:
                pst_bonus = _PST_KING_EG[sq] if endgame else _PST_KING_MG[sq]
            elif pst_table:
                pst_bonus = pst_table[sq]
            score -= val + pst_bonus

    w_mobility = 0
    b_mobility = 0
    try:
        if board.turn == chess.WHITE:
            w_mobility = len(list(board.legal_moves))
            board.push(chess.Move.null())
            b_mobility = len(list(board.legal_moves))
            board.pop()
        else:
            b_mobility = len(list(board.legal_moves))
            board.push(chess.Move.null())
            w_mobility = len(list(board.legal_moves))
            board.pop()
    except Exception:
        pass
    score += (w_mobility - b_mobility) * 5

    if board.has_castling_rights(chess.WHITE):
        score += 15
    if board.has_castling_rights(chess.BLACK):
        score -= 15

    w_bishops = len(board.pieces(chess.BISHOP, chess.WHITE))
    b_bishops = len(board.pieces(chess.BISHOP, chess.BLACK))
    if w_bishops >= 2:
        score += 30
    if b_bishops >= 2:
        score -= 30

    for color in [chess.WHITE, chess.BLACK]:
        pawn_files = set()
        for sq in board.pieces(chess.PAWN, color):
            f = chess.square_file(sq)
            if f in pawn_files:
                if color == chess.WHITE:
                    score -= 10
                else:
                    score += 10
            pawn_files.add(f)

    if engine_color == chess.WHITE:
        return score
    return -score


def _order_moves(board):
    """Order moves for more efficient alpha-beta pruning."""
    scored = []
    for move in board.legal_moves:
        s = 0
        if board.is_capture(move):
            victim = board.piece_at(move.to_square)
            attacker = board.piece_at(move.from_square)
            if victim and attacker:
                s += 10 * PIECE_VALUES.get(victim.piece_type, 0) - PIECE_VALUES.get(attacker.piece_type, 0)
            else:
                s += 100
        if move.promotion:
            s += PIECE_VALUES.get(move.promotion, 0)
        if board.gives_check(move):
            s += 50
        scored.append((s, move))
    scored.sort(key=lambda x: -x[0])
    return [m for _, m in scored]


def _alphabeta(board, depth, alpha, beta, engine_color, maximizing):
    """Minimax with alpha-beta pruning."""
    if depth == 0 or board.is_game_over():
        return _evaluate_board(board, engine_color)

    if maximizing:
        max_eval = -100000
        for move in _order_moves(board):
            board.push(move)
            val = _alphabeta(board, depth - 1, alpha, beta, engine_color, False)
            board.pop()
            if val > max_eval:
                max_eval = val
            if max_eval > alpha:
                alpha = max_eval
            if beta <= alpha:
                break
        return max_eval
    else:
        min_eval = 100000
        for move in _order_moves(board):
            board.push(move)
            val = _alphabeta(board, depth - 1, alpha, beta, engine_color, True)
            board.pop()
            if val < min_eval:
                min_eval = val
            if min_eval < beta:
                beta = min_eval
            if beta <= alpha:
                break
        return min_eval


def _find_best_moves(board, engine_color, depth):
    """Return all legal moves scored by minimax, sorted best-first."""
    results = []
    for move in _order_moves(board):
        board.push(move)
        val = _alphabeta(board, depth - 1, -100000, 100000, engine_color, False)
        board.pop()
        results.append((val, move))
    results.sort(key=lambda x: -x[0])
    return results


def pick_move(fen, mood_key=None):
    """Select Enoch's next move given a FEN string.

    Uses minimax with alpha-beta pruning at mood-appropriate depth,
    then selects from top candidates with noise to simulate the target Elo.

    Returns (chess.Move or None, move_mood_str).
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

    if random.random() < params['blunder_chance']:
        chosen = random.choice(legal)
        is_cap = board.is_capture(chosen)
        board.push(chosen)
        if board.is_checkmate():
            mv_mood = 'checkmate'
        elif board.is_check():
            mv_mood = 'check'
        elif is_cap:
            mv_mood = 'capture'
        else:
            mv_mood = 'blunder'
        board.pop()
        return chosen, mv_mood

    scored = _find_best_moves(board, engine_color, params['depth'])

    for i in range(len(scored)):
        noise = random.gauss(0, params['noise'])
        scored[i] = (scored[i][0] + noise, scored[i][1])
    scored.sort(key=lambda x: -x[0])

    top_n = min(params['top_n'], len(scored))
    weights = [max(1, 100 - i * (80 // top_n)) for i in range(top_n)]
    chosen = random.choices([s[1] for s in scored[:top_n]], weights=weights, k=1)[0]

    is_cap = board.is_capture(chosen)
    board.push(chosen)
    if board.is_checkmate():
        mv_mood = 'checkmate'
    elif board.is_check():
        mv_mood = 'check'
    elif is_cap:
        mv_mood = 'capture'
    else:
        mv_mood = 'normal'
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
