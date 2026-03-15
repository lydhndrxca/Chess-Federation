"""Courier Run AI — heuristic evaluation + minimax with alpha-beta.

Phase 1: Greedy single-ply evaluator
Phase 2: Minimax with alpha-beta (depth 2-4)
"""

import random
import time

import chess

from app.services.courier_engine import (
    get_legal_moves, make_move, check_game_over,
    courier_distance_to_goal, PIECE_VALUES, TURN_CAP,
)

INF = 999999


def _material(board, color):
    score = 0
    for sq in chess.SQUARES:
        p = board.piece_at(sq)
        if p and p.color == color:
            score += PIECE_VALUES.get(p.piece_type, 0)
    return score


def _is_protected(board, sq, color):
    """Check if square is defended by a friendly piece."""
    return bool(board.attackers(color, sq))


def _attacker_count(board, sq, color):
    """Count how many pieces of `color` attack `sq`."""
    return len(board.attackers(color, sq))


def _lane_openness(board, file_idx, color):
    """Score how clear the file is for a pawn to advance.
    Higher = more open. Penalize enemy pieces blocking the lane.
    """
    score = 0
    enemy = not color
    if color == chess.WHITE:
        ranks = range(2, 8)
    else:
        ranks = range(5, -1, -1)
    for r in ranks:
        sq = chess.square(file_idx, r)
        p = board.piece_at(sq)
        if p is None:
            score += 1
        elif p.color == enemy:
            score -= 1
            break
        else:
            break
    return max(0, score)


def evaluate(fen, courier_white_sq, courier_black_sq, turn_count, for_color=chess.WHITE):
    """Heuristic evaluation of a Courier Run position.

    Positive = good for `for_color`. Negative = bad.
    """
    board = chess.Board(fen)

    over, winner, reason = check_game_over(fen, courier_white_sq, courier_black_sq, turn_count)
    if over:
        if winner == 'draw':
            return 0
        win_color = chess.WHITE if winner == 'white' else chess.BLACK
        return INF if win_color == for_color else -INF

    if courier_white_sq is None or courier_black_sq is None:
        return 0

    w_dist = courier_distance_to_goal(courier_white_sq, 'white')
    b_dist = courier_distance_to_goal(courier_black_sq, 'black')

    if for_color == chess.WHITE:
        my_dist, enemy_dist = w_dist, b_dist
        my_courier, enemy_courier = courier_white_sq, courier_black_sq
        my_color, enemy_color = chess.WHITE, chess.BLACK
    else:
        my_dist, enemy_dist = b_dist, w_dist
        my_courier, enemy_courier = courier_black_sq, courier_white_sq
        my_color, enemy_color = chess.BLACK, chess.WHITE

    score = 0.0

    # Distance differential (huge weight)
    score += 50 * (enemy_dist - my_dist)

    # Immediate threats
    if my_dist == 1:
        can_advance = False
        if my_color == chess.WHITE:
            dest = chess.square(chess.square_file(my_courier), chess.square_rank(my_courier) + 1)
        else:
            dest = chess.square(chess.square_file(my_courier), chess.square_rank(my_courier) - 1)
        p_at_dest = board.piece_at(dest)
        if p_at_dest is None or p_at_dest.color == enemy_color:
            can_advance = True
        if can_advance:
            score += 500

    if enemy_dist == 1:
        score -= 400

    # Protection of my courier
    my_protection = _attacker_count(board, my_courier, my_color)
    score += 15 * my_protection

    # Pressure on enemy courier
    enemy_pressure = _attacker_count(board, enemy_courier, my_color)
    score += 20 * enemy_pressure

    # Enemy protection of their courier
    enemy_protection = _attacker_count(board, enemy_courier, enemy_color)
    score -= 12 * enemy_protection

    # Threats to my courier
    threats_to_mine = _attacker_count(board, my_courier, enemy_color)
    score -= 25 * threats_to_mine

    # Lane openness
    my_file = chess.square_file(my_courier)
    enemy_file = chess.square_file(enemy_courier)
    score += 10 * _lane_openness(board, my_file, my_color)
    score -= 8 * _lane_openness(board, enemy_file, enemy_color)

    # Material balance
    my_mat = _material(board, my_color)
    enemy_mat = _material(board, enemy_color)
    score += (my_mat - enemy_mat) * 5

    # Can capture enemy courier this move?
    if board.turn == my_color:
        cw = courier_white_sq if courier_white_sq is not None else None
        cb = courier_black_sq if courier_black_sq is not None else None
        for m in get_legal_moves(fen, cw, cb):
            if m.to_square == enemy_courier:
                score += 800
                break

    return score


def pick_move_greedy(fen, courier_white_sq, courier_black_sq, turn_count):
    """Greedy single-ply: evaluate all moves and pick the best."""
    legal = get_legal_moves(fen, courier_white_sq, courier_black_sq)
    if not legal:
        return None

    board = chess.Board(fen)
    for_color = board.turn

    best_score = -INF - 1
    best_moves = []

    for m in legal:
        result = make_move(fen, m.uci(), courier_white_sq, courier_black_sq)
        score = evaluate(
            result['fen'],
            result['courier_white_sq'],
            result['courier_black_sq'],
            turn_count,
            for_color,
        )
        if score > best_score:
            best_score = score
            best_moves = [m]
        elif score == best_score:
            best_moves.append(m)

    return random.choice(best_moves) if best_moves else legal[0]


def _minimax(fen, courier_white_sq, courier_black_sq, turn_count,
             depth, alpha, beta, maximizing, for_color, deadline):
    """Minimax with alpha-beta pruning."""
    if time.time() > deadline:
        return evaluate(fen, courier_white_sq, courier_black_sq, turn_count, for_color)

    over, winner, reason = check_game_over(fen, courier_white_sq, courier_black_sq, turn_count)
    if over:
        if winner == 'draw':
            return 0
        win_color = chess.WHITE if winner == 'white' else chess.BLACK
        return INF if win_color == for_color else -INF

    if depth == 0:
        return evaluate(fen, courier_white_sq, courier_black_sq, turn_count, for_color)

    legal = get_legal_moves(fen, courier_white_sq, courier_black_sq)
    if not legal:
        return evaluate(fen, courier_white_sq, courier_black_sq, turn_count, for_color)

    # Move ordering: captures first, then courier moves, then rest
    board = chess.Board(fen)

    def move_priority(m):
        p = 0
        if board.is_capture(m):
            p -= 100
        my_courier = courier_white_sq if board.turn == chess.WHITE else courier_black_sq
        if m.from_square == my_courier:
            p -= 50
        return p

    legal.sort(key=move_priority)

    if maximizing:
        value = -INF
        for m in legal:
            result = make_move(fen, m.uci(), courier_white_sq, courier_black_sq)
            new_tc = turn_count + (1 if result['turn'] == 'white' else 0)
            child_val = _minimax(
                result['fen'], result['courier_white_sq'], result['courier_black_sq'],
                new_tc, depth - 1, alpha, beta, False, for_color, deadline,
            )
            value = max(value, child_val)
            alpha = max(alpha, value)
            if alpha >= beta:
                break
        return value
    else:
        value = INF
        for m in legal:
            result = make_move(fen, m.uci(), courier_white_sq, courier_black_sq)
            new_tc = turn_count + (1 if result['turn'] == 'white' else 0)
            child_val = _minimax(
                result['fen'], result['courier_white_sq'], result['courier_black_sq'],
                new_tc, depth - 1, alpha, beta, True, for_color, deadline,
            )
            value = min(value, child_val)
            beta = min(beta, value)
            if alpha >= beta:
                break
        return value


def pick_move_minimax(fen, courier_white_sq, courier_black_sq, turn_count,
                      depth=3, time_limit=3.0):
    """Minimax with alpha-beta and iterative deepening."""
    legal = get_legal_moves(fen, courier_white_sq, courier_black_sq)
    if not legal:
        return None
    if len(legal) == 1:
        return legal[0]

    board = chess.Board(fen)
    for_color = board.turn
    deadline = time.time() + time_limit

    best_move = legal[0]
    best_score = -INF - 1

    for d in range(1, depth + 1):
        if time.time() > deadline:
            break
        current_best = None
        current_score = -INF - 1

        for m in legal:
            if time.time() > deadline:
                break
            result = make_move(fen, m.uci(), courier_white_sq, courier_black_sq)
            new_tc = turn_count + (1 if result['turn'] == 'white' else 0)
            score = _minimax(
                result['fen'], result['courier_white_sq'], result['courier_black_sq'],
                new_tc, d - 1, -INF, INF, False, for_color, deadline,
            )
            if score > current_score:
                current_score = score
                current_best = m

        if current_best is not None:
            best_move = current_best
            best_score = current_score

        if best_score >= INF - 1:
            break

    return best_move


def pick_courier_for_ai(fen, color='black'):
    """AI selects which pawn to designate as courier.

    Strategy: pick a pawn that has the most open lane ahead.
    Prefer center/off-center files for more flexibility.
    """
    board = chess.Board(fen)
    side = chess.WHITE if color == 'white' else chess.BLACK
    pawns = list(board.pieces(chess.PAWN, side))

    if not pawns:
        return None

    file_preference = {3: 5, 4: 5, 2: 4, 5: 4, 1: 3, 6: 3, 0: 2, 7: 2}

    best_sq = pawns[0]
    best_score = -999

    for sq in pawns:
        f = chess.square_file(sq)
        openness = _lane_openness(board, f, side)
        pref = file_preference.get(f, 1)
        score = openness * 3 + pref
        if score > best_score:
            best_score = score
            best_sq = sq

    return best_sq
