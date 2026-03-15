"""Courier Run AI — deep heuristic evaluation + minimax with alpha-beta.

Tuned to play at roughly ~600-rated level for Courier Run specifically.
Understands escort formations, interception, path control, sacrifice timing,
and pawn screening patterns unique to this game mode.

If trained neural network weights exist (courier_weights.pt), the evaluation
blends the heuristic score with the neural net prediction for stronger play.
"""

import os
import random
import time

import chess

try:
    from app.services.courier_engine import (
        get_legal_moves, make_move, check_game_over,
        courier_distance_to_goal, PIECE_VALUES, TURN_CAP,
    )
except ImportError:
    from courier_engine import (
        get_legal_moves, make_move, check_game_over,
        courier_distance_to_goal, PIECE_VALUES, TURN_CAP,
    )

INF = 999999

# ---------- Neural network integration ----------

_nn_model = None
_nn_loaded = False
_nn_available = False

PIECE_PLANES = {
    'P': 0, 'N': 1, 'B': 2, 'R': 3, 'Q': 4, 'K': 5,
    'p': 6, 'n': 7, 'b': 8, 'r': 9, 'q': 10, 'k': 11,
}


def _load_nn():
    """Try to load the trained neural network weights."""
    global _nn_model, _nn_loaded, _nn_available
    if _nn_loaded:
        return _nn_available
    _nn_loaded = True

    weights_path = os.path.join(os.path.dirname(__file__), 'courier_weights.pt')
    if not os.path.exists(weights_path):
        return False

    try:
        import torch
        _nn_model = torch.jit.load(weights_path, map_location='cpu')
        _nn_model.eval()
        _nn_available = True
        return True
    except Exception:
        return False


def _nn_evaluate(fen, courier_white_sq, courier_black_sq, for_color):
    """Get the neural network's evaluation of a position.
    Returns a score in [-1, 1] or None if unavailable.
    """
    if not _nn_available or _nn_model is None:
        return None

    try:
        import torch
        import numpy as np

        planes = np.zeros((14, 8, 8), dtype=np.float32)
        board = chess.Board(fen)

        for sq in chess.SQUARES:
            p = board.piece_at(sq)
            if p:
                idx = PIECE_PLANES.get(p.symbol())
                if idx is not None:
                    planes[idx][chess.square_rank(sq)][chess.square_file(sq)] = 1.0

        if courier_white_sq is not None:
            r, f = chess.square_rank(courier_white_sq), chess.square_file(courier_white_sq)
            planes[12][r][f] = 1.0
        if courier_black_sq is not None:
            r, f = chess.square_rank(courier_black_sq), chess.square_file(courier_black_sq)
            planes[13][r][f] = 1.0

        tensor = torch.tensor(planes, dtype=torch.float32).unsqueeze(0)
        with torch.no_grad():
            raw = _nn_model(tensor).item()

        # raw is from the side-to-move perspective; flip if needed
        if board.turn == chess.WHITE and for_color == chess.BLACK:
            raw = -raw
        elif board.turn == chess.BLACK and for_color == chess.WHITE:
            raw = -raw

        return raw
    except Exception:
        return None


# Try to load on import
_load_nn()

# ---------- low-level helpers ----------

def _material(board, color):
    s = 0
    for pt in (chess.PAWN, chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN):
        s += len(board.pieces(pt, color)) * PIECE_VALUES[pt]
    return s


def _attacker_count(board, sq, color):
    return len(board.attackers(color, sq))


# ---------- Courier-Run-specific evaluation features ----------

def _courier_path_squares(courier_sq, color):
    """All squares on the courier's file from current rank to the goal rank."""
    f = chess.square_file(courier_sq)
    r = chess.square_rank(courier_sq)
    if color == chess.WHITE:
        return [chess.square(f, rank) for rank in range(r + 1, 8)]
    else:
        return [chess.square(f, rank) for rank in range(r - 1, -1, -1)]


def _path_blockage(board, courier_sq, color):
    """How many squares ahead of the courier are blocked by enemy or friendly pieces.
    Returns (blocked_count, first_blocker_distance).
    """
    path = _courier_path_squares(courier_sq, color)
    blocked = 0
    first_dist = len(path)
    for i, sq in enumerate(path):
        p = board.piece_at(sq)
        if p is not None:
            blocked += 1
            if i < first_dist:
                first_dist = i
    return blocked, first_dist


def _escort_score(board, courier_sq, color):
    """How well the courier is escorted — friendly pieces on adjacent files
    within ±2 ranks of the courier, especially ahead of it.
    """
    f = chess.square_file(courier_sq)
    r = chess.square_rank(courier_sq)
    score = 0.0

    for df in (-1, 0, 1):
        for dr in (-2, -1, 0, 1, 2):
            ff = f + df
            rr = r + dr
            if ff < 0 or ff > 7 or rr < 0 or rr > 7:
                continue
            if df == 0 and dr == 0:
                continue
            sq = chess.square(ff, rr)
            p = board.piece_at(sq)
            if p and p.color == color:
                weight = 1.0
                if color == chess.WHITE and dr > 0:
                    weight = 1.5  # pieces ahead of courier are more valuable
                elif color == chess.BLACK and dr < 0:
                    weight = 1.5
                if p.piece_type in (chess.KNIGHT, chess.BISHOP):
                    weight *= 1.3
                elif p.piece_type == chess.ROOK:
                    weight *= 1.1
                score += weight
    return score


def _interception_score(board, enemy_courier_sq, my_color):
    """How well we're positioned to intercept the enemy courier.
    Considers pieces that attack squares in the courier's path, and
    pieces that can reach the courier's file quickly.
    """
    enemy_color = not my_color
    path = _courier_path_squares(enemy_courier_sq, enemy_color)
    score = 0.0

    # Pieces attacking squares in the enemy courier's path
    for sq in path[:4]:  # focus on the next 4 squares
        attackers = board.attackers(my_color, sq)
        score += len(attackers) * 3.0

    # Pieces that directly attack the courier itself
    direct = _attacker_count(board, enemy_courier_sq, my_color)
    score += direct * 5.0

    # Pieces on the same file as the enemy courier (blocking potential)
    ef = chess.square_file(enemy_courier_sq)
    for rank in range(8):
        sq = chess.square(ef, rank)
        p = board.piece_at(sq)
        if p and p.color == my_color:
            score += 2.0

    # Pieces on adjacent files
    for df in (-1, 1):
        ff = ef + df
        if 0 <= ff <= 7:
            for rank in range(8):
                sq = chess.square(ff, rank)
                p = board.piece_at(sq)
                if p and p.color == my_color and p.piece_type in (chess.KNIGHT, chess.BISHOP):
                    score += 1.5

    return score


def _forward_control(board, courier_sq, color):
    """How many squares ahead of the courier are controlled by friendly pieces."""
    f = chess.square_file(courier_sq)
    r = chess.square_rank(courier_sq)
    controlled = 0

    for df in (-1, 0, 1):
        ff = f + df
        if ff < 0 or ff > 7:
            continue
        # Check the next 3 ranks ahead
        for step in range(1, 4):
            if color == chess.WHITE:
                rr = r + step
            else:
                rr = r - step
            if rr < 0 or rr > 7:
                break
            sq = chess.square(ff, rr)
            if board.attackers(color, sq):
                controlled += 1

    return controlled


def _pawn_screen(board, courier_sq, color):
    """Bonus for friendly pawns ahead or flanking the courier that provide cover."""
    f = chess.square_file(courier_sq)
    r = chess.square_rank(courier_sq)
    score = 0.0

    for df in (-1, 0, 1):
        ff = f + df
        if ff < 0 or ff > 7:
            continue
        for step in (1, 2):
            rr = r + step if color == chess.WHITE else r - step
            if rr < 0 or rr > 7:
                continue
            sq = chess.square(ff, rr)
            p = board.piece_at(sq)
            if p and p.color == color and p.piece_type == chess.PAWN:
                if df == 0:
                    score -= 2.0  # pawn directly ahead BLOCKS the courier
                else:
                    score += 3.0  # flanking pawns provide capture defense

    return score


def _can_capture_courier_now(board, fen, courier_white_sq, courier_black_sq, my_color):
    """Check if we can capture the enemy courier on this move."""
    if board.turn != my_color:
        return False
    enemy_courier = courier_black_sq if my_color == chess.WHITE else courier_white_sq
    if enemy_courier is None:
        return False
    legal = get_legal_moves(fen, courier_white_sq, courier_black_sq)
    for m in legal:
        if m.to_square == enemy_courier:
            return True
    return False


def _can_deliver_now(board, fen, courier_white_sq, courier_black_sq, my_color):
    """Check if our courier can advance to the delivery rank this move."""
    if board.turn != my_color:
        return False
    my_courier = courier_white_sq if my_color == chess.WHITE else courier_black_sq
    if my_courier is None:
        return False
    goal_rank = 7 if my_color == chess.WHITE else 0
    legal = get_legal_moves(fen, courier_white_sq, courier_black_sq)
    for m in legal:
        if m.from_square == my_courier and chess.square_rank(m.to_square) == goal_rank:
            return True
    return False


def _king_proximity_to_courier(board, courier_sq, color):
    """Bonus if our king is near the courier (king can escort/block)."""
    king_sqs = board.pieces(chess.KING, color)
    if not king_sqs:
        return 0
    king_sq = list(king_sqs)[0]
    dist = max(abs(chess.square_file(king_sq) - chess.square_file(courier_sq)),
               abs(chess.square_rank(king_sq) - chess.square_rank(courier_sq)))
    return max(0, 4 - dist)


# ---------- Main evaluation ----------

def evaluate(fen, courier_white_sq, courier_black_sq, turn_count, for_color=chess.WHITE):
    """Deep heuristic evaluation tuned for Courier Run.

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

    # ── 1. DISTANCE (most important — drives the win condition) ──
    # Non-linear: each rank closer is worth more than the last
    my_progress = 6 - my_dist     # 0 = starting rank, 6 = one away
    enemy_progress = 6 - enemy_dist

    score += 60 * (enemy_dist - my_dist)
    # Exponential bonus as courier gets very close
    if my_dist <= 2:
        score += (3 - my_dist) * 80
    if enemy_dist <= 2:
        score -= (3 - enemy_dist) * 70

    # ── 2. IMMEDIATE TACTICAL THREATS ──
    if _can_deliver_now(board, fen, courier_white_sq, courier_black_sq, my_color):
        score += 900
    if _can_deliver_now(board, fen, courier_white_sq, courier_black_sq, enemy_color):
        score -= 850

    if _can_capture_courier_now(board, fen, courier_white_sq, courier_black_sq, my_color):
        score += 800
    if _can_capture_courier_now(board, fen, courier_white_sq, courier_black_sq, enemy_color):
        score -= 750

    # ── 3. COURIER SAFETY ──
    # Protection (defenders)
    my_defenders = _attacker_count(board, my_courier, my_color)
    score += 18 * my_defenders

    # Threats (attackers on my courier)
    my_threats = _attacker_count(board, my_courier, enemy_color)
    score -= 30 * my_threats

    # Net safety: positive = well defended, negative = in danger
    if my_threats > my_defenders:
        score -= 40 * (my_threats - my_defenders)

    # ── 4. ENEMY COURIER PRESSURE ──
    enemy_attackers = _attacker_count(board, enemy_courier, my_color)
    enemy_defenders = _attacker_count(board, enemy_courier, enemy_color)
    score += 22 * enemy_attackers
    score -= 10 * enemy_defenders
    if enemy_attackers > enemy_defenders:
        score += 35 * (enemy_attackers - enemy_defenders)

    # ── 5. ESCORT FORMATION ──
    score += 12 * _escort_score(board, my_courier, my_color)
    score -= 8 * _escort_score(board, enemy_courier, enemy_color)

    # ── 6. INTERCEPTION ──
    score += 8 * _interception_score(board, enemy_courier, my_color)
    score -= 6 * _interception_score(board, my_courier, enemy_color)

    # ── 7. PATH ANALYSIS ──
    my_blocked, my_first = _path_blockage(board, my_courier, my_color)
    enemy_blocked, enemy_first = _path_blockage(board, enemy_courier, enemy_color)
    score -= 12 * my_blocked
    score += 8 * enemy_blocked
    # Bonus if immediate path is clear
    if my_first >= 2:
        score += 15
    if enemy_first == 0:
        score += 20  # enemy's path is immediately blocked

    # ── 8. FORWARD CONTROL ──
    score += 6 * _forward_control(board, my_courier, my_color)
    score -= 4 * _forward_control(board, enemy_courier, enemy_color)

    # ── 9. PAWN SCREEN ──
    score += 5 * _pawn_screen(board, my_courier, my_color)
    score -= 3 * _pawn_screen(board, enemy_courier, enemy_color)

    # ── 10. KING UTILITY (no check/checkmate, so king is a piece to use) ──
    score += 4 * _king_proximity_to_courier(board, my_courier, my_color)
    score += 3 * _king_proximity_to_courier(board, enemy_courier, my_color)

    # ── 11. MATERIAL ──
    my_mat = _material(board, my_color)
    enemy_mat = _material(board, enemy_color)
    score += (my_mat - enemy_mat) * 4

    # Material matters more when couriers are far from goal (long game)
    avg_dist = (my_dist + enemy_dist) / 2.0
    if avg_dist > 3:
        score += (my_mat - enemy_mat) * 2

    # ── 12. TEMPO / INITIATIVE ──
    # Being on move is worth something when close to delivery
    if board.turn == my_color and my_dist <= 3:
        score += 15
    elif board.turn == enemy_color and enemy_dist <= 3:
        score -= 15

    # ── 13. NEURAL NETWORK BLEND ──
    # If trained weights are available, blend heuristic with NN prediction.
    # NN output is [-1, 1]; scale to match heuristic range (~±500).
    if _nn_available:
        nn_val = _nn_evaluate(fen, courier_white_sq, courier_black_sq, for_color)
        if nn_val is not None:
            nn_score = nn_val * 500
            score = 0.4 * score + 0.6 * nn_score

    return score


# ---------- Transposition table ----------

_tt = {}
_tt_max_size = 500000


def _tt_lookup(key):
    return _tt.get(key)


def _tt_store(key, depth, value, flag):
    if len(_tt) > _tt_max_size:
        _tt.clear()
    _tt[key] = (depth, value, flag)


def _tt_key(fen, courier_white_sq, courier_black_sq):
    return (fen, courier_white_sq, courier_black_sq)


# ---------- Move ordering ----------

def _move_score(board, m, courier_white_sq, courier_black_sq, killer_move=None):
    """Score a move for ordering. Higher = search first."""
    score = 0

    my_courier = courier_white_sq if board.turn == chess.WHITE else courier_black_sq
    enemy_courier = courier_black_sq if board.turn == chess.WHITE else courier_white_sq

    # Capturing the enemy courier is always best
    if enemy_courier is not None and m.to_square == enemy_courier:
        return 10000

    # Courier delivery move
    if m.from_square == my_courier:
        goal_rank = 7 if board.turn == chess.WHITE else 0
        if chess.square_rank(m.to_square) == goal_rank:
            return 9000
        # Courier advancing toward goal
        if board.turn == chess.WHITE:
            score += (chess.square_rank(m.to_square) - chess.square_rank(m.from_square)) * 60
        else:
            score += (chess.square_rank(m.from_square) - chess.square_rank(m.to_square)) * 60

    # Captures — MVV-LVA
    if board.is_capture(m):
        victim = board.piece_at(m.to_square)
        attacker = board.piece_at(m.from_square)
        victim_val = PIECE_VALUES.get(victim.piece_type, 0) if victim else 0
        attacker_val = PIECE_VALUES.get(attacker.piece_type, 0) if attacker else 0
        score += 200 + victim_val * 10 - attacker_val

    # Killer move bonus
    if killer_move and m == killer_move:
        score += 150

    # Moves toward the enemy courier
    if enemy_courier is not None:
        d_before = max(abs(chess.square_file(m.from_square) - chess.square_file(enemy_courier)),
                       abs(chess.square_rank(m.from_square) - chess.square_rank(enemy_courier)))
        d_after = max(abs(chess.square_file(m.to_square) - chess.square_file(enemy_courier)),
                      abs(chess.square_rank(m.to_square) - chess.square_rank(enemy_courier)))
        if d_after < d_before:
            score += 30

    # Center control
    to_file = chess.square_file(m.to_square)
    if 2 <= to_file <= 5:
        score += 5

    return score


# ---------- Minimax with alpha-beta ----------

def _minimax(fen, courier_white_sq, courier_black_sq, turn_count,
             depth, alpha, beta, maximizing, for_color, deadline, killer=None):
    """Minimax with alpha-beta, transposition table, and killer moves."""
    if time.time() > deadline:
        return evaluate(fen, courier_white_sq, courier_black_sq, turn_count, for_color)

    tt_key = _tt_key(fen, courier_white_sq, courier_black_sq)
    tt_entry = _tt_lookup(tt_key)
    if tt_entry and tt_entry[0] >= depth:
        stored_depth, stored_val, stored_flag = tt_entry
        if stored_flag == 'exact':
            return stored_val
        elif stored_flag == 'lower' and stored_val > alpha:
            alpha = stored_val
        elif stored_flag == 'upper' and stored_val < beta:
            beta = stored_val
        if alpha >= beta:
            return stored_val

    over, winner, reason = check_game_over(fen, courier_white_sq, courier_black_sq, turn_count)
    if over:
        if winner == 'draw':
            return 0
        win_color = chess.WHITE if winner == 'white' else chess.BLACK
        return INF if win_color == for_color else -INF

    if depth == 0:
        return _quiesce(fen, courier_white_sq, courier_black_sq, turn_count,
                        alpha, beta, for_color, deadline, 3)

    legal = get_legal_moves(fen, courier_white_sq, courier_black_sq)
    if not legal:
        return evaluate(fen, courier_white_sq, courier_black_sq, turn_count, for_color)

    board = chess.Board(fen)
    legal.sort(key=lambda m: _move_score(board, m, courier_white_sq, courier_black_sq, killer),
               reverse=True)

    best_move = None
    orig_alpha = alpha

    if maximizing:
        value = -INF
        for m in legal:
            if time.time() > deadline:
                break
            result = make_move(fen, m.uci(), courier_white_sq, courier_black_sq)
            new_tc = turn_count + (1 if result['turn'] == 'white' else 0)
            child_val = _minimax(
                result['fen'], result['courier_white_sq'], result['courier_black_sq'],
                new_tc, depth - 1, alpha, beta, False, for_color, deadline, killer,
            )
            if child_val > value:
                value = child_val
                best_move = m
            alpha = max(alpha, value)
            if alpha >= beta:
                break
    else:
        value = INF
        for m in legal:
            if time.time() > deadline:
                break
            result = make_move(fen, m.uci(), courier_white_sq, courier_black_sq)
            new_tc = turn_count + (1 if result['turn'] == 'white' else 0)
            child_val = _minimax(
                result['fen'], result['courier_white_sq'], result['courier_black_sq'],
                new_tc, depth - 1, alpha, beta, True, for_color, deadline, killer,
            )
            if child_val < value:
                value = child_val
                best_move = m
            beta = min(beta, value)
            if alpha >= beta:
                break

    if value <= orig_alpha:
        flag = 'upper'
    elif value >= beta:
        flag = 'lower'
    else:
        flag = 'exact'
    _tt_store(tt_key, depth, value, flag)

    return value


def _quiesce(fen, courier_white_sq, courier_black_sq, turn_count,
             alpha, beta, for_color, deadline, max_depth):
    """Quiescence search — evaluate captures and courier moves to avoid horizon effect."""
    stand_pat = evaluate(fen, courier_white_sq, courier_black_sq, turn_count, for_color)

    board = chess.Board(fen)
    is_max = (board.turn == for_color)

    if is_max:
        if stand_pat >= beta:
            return beta
        alpha = max(alpha, stand_pat)
    else:
        if stand_pat <= alpha:
            return alpha
        beta = min(beta, stand_pat)

    if max_depth <= 0 or time.time() > deadline:
        return stand_pat

    legal = get_legal_moves(fen, courier_white_sq, courier_black_sq)
    my_courier = courier_white_sq if board.turn == chess.WHITE else courier_black_sq
    enemy_courier = courier_black_sq if board.turn == chess.WHITE else courier_white_sq

    # Only search captures, courier captures, and courier delivery moves
    tactical = []
    for m in legal:
        if board.is_capture(m):
            tactical.append(m)
        elif m.from_square == my_courier:
            goal_rank = 7 if board.turn == chess.WHITE else 0
            if chess.square_rank(m.to_square) == goal_rank:
                tactical.append(m)
            elif courier_distance_to_goal(m.to_square,
                    'white' if board.turn == chess.WHITE else 'black') <= 1:
                tactical.append(m)

    if not tactical:
        return stand_pat

    tactical.sort(key=lambda m: _move_score(board, m, courier_white_sq, courier_black_sq),
                  reverse=True)

    for m in tactical:
        if time.time() > deadline:
            break
        result = make_move(fen, m.uci(), courier_white_sq, courier_black_sq)
        new_tc = turn_count + (1 if result['turn'] == 'white' else 0)
        val = _quiesce(result['fen'], result['courier_white_sq'], result['courier_black_sq'],
                       new_tc, alpha, beta, for_color, deadline, max_depth - 1)

        if is_max:
            if val > alpha:
                alpha = val
            if alpha >= beta:
                return beta
        else:
            if val < beta:
                beta = val
            if alpha >= beta:
                return alpha

    return alpha if is_max else beta


# ---------- Top-level move picker ----------

def pick_move_minimax(fen, courier_white_sq, courier_black_sq, turn_count,
                      depth=4, time_limit=3.0):
    """Iterative deepening minimax with alpha-beta, TT, and quiescence."""
    legal = get_legal_moves(fen, courier_white_sq, courier_black_sq)
    if not legal:
        return None
    if len(legal) == 1:
        return legal[0]

    board = chess.Board(fen)
    for_color = board.turn
    deadline = time.time() + time_limit

    # Pre-sort moves
    legal.sort(key=lambda m: _move_score(board, m, courier_white_sq, courier_black_sq),
               reverse=True)

    best_move = legal[0]
    best_score = -INF - 1
    killer = None

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
                new_tc, d - 1, -INF, INF, False, for_color, deadline, killer,
            )
            if score > current_score:
                current_score = score
                current_best = m

        if current_best is not None:
            best_move = current_best
            best_score = current_score
            killer = current_best
            # Reorder for next iteration: put best move first
            legal.remove(current_best)
            legal.insert(0, current_best)

        if best_score >= INF - 1:
            break

    return best_move


# ---------- Greedy fallback ----------

def pick_move_greedy(fen, courier_white_sq, courier_black_sq, turn_count):
    """Greedy single-ply evaluator (fallback)."""
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
            result['fen'], result['courier_white_sq'], result['courier_black_sq'],
            turn_count, for_color,
        )
        if score > best_score:
            best_score = score
            best_moves = [m]
        elif score == best_score:
            best_moves.append(m)

    return random.choice(best_moves) if best_moves else legal[0]


# ---------- Courier selection ----------

def pick_courier_for_ai(fen, color='black'):
    """Smart courier selection considering lane openness, protection potential,
    and distance from enemy pieces.
    """
    board = chess.Board(fen)
    side = chess.WHITE if color == 'white' else chess.BLACK
    enemy = not side
    pawns = list(board.pieces(chess.PAWN, side))

    if not pawns:
        return None

    best_sq = pawns[0]
    best_score = -999

    for sq in pawns:
        f = chess.square_file(sq)
        r = chess.square_rank(sq)
        score = 0.0

        # Center preference (d/e best, c/f good, edges weak)
        center_bonus = {3: 8, 4: 8, 2: 6, 5: 6, 1: 3, 6: 3, 0: 1, 7: 1}
        score += center_bonus.get(f, 0)

        # Lane openness ahead
        path = _courier_path_squares(sq, side)
        clear = 0
        for psq in path:
            p = board.piece_at(psq)
            if p is None:
                clear += 1
            else:
                break
        score += clear * 4

        # Friendly pieces on adjacent files (escort potential)
        for df in (-1, 1):
            ff = f + df
            if 0 <= ff <= 7:
                for dr in range(-1, 3):
                    rr = r + dr if side == chess.WHITE else r - dr
                    if 0 <= rr <= 7:
                        p = board.piece_at(chess.square(ff, rr))
                        if p and p.color == side:
                            score += 2

        # Penalty if enemy pieces directly ahead
        for psq in path[:3]:
            p = board.piece_at(psq)
            if p and p.color == enemy:
                score -= 5

        # Avoid rook/bishop files where enemy has long-range control
        for rank in range(8):
            s = chess.square(f, rank)
            p = board.piece_at(s)
            if p and p.color == enemy and p.piece_type in (chess.ROOK, chess.QUEEN):
                score -= 4

        if score > best_score:
            best_score = score
            best_sq = sq

    return best_sq
