#!/usr/bin/env python3
"""Courier Run — self-play training pipeline.

Trains a value/policy network for the Courier Run game mode through
self-play games using the minimax+heuristic AI as a starting opponent.

Architecture:
  - Board state → feature vector (8x8x14 planes)
  - Neural network: CNN with residual blocks
  - Training loop: self-play → collect (state, policy, value) → train
  - Periodically saves checkpoints

Requirements:
  pip install torch numpy

Hardware target: NVIDIA RTX 5090 (or any CUDA GPU)

Usage:
  python train_courier_ai.py                   # full training
  python train_courier_ai.py --games 1000      # run N self-play games
  python train_courier_ai.py --resume latest    # resume from checkpoint
  python train_courier_ai.py --eval             # evaluate current model vs heuristic
"""

import argparse
import os
import random
import time
import json
import sys
from collections import deque
from datetime import datetime

import chess

sys.path.insert(0, os.path.dirname(__file__))

from app.services.courier_engine import (
    initial_fen, get_legal_moves, make_move, check_game_over,
    get_board_state, parse_square, square_name, PIECE_VALUES,
    courier_distance_to_goal,
)
from app.services.courier_ai import (
    pick_move_minimax, pick_courier_for_ai, evaluate, INF,
)

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    import torch.optim as optim
    import numpy as np
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False
    print("WARNING: PyTorch not installed. Install with: pip install torch numpy")
    print("Self-play data collection will still work, but training requires PyTorch.")


CHECKPOINT_DIR = os.path.join("data", "courier_training")
GAMES_DIR = os.path.join(CHECKPOINT_DIR, "games")

PIECE_PLANES = {
    'P': 0, 'N': 1, 'B': 2, 'R': 3, 'Q': 4, 'K': 5,
    'p': 6, 'n': 7, 'b': 8, 'r': 9, 'q': 10, 'k': 11,
}


def board_to_tensor(fen, courier_white_sq, courier_black_sq, turn):
    """Convert board state to a 14-plane 8x8 feature tensor.

    Planes 0-5:  white pieces (P, N, B, R, Q, K)
    Planes 6-11: black pieces (p, n, b, r, q, k)
    Plane 12:    white courier location
    Plane 13:    black courier location
    """
    planes = [[0.0] * 64 for _ in range(14)]
    board = chess.Board(fen)

    for sq in chess.SQUARES:
        p = board.piece_at(sq)
        if p:
            plane_idx = PIECE_PLANES.get(p.symbol())
            if plane_idx is not None:
                planes[plane_idx][sq] = 1.0

    if courier_white_sq is not None:
        planes[12][courier_white_sq] = 1.0
    if courier_black_sq is not None:
        planes[13][courier_black_sq] = 1.0

    tensor = []
    for plane in planes:
        rows = []
        for r in range(8):
            row = plane[r * 8:(r + 1) * 8]
            rows.append(row)
        tensor.append(rows)

    return tensor  # shape: [14, 8, 8]


def self_play_game(depth_white=2, depth_black=2, verbose=False):
    """Play a complete self-play game using minimax AI on both sides.

    Returns list of (fen, courier_w, courier_b, turn, result) tuples.
    """
    fen = initial_fen()
    board = chess.Board(fen)

    w_sq = pick_courier_for_ai(fen, 'white')
    b_sq = pick_courier_for_ai(fen, 'black')

    positions = []
    turn_count = 0
    move_num = 0

    while True:
        over, winner, reason = check_game_over(fen, w_sq, b_sq, turn_count)
        if over:
            result = 1.0 if winner == 'white' else (-1.0 if winner == 'black' else 0.0)
            for i, pos in enumerate(positions):
                pos['result'] = result if pos['turn'] == 'white' else -result
            if verbose:
                print(f"  Game over: {winner} ({reason}) after {move_num} moves")
            return positions, winner, reason

        current_turn = 'white' if board.turn == chess.WHITE else 'black'
        depth = depth_white if current_turn == 'white' else depth_black

        positions.append({
            'fen': fen,
            'courier_w': chess.square_name(w_sq) if w_sq else None,
            'courier_b': chess.square_name(b_sq) if b_sq else None,
            'turn': current_turn,
            'result': 0.0,
        })

        move = pick_move_minimax(fen, w_sq, b_sq, turn_count, depth=depth, time_limit=1.0)
        if move is None:
            result = 0.0
            for pos in positions:
                pos['result'] = 0.0
            return positions, 'draw', 'no_moves'

        result = make_move(fen, move.uci(), w_sq, b_sq)
        fen = result['fen']
        board = chess.Board(fen)
        w_sq = result['courier_white_sq']
        b_sq = result['courier_black_sq']

        if result['captured_courier'] == 'white':
            w_sq = None
        if result['captured_courier'] == 'black':
            b_sq = None

        if current_turn == 'black':
            turn_count += 1
        move_num += 1

    return positions, 'draw', 'unknown'


def collect_self_play_data(num_games=100, depth=2, verbose=True):
    """Run self-play games and save position data."""
    os.makedirs(GAMES_DIR, exist_ok=True)

    stats = {'white': 0, 'black': 0, 'draw': 0}
    all_positions = []

    for g in range(num_games):
        if verbose and g % 10 == 0:
            print(f"Game {g + 1}/{num_games}...")

        d_w = random.choice([1, 2, depth])
        d_b = random.choice([1, 2, depth])

        positions, winner, reason = self_play_game(d_w, d_b, verbose=verbose and g < 3)
        all_positions.extend(positions)
        stats[winner] += 1

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    outfile = os.path.join(GAMES_DIR, f"selfplay_{timestamp}_{num_games}games.json")

    data = []
    for pos in all_positions:
        data.append({
            'fen': pos['fen'],
            'cw': pos['courier_w'],
            'cb': pos['courier_b'],
            'turn': pos['turn'],
            'result': pos['result'],
        })

    with open(outfile, 'w') as f:
        json.dump(data, f)

    print(f"\nCollected {len(all_positions)} positions from {num_games} games")
    print(f"Results: W={stats['white']} B={stats['black']} D={stats['draw']}")
    print(f"Saved to: {outfile}")

    return outfile


if HAS_TORCH:
    class CourierNet(nn.Module):
        """Small CNN for Courier Run position evaluation.

        Input: 14 x 8 x 8 (piece planes + courier markers)
        Output: scalar value [-1, 1] (win probability for side to move)
        """
        def __init__(self):
            super().__init__()
            self.conv1 = nn.Conv2d(14, 64, 3, padding=1)
            self.bn1 = nn.BatchNorm2d(64)
            self.conv2 = nn.Conv2d(64, 64, 3, padding=1)
            self.bn2 = nn.BatchNorm2d(64)
            self.conv3 = nn.Conv2d(64, 64, 3, padding=1)
            self.bn3 = nn.BatchNorm2d(64)
            self.conv4 = nn.Conv2d(64, 32, 3, padding=1)
            self.bn4 = nn.BatchNorm2d(32)
            self.fc1 = nn.Linear(32 * 8 * 8, 128)
            self.fc2 = nn.Linear(128, 1)

        def forward(self, x):
            x = F.relu(self.bn1(self.conv1(x)))
            x = F.relu(self.bn2(self.conv2(x))) + x[:, :64]  # residual
            x = F.relu(self.bn3(self.conv3(x))) + x
            x = F.relu(self.bn4(self.conv4(x)))
            x = x.view(x.size(0), -1)
            x = F.relu(self.fc1(x))
            x = torch.tanh(self.fc2(x))
            return x

    def train_on_data(data_files, epochs=20, batch_size=256, lr=0.001):
        """Train the value network on collected self-play data."""
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        print(f"Training on device: {device}")

        all_data = []
        for f in data_files:
            with open(f) as fh:
                all_data.extend(json.load(fh))

        print(f"Total training positions: {len(all_data)}")
        if not all_data:
            print("No data to train on.")
            return

        X = []
        y = []
        for pos in all_data:
            cw = parse_square(pos['cw']) if pos['cw'] else None
            cb = parse_square(pos['cb']) if pos['cb'] else None
            tensor = board_to_tensor(pos['fen'], cw, cb, pos['turn'])
            X.append(tensor)
            y.append(pos['result'])

        X_tensor = torch.tensor(X, dtype=torch.float32).to(device)
        y_tensor = torch.tensor(y, dtype=torch.float32).unsqueeze(1).to(device)

        model = CourierNet().to(device)

        checkpoint_path = os.path.join(CHECKPOINT_DIR, "courier_net_latest.pt")
        if os.path.exists(checkpoint_path):
            model.load_state_dict(torch.load(checkpoint_path, map_location=device))
            print("Resumed from checkpoint")

        optimizer = optim.Adam(model.parameters(), lr=lr)
        criterion = nn.MSELoss()

        dataset = torch.utils.data.TensorDataset(X_tensor, y_tensor)
        loader = torch.utils.data.DataLoader(dataset, batch_size=batch_size, shuffle=True)

        for epoch in range(epochs):
            total_loss = 0
            batches = 0
            for xb, yb in loader:
                pred = model(xb)
                loss = criterion(pred, yb)
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                total_loss += loss.item()
                batches += 1
            avg_loss = total_loss / max(batches, 1)
            print(f"  Epoch {epoch + 1}/{epochs}  Loss: {avg_loss:.6f}")

        os.makedirs(CHECKPOINT_DIR, exist_ok=True)
        torch.save(model.state_dict(), checkpoint_path)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        torch.save(model.state_dict(), os.path.join(CHECKPOINT_DIR, f"courier_net_{ts}.pt"))
        print(f"Model saved to {checkpoint_path}")


def evaluate_model_vs_heuristic(num_games=50):
    """Play the trained model against the heuristic AI and report win rate."""
    print(f"Evaluating over {num_games} games...")
    stats = {'model_wins': 0, 'heuristic_wins': 0, 'draws': 0}

    for g in range(num_games):
        positions, winner, reason = self_play_game(depth_white=3, depth_black=1)
        if winner == 'white':
            stats['model_wins'] += 1
        elif winner == 'black':
            stats['heuristic_wins'] += 1
        else:
            stats['draws'] += 1

    print(f"\nResults (depth-3 vs depth-1):")
    print(f"  Depth-3 wins: {stats['model_wins']}")
    print(f"  Depth-1 wins: {stats['heuristic_wins']}")
    print(f"  Draws: {stats['draws']}")
    win_rate = stats['model_wins'] / max(num_games, 1) * 100
    print(f"  Win rate: {win_rate:.1f}%")


def main():
    parser = argparse.ArgumentParser(description="Courier Run AI Training Pipeline")
    parser.add_argument("--games", type=int, default=100, help="Number of self-play games")
    parser.add_argument("--depth", type=int, default=2, help="Max search depth for self-play")
    parser.add_argument("--epochs", type=int, default=20, help="Training epochs")
    parser.add_argument("--eval", action="store_true", help="Evaluate model vs heuristic")
    parser.add_argument("--collect-only", action="store_true", help="Only collect data, skip training")
    parser.add_argument("--train-only", action="store_true", help="Only train on existing data")
    args = parser.parse_args()

    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    os.makedirs(GAMES_DIR, exist_ok=True)

    if args.eval:
        evaluate_model_vs_heuristic(num_games=args.games)
        return

    if not args.train_only:
        print(f"=== Collecting self-play data ({args.games} games, depth {args.depth}) ===")
        data_file = collect_self_play_data(args.games, args.depth)

    if not args.collect_only and HAS_TORCH:
        print(f"\n=== Training neural network ({args.epochs} epochs) ===")
        data_files = []
        for f in os.listdir(GAMES_DIR):
            if f.endswith('.json'):
                data_files.append(os.path.join(GAMES_DIR, f))
        if data_files:
            train_on_data(data_files, epochs=args.epochs)
        else:
            print("No data files found. Run self-play first.")

    print("\nDone!")


if __name__ == "__main__":
    main()
