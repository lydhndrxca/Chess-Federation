"""The Crypt — 10-wave Millionaire-style solo chess mode.

Player (White) faces 10 escalating waves of Enoch's minions (Black).
Entry costs 5 rating points.  Cash-out checkpoints at waves 3, 6, 9.
Wave 10 is the Enoch Boss fight.
"""

import json
import random
from datetime import datetime, timedelta, timezone

import chess

# ── Constants ───────────────────────────────────────────────────

MAX_WAVES = 10
ENTRY_COST = 5
DAILY_LIMIT = 3
CST_OFFSET = timedelta(hours=-6)

# ── Milestones / Tiers ─────────────────────────────────────────
# After clearing these waves, the player may cash out.
# safety_net: locked-in net rating if they lose AFTER this milestone
# cashout:    net rating if they choose to leave now

MILESTONES = {
    3:  {'cashout': 0,  'safety_net': 0},
    6:  {'cashout': 10, 'safety_net': 5},
    9:  {'cashout': 25, 'safety_net': 15},
}
BOSS_REWARD = 50  # net rating for beating wave 10

# Ladder data for the frontend
LADDER = []
for w in range(1, MAX_WAVES + 1):
    entry = {'wave': w, 'is_milestone': w in MILESTONES, 'is_boss': w == MAX_WAVES}
    if w in MILESTONES:
        entry['cashout'] = MILESTONES[w]['cashout']
        entry['safety_net'] = MILESTONES[w]['safety_net']
    if w == MAX_WAVES:
        entry['reward'] = BOSS_REWARD
    LADDER.append(entry)


def get_safety_net(highest_wave_cleared):
    """Return the locked-in net rating for a player who cleared up to *wave*."""
    net = -ENTRY_COST
    for mw in sorted(MILESTONES):
        if highest_wave_cleared >= mw:
            net = MILESTONES[mw]['safety_net']
    return net


def get_cashout_value(wave_just_cleared):
    """Return net rating if cashing out after clearing *wave*, or None."""
    m = MILESTONES.get(wave_just_cleared)
    return m['cashout'] if m else None


def is_milestone_wave(wave):
    return wave in MILESTONES


# ── Daily limit ─────────────────────────────────────────────────

def _cst_today():
    """Return the current CST date boundaries as UTC datetimes."""
    now_utc = datetime.now(timezone.utc)
    now_cst = now_utc + CST_OFFSET
    start_cst = now_cst.replace(hour=0, minute=0, second=0, microsecond=0)
    start_utc = start_cst - CST_OFFSET
    end_utc = start_utc + timedelta(days=1)
    return start_utc, end_utc


def runs_today(user_id):
    from app.models import CryptGame
    start, end = _cst_today()
    return CryptGame.query.filter(
        CryptGame.user_id == user_id,
        CryptGame.started_at >= start,
        CryptGame.started_at < end,
    ).count()


def can_enter(user_id):
    return runs_today(user_id) < DAILY_LIMIT


# ── Shop ────────────────────────────────────────────────────────

SHOP_PRICES = {'P': 3, 'N': 6, 'B': 6, 'R': 10, 'Q': 20}

PIECE_LABELS = {
    'P': 'Pawn', 'N': 'Knight', 'B': 'Bishop', 'R': 'Rook', 'Q': 'Queen',
}

# ── Scoring ─────────────────────────────────────────────────────

CAPTURE_GOLD = {
    chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3,
    chess.ROOK: 5, chess.QUEEN: 9,
}

CAPTURE_SCORE = {
    chess.PAWN: 10, chess.KNIGHT: 30, chess.BISHOP: 30,
    chess.ROOK: 50, chess.QUEEN: 90,
}


def wave_bonus_gold(wave):
    return wave * 5


def wave_bonus_score(wave):
    return wave * 100


# ── Wave generation ─────────────────────────────────────────────

def generate_wave(wave_number):
    """Return a list of ``(piece_symbol, square_name)`` for Black pieces."""
    w = min(wave_number, MAX_WAVES)

    #               wave: 0  1  2  3  4  5  6  7  8  9  10
    n_pawns   = [0, 3, 4, 5, 5, 6, 6, 7, 7, 8, 8][w]
    n_knights = [0, 0, 1, 1, 2, 2, 2, 2, 2, 2, 2][w]
    n_bishops = [0, 0, 0, 1, 1, 2, 2, 2, 2, 2, 2][w]
    n_rooks   = [0, 0, 0, 0, 0, 0, 1, 2, 2, 2, 2][w]
    n_queens  = [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 2][w]

    pieces = [('k', 'e8')]

    rank8 = ['a8', 'b8', 'c8', 'd8', 'f8', 'g8', 'h8']
    random.shuffle(rank8)

    for sym, count in [('q', n_queens), ('r', n_rooks),
                       ('b', n_bishops), ('n', n_knights)]:
        for _ in range(count):
            if rank8:
                pieces.append((sym, rank8.pop()))

    rank7 = ['a7', 'b7', 'c7', 'd7', 'e7', 'f7', 'g7', 'h7']
    random.shuffle(rank7)
    for _ in range(min(n_pawns, len(rank7))):
        pieces.append(('p', rank7.pop()))

    # Overflow for boss wave extra pieces
    rank6 = ['a6', 'b6', 'c6', 'd6', 'e6', 'f6', 'g6', 'h6']
    random.shuffle(rank6)
    placed_major = sum(1 for s, _ in pieces if s not in ('k', 'p'))
    needed_major = n_knights + n_bishops + n_rooks + n_queens
    overflow = needed_major - placed_major
    for sym, count in [('n', n_knights), ('b', n_bishops),
                       ('r', n_rooks), ('q', n_queens)]:
        if overflow <= 0:
            break
        already = sum(1 for s, _ in pieces if s == sym)
        deficit = count - already
        for _ in range(deficit):
            if rank6:
                pieces.append((sym, rank6.pop()))
                overflow -= 1

    return pieces


# ── FEN helpers ─────────────────────────────────────────────────

_SYM_TO_PIECE = {
    'K': chess.Piece(chess.KING, chess.WHITE),
    'Q': chess.Piece(chess.QUEEN, chess.WHITE),
    'R': chess.Piece(chess.ROOK, chess.WHITE),
    'B': chess.Piece(chess.BISHOP, chess.WHITE),
    'N': chess.Piece(chess.KNIGHT, chess.WHITE),
    'P': chess.Piece(chess.PAWN, chess.WHITE),
    'k': chess.Piece(chess.KING, chess.BLACK),
    'q': chess.Piece(chess.QUEEN, chess.BLACK),
    'r': chess.Piece(chess.ROOK, chess.BLACK),
    'b': chess.Piece(chess.BISHOP, chess.BLACK),
    'n': chess.Piece(chess.KNIGHT, chess.BLACK),
    'p': chess.Piece(chess.PAWN, chess.BLACK),
}


def build_fen(player_placement, enemy_pieces):
    board = chess.Board.empty()
    for sq_name, sym in player_placement.items():
        board.set_piece_at(chess.parse_square(sq_name), _SYM_TO_PIECE[sym])
    for sym, sq_name in enemy_pieces:
        board.set_piece_at(chess.parse_square(sq_name), _SYM_TO_PIECE[sym])
    board.turn = chess.WHITE
    board.castling_rights = chess.BB_EMPTY
    board.ep_square = None
    return board.fen()


def get_surviving_pieces(board):
    return [piece.symbol().upper() for sq, piece in board.piece_map().items()
            if piece.color == chess.WHITE]


def check_wave_complete(board):
    for sq, piece in board.piece_map().items():
        if piece.color == chess.BLACK and piece.piece_type != chess.KING:
            return False
    return True


def get_legal_moves_list(board):
    moves = []
    for m in board.legal_moves:
        promo = ''
        if m.promotion:
            promo = chess.piece_symbol(m.promotion)
        moves.append({
            'from': chess.square_name(m.from_square),
            'to': chess.square_name(m.to_square),
            'uci': m.uci(),
            'san': board.san(m),
            'promotion': promo,
        })
    return moves


# ── AI difficulty per wave (tuned for 10-wave run) ──────────────

_WAVE_PARAMS = {
    1:  {'depth': 1, 'noise': 150, 'blunder_chance': 0.30, 'top_n': 6, 'time_limit': 0.5},
    2:  {'depth': 2, 'noise': 120, 'blunder_chance': 0.20, 'top_n': 5, 'time_limit': 0.6},
    3:  {'depth': 2, 'noise': 80,  'blunder_chance': 0.12, 'top_n': 4, 'time_limit': 0.8},
    4:  {'depth': 3, 'noise': 60,  'blunder_chance': 0.08, 'top_n': 3, 'time_limit': 1.0},
    5:  {'depth': 3, 'noise': 40,  'blunder_chance': 0.05, 'top_n': 3, 'time_limit': 1.0},
    6:  {'depth': 3, 'noise': 25,  'blunder_chance': 0.03, 'top_n': 2, 'time_limit': 1.2},
    7:  {'depth': 4, 'noise': 15,  'blunder_chance': 0.02, 'top_n': 2, 'time_limit': 1.5},
    8:  {'depth': 4, 'noise': 10,  'blunder_chance': 0.01, 'top_n': 2, 'time_limit': 1.5},
    9:  {'depth': 5, 'noise': 5,   'blunder_chance': 0.00, 'top_n': 2, 'time_limit': 2.0},
    10: {'depth': 5, 'noise': 0,   'blunder_chance': 0.00, 'top_n': 1, 'time_limit': 2.5},
}


def pick_horde_move(fen, wave):
    from app.services.enoch_ai import _find_best_moves

    params = _WAVE_PARAMS.get(min(wave, MAX_WAVES), _WAVE_PARAMS[MAX_WAVES])
    board = chess.Board(fen)
    legal = list(board.legal_moves)
    if not legal:
        return None
    if len(legal) == 1:
        return legal[0]

    engine_color = board.turn

    if random.random() < params['blunder_chance']:
        return random.choice(legal)

    scored = _find_best_moves(board, engine_color, params['depth'],
                              params['time_limit'])

    for i in range(len(scored)):
        noise = random.gauss(0, params['noise'])
        scored[i] = (scored[i][0] + noise, scored[i][1])
    scored.sort(key=lambda x: -x[0])

    top_n = min(params['top_n'], len(scored))
    weights = [max(1, 100 - i * (80 // max(top_n, 1))) for i in range(top_n)]
    chosen = random.choices(
        [s[1] for s in scored[:top_n]], weights=weights, k=1
    )[0]
    return chosen
