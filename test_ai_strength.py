"""Test Enoch's Courier Run AI strength."""
import sys, os, time
sys.path.insert(0, os.path.join('app', 'services'))
from courier_ai import _nn_available, evaluate, pick_move_minimax, pick_courier_for_ai, _tt
from courier_engine import initial_fen, make_move, check_game_over, square_name
import chess

print(f"Neural network active: {_nn_available}")
print()

results = {"white": 0, "black": 0, "draw": 0}
game_lengths = []

for g in range(10):
    _tt.clear()
    fen = initial_fen()
    board = chess.Board(fen)
    w_sq = pick_courier_for_ai(fen, "white")
    b_sq = pick_courier_for_ai(fen, "black")

    turn_count = 0
    move_num = 0

    while True:
        over, winner, reason = check_game_over(fen, w_sq, b_sq, turn_count)
        if over:
            results[winner] += 1
            game_lengths.append(move_num)
            w_name = square_name(w_sq) if w_sq else "CAPTURED"
            b_name = square_name(b_sq) if b_sq else "CAPTURED"
            print(f"Game {g+1}: {winner} wins ({reason}) in {move_num} moves  "
                  f"[W courier={w_name} B courier={b_name}]")
            break

        current = "white" if board.turn == chess.WHITE else "black"

        # White = Enoch (depth 4, NN-enhanced) — the AI players face
        # Black = weaker opponent simulating a human (depth 2, shorter time)
        if current == "white":
            move = pick_move_minimax(fen, w_sq, b_sq, turn_count, depth=4, time_limit=2.0)
        else:
            move = pick_move_minimax(fen, w_sq, b_sq, turn_count, depth=2, time_limit=0.5)

        if move is None:
            results["draw"] += 1
            game_lengths.append(move_num)
            print(f"Game {g+1}: draw (no moves) in {move_num} moves")
            break

        result = make_move(fen, move.uci(), w_sq, b_sq)
        fen = result["fen"]
        board = chess.Board(fen)
        w_sq = result["courier_white_sq"]
        b_sq = result["courier_black_sq"]

        if current == "black":
            turn_count += 1
        move_num += 1

print()
print("=== RESULTS (Enoch depth-4 vs Opponent depth-2) ===")
print(f"Enoch (White, depth-4):  {results['white']} wins")
print(f"Opponent (Black, depth-2): {results['black']} wins")
print(f"Draws:                     {results['draw']}")
avg = sum(game_lengths) / max(len(game_lengths), 1)
print(f"Avg game length: {avg:.0f} moves")
print(f"Enoch win rate: {results['white']/10*100:.0f}%")
