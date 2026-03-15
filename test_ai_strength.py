"""Measure Courier Run AI strength with different opponents."""
import sys, os, time, random
sys.path.insert(0, os.path.join('app', 'services'))

from courier_ai import (
    _nn_available, evaluate, pick_move_minimax, pick_courier_for_ai, _tt,
)
from courier_engine import (
    initial_fen, make_move, check_game_over, get_legal_moves, square_name,
)
import chess

print(f"Neural network active: {_nn_available}\n")


def play_game(white_fn, black_fn, verbose=False):
    """Play one Courier Run game. Returns ('white'|'black'|'draw', reason, moves)."""
    fen = initial_fen()
    w_sq = pick_courier_for_ai(fen, 'white')
    b_sq = pick_courier_for_ai(fen, 'black')
    turn_count = 0
    move_num = 0
    _tt.clear()

    while True:
        over, winner, reason = check_game_over(fen, w_sq, b_sq, turn_count)
        if over:
            return winner, reason, move_num

        board = chess.Board(fen)
        is_white = board.turn == chess.WHITE

        if is_white:
            move = white_fn(fen, w_sq, b_sq, turn_count)
        else:
            move = black_fn(fen, w_sq, b_sq, turn_count)

        if move is None:
            return 'draw', 'no_moves', move_num

        result = make_move(fen, move.uci(), w_sq, b_sq)
        fen = result['fen']
        w_sq = result['courier_white_sq']
        b_sq = result['courier_black_sq']

        if not is_white:
            turn_count += 1
        move_num += 1


def random_player(fen, w_sq, b_sq, tc):
    legal = get_legal_moves(fen, w_sq, b_sq)
    return random.choice(legal) if legal else None


def greedy_player(fen, w_sq, b_sq, tc):
    """Picks the move with the best immediate evaluation (no lookahead)."""
    legal = get_legal_moves(fen, w_sq, b_sq)
    if not legal:
        return None
    board = chess.Board(fen)
    color = chess.WHITE if board.turn == chess.WHITE else chess.BLACK
    best_score = -999999
    best_move = legal[0]
    for m in legal:
        r = make_move(fen, m.uci(), w_sq, b_sq)
        s = evaluate(r['fen'], r['courier_white_sq'], r['courier_black_sq'], tc, color)
        if s > best_score:
            best_score = s
            best_move = m
    return best_move


def enoch_d2(fen, w_sq, b_sq, tc):
    return pick_move_minimax(fen, w_sq, b_sq, tc, depth=2, time_limit=1.0)


def enoch_d3(fen, w_sq, b_sq, tc):
    return pick_move_minimax(fen, w_sq, b_sq, tc, depth=3, time_limit=2.0)


def run_matchup(name, white_fn, black_fn, n_games=10):
    print(f"--- {name} ({n_games} games) ---")
    results = {'white': 0, 'black': 0, 'draw': 0}
    reasons = {}
    total_moves = 0
    t0 = time.time()

    for i in range(n_games):
        winner, reason, moves = play_game(white_fn, black_fn)
        w = winner if winner else 'draw'
        results[w] = results.get(w, 0) + 1
        reasons[reason] = reasons.get(reason, 0) + 1
        total_moves += moves
        elapsed = time.time() - t0
        print(f"  Game {i+1}: {w} ({reason}, {moves} moves) [{elapsed:.0f}s elapsed]")

    elapsed = time.time() - t0
    print(f"\nResults: White {results['white']}  Black {results['black']}  Draw {results['draw']}")
    print(f"Reasons: {reasons}")
    print(f"Avg moves: {total_moves / n_games:.0f}, Total time: {elapsed:.0f}s\n")
    return results


# Test 1: Enoch (depth 3) as White vs Random as Black
print("=" * 60)
r1 = run_matchup("Enoch d3 (White) vs Random (Black)", enoch_d3, random_player, n_games=5)

# Test 2: Enoch (depth 3) as Black vs Random as White
print("=" * 60)
r2 = run_matchup("Random (White) vs Enoch d3 (Black)", random_player, enoch_d3, n_games=5)

# Test 3: Enoch (depth 3) vs Greedy (depth 0 but uses the eval function)
print("=" * 60)
r3 = run_matchup("Enoch d3 (White) vs Greedy (Black)", enoch_d3, greedy_player, n_games=3)

# Test 4: Enoch d3 vs Enoch d2 (to show depth matters)
print("=" * 60)
r4 = run_matchup("Enoch d3 (White) vs Enoch d2 (Black)", enoch_d3, enoch_d2, n_games=3)

# Summary
print("=" * 60)
print("STRENGTH SUMMARY")
print("=" * 60)
enoch_vs_random = r1['white'] + r2['black']
total_random = 10
print(f"Enoch d3 vs Random:   {enoch_vs_random}/{total_random} wins ({enoch_vs_random/total_random*100:.0f}%)")
print(f"Enoch d3 vs Greedy:   {r3['white']}/3 wins")
print(f"Enoch d3 vs Enoch d2: {r4['white']}/3 wins")
print()

if enoch_vs_random >= 9:
    print("-> Enoch dominates random players (expected for any decent AI)")
if r3['white'] >= 2:
    print("-> Enoch's search depth gives a real edge over pure evaluation")
print(f"\nNN active: {_nn_available}")
