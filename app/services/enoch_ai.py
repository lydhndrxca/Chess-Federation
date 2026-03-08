"""Enoch AI — a weak, distracted chess engine (~500-600 Elo).

'A man who watches brilliant chess all day but cannot play it himself.'

Behavior:
- Prefers standard, clumsy development
- Completely misses 2-move tactics
- Hangs pieces when the board is crowded
- Occasionally finds a sharp move, then blunders next turn
"""

import random
import chess


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


def _score_move(board, move, engine_color):
    """Score a single move for Enoch's selection heuristic.  Depth-1 only."""
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

    board.pop()

    score += random.gauss(0, 80)

    return score


def _is_blunder_turn(move_number):
    """Enoch blunders more as the board gets crowded / in the midgame."""
    if move_number < 6:
        return random.random() < 0.15
    elif move_number < 20:
        return random.random() < 0.35
    else:
        return random.random() < 0.25


def _is_sharp_turn():
    """Occasionally Enoch finds a surprisingly good move."""
    return random.random() < 0.08


def pick_move(fen):
    """Select Enoch's next move given a FEN string.

    Returns a chess.Move, or None if no legal moves.
    Also returns a 'mood' string for dialogue selection:
      'blunder', 'sharp', 'normal', 'capture', 'check'
    """
    board = chess.Board(fen)
    legal = list(board.legal_moves)
    if not legal:
        return None, 'none'

    if len(legal) == 1:
        board.push(legal[0])
        mood = 'check' if board.is_check() else 'normal'
        board.pop()
        return legal[0], mood

    engine_color = board.turn
    move_number = board.fullmove_number

    if _is_blunder_turn(move_number) and not _is_sharp_turn():
        chosen = random.choice(legal)
        board.push(chosen)
        mat_before = _material(board, engine_color)
        board.pop()

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
        s = _score_move(board, move, engine_color)
        scored.append((s, move))

    scored.sort(key=lambda x: -x[0])

    if _is_sharp_turn():
        chosen = scored[0][1]
        mood = 'sharp'
    else:
        top_n = min(5, len(scored))
        weights = [max(1, 100 - i * 25) for i in range(top_n)]
        chosen = random.choices([s[1] for s in scored[:top_n]], weights=weights, k=1)[0]
        mood = 'normal'

    is_cap = board.is_capture(chosen)
    board.push(chosen)
    if board.is_checkmate():
        mood = 'checkmate'
    elif board.is_check():
        mood = 'check'
    elif is_cap:
        mood = 'capture'
    board.pop()

    return chosen, mood


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
