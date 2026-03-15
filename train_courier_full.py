#!/usr/bin/env python3
"""Courier Run — Full AI training pipeline.

Combines fast heuristic self-play with Ollama position evaluation
to train a neural network for Enoch's Courier Run AI.

Pipeline:
  1. Fast self-play (depth 1-2) generates thousands of positions
  2. Ollama evaluates a subset of mid/late-game positions
  3. CNN trains on combined data (game outcomes + LLM evaluations)
  4. Export weights for live use

Usage:
  python train_courier_full.py                     # full pipeline
  python train_courier_full.py --skip-ollama       # self-play + train only
  python train_courier_full.py --games 500         # more self-play games
  python train_courier_full.py --evals 300         # more LLM evaluations
"""

import argparse
import json
import os
import random
import sys
import time
from datetime import datetime

import chess

_root = os.path.dirname(os.path.abspath(__file__))
_svc = os.path.join(_root, "app", "services")
sys.path.insert(0, _svc)
sys.path.insert(0, _root)

from courier_engine import (
    initial_fen, get_legal_moves, make_move, check_game_over,
    parse_square, square_name, PIECE_VALUES, courier_distance_to_goal,
    TURN_CAP,
)
from courier_ai import (
    pick_move_minimax, pick_courier_for_ai, evaluate, _tt,
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
    print("ERROR: PyTorch is required. pip install torch numpy")
    sys.exit(1)

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
DATA_DIR = os.path.join("data", "courier_training")
GAMES_DIR = os.path.join(DATA_DIR, "games")
EVALS_DIR = os.path.join(DATA_DIR, "ollama_evals")

PIECE_PLANES = {
    'P': 0, 'N': 1, 'B': 2, 'R': 3, 'Q': 4, 'K': 5,
    'p': 6, 'n': 7, 'b': 8, 'r': 9, 'q': 10, 'k': 11,
}


# ══════════════════════════════════════════════════════════════
#  STEP 1: FAST SELF-PLAY
# ══════════════════════════════════════════════════════════════

def _fast_move(fen, cw_sq, cb_sq, turn_count):
    """Fast semi-random move with tactical awareness."""
    legal = get_legal_moves(fen, cw_sq, cb_sq)
    if not legal:
        return None
    board = chess.Board(fen)
    for_color = board.turn
    my_courier = cw_sq if for_color == chess.WHITE else cb_sq
    enemy_courier = cb_sq if for_color == chess.WHITE else cw_sq

    # Priority 1: capture enemy courier (instant win)
    for m in legal:
        if m.to_square == enemy_courier:
            return m

    # Priority 2: deliver courier to back rank
    goal_rank = 7 if for_color == chess.WHITE else 0
    if my_courier is not None:
        for m in legal:
            if m.from_square == my_courier and chess.square_rank(m.to_square) == goal_rank:
                return m

    # Priority 3: score moves with simple heuristics + noise
    scored = []
    for m in legal:
        s = random.gauss(0, 50)
        captured = board.piece_at(m.to_square)
        if captured:
            s += PIECE_VALUES.get(captured.piece_type, 100)
        if my_courier is not None and m.from_square == my_courier:
            if for_color == chess.WHITE:
                s += (chess.square_rank(m.to_square) - chess.square_rank(m.from_square)) * 30
            else:
                s += (chess.square_rank(m.from_square) - chess.square_rank(m.to_square)) * 30
        if enemy_courier is not None:
            dist = abs(chess.square_file(m.to_square) - chess.square_file(enemy_courier)) + \
                   abs(chess.square_rank(m.to_square) - chess.square_rank(enemy_courier))
            s += max(0, 5 - dist) * 10
        scored.append((s, m))

    scored.sort(key=lambda x: x[0], reverse=True)
    # Pick from top 3 with weighted random
    top = scored[:min(3, len(scored))]
    weights = [max(s + 200, 1) for s, _ in top]
    total = sum(weights)
    r = random.random() * total
    for w, (_, m) in zip(weights, top):
        r -= w
        if r <= 0:
            return m
    return top[0][1]


def self_play_game():
    """Play one fast self-play game."""
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
            for pos in positions:
                pos['result'] = result if pos['turn'] == 'white' else -result
            return positions, winner, reason, move_num

        current_turn = 'white' if board.turn == chess.WHITE else 'black'

        positions.append({
            'fen': fen,
            'cw': square_name(w_sq) if w_sq is not None else None,
            'cb': square_name(b_sq) if b_sq is not None else None,
            'turn': current_turn,
            'turn_count': turn_count,
            'result': 0.0,
        })

        move = _fast_move(fen, w_sq, b_sq, turn_count)

        if move is None:
            for pos in positions:
                pos['result'] = 0.0
            return positions, 'draw', 'no_moves', move_num

        result = make_move(fen, move.uci(), w_sq, b_sq)
        fen = result['fen']
        board = chess.Board(fen)
        w_sq = result['courier_white_sq']
        b_sq = result['courier_black_sq']

        if current_turn == 'black':
            turn_count += 1
        move_num += 1


def run_self_play(num_games=200):
    """Run many fast self-play games."""
    os.makedirs(GAMES_DIR, exist_ok=True)

    stats = {'white': 0, 'black': 0, 'draw': 0}
    all_positions = []
    t0 = time.time()

    for g in range(num_games):
        positions, winner, reason, moves = self_play_game()
        all_positions.extend(positions)
        stats[winner] += 1

        if (g + 1) % 10 == 0:
            elapsed = time.time() - t0
            rate = (g + 1) / elapsed
            eta = (num_games - g - 1) / rate
            print(f"  Game {g+1}/{num_games}  "
                  f"({len(all_positions)} positions, "
                  f"{elapsed:.0f}s, {rate:.1f} g/s, "
                  f"ETA {eta:.0f}s)")

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    outfile = os.path.join(GAMES_DIR, f"selfplay_{timestamp}_{num_games}g.json")

    data = [{
        'fen': p['fen'], 'cw': p['cw'], 'cb': p['cb'],
        'turn': p['turn'], 'turn_count': p.get('turn_count', 0),
        'result': p['result'],
    } for p in all_positions]

    with open(outfile, 'w') as f:
        json.dump(data, f)

    elapsed = time.time() - t0
    print(f"\n  {len(all_positions)} positions from {num_games} games in {elapsed:.0f}s")
    print(f"  Results: W={stats['white']} B={stats['black']} D={stats['draw']}")
    print(f"  Saved: {outfile}")
    return outfile


# ══════════════════════════════════════════════════════════════
#  STEP 2: OLLAMA POSITION EVALUATION
# ══════════════════════════════════════════════════════════════

COURIER_RULES_SHORT = """COURIER RUN: Chess variant where each side picks a pawn as Courier.
Win by: (1) delivering your Courier to enemy back rank, or (2) capturing enemy Courier.
No check/checkmate/castling/en passant/promotion. King is just a piece. 80-turn cap with tiebreaks."""


def _board_to_text(fen, cw_sq, cb_sq):
    """Render board as text for the LLM."""
    board = chess.Board(fen)
    lines = ["    a   b   c   d   e   f   g   h",
             "  +---+---+---+---+---+---+---+---+"]
    for rank in range(7, -1, -1):
        row = f"{rank+1} |"
        for file in range(8):
            sq = chess.square(file, rank)
            p = board.piece_at(sq)
            if p:
                sym = p.symbol()
                is_c = (cw_sq is not None and sq == cw_sq) or \
                       (cb_sq is not None and sq == cb_sq)
                cell = f"[{sym}]" if is_c else f" {sym} "
            else:
                cell = "   "
            row += cell + "|"
        row += f" {rank+1}"
        lines.append(row)
        lines.append("  +---+---+---+---+---+---+---+---+")
    lines.append("    a   b   c   d   e   f   g   h")
    return "\n".join(lines)


def _ollama_chat(model, prompt, temperature=0.1):
    """Single Ollama chat call with generous timeout."""
    try:
        resp = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "options": {"temperature": temperature, "num_predict": 256},
            },
            timeout=180,
        )
        if resp.status_code == 200:
            return resp.json().get("message", {}).get("content", "")
        return None
    except Exception as e:
        print(f"    Ollama error: {e}")
        return None


def _parse_eval(response):
    """Extract a float in [-1.0, 1.0] from LLM response."""
    if not response:
        return None
    import re
    for pat in [
        r'(?:score|evaluation|eval|rating|value)[:\s]+([-+]?\d*\.?\d+)',
        r'\*\*([-+]?\d*\.?\d+)\*\*',
        r'([-+]?\d*\.\d+)',
    ]:
        for m in re.findall(pat, response):
            try:
                v = float(m)
                if -1.0 <= v <= 1.0:
                    return v
            except ValueError:
                continue
    return None


def evaluate_with_ollama(model, positions, num_evals=200):
    """Have the LLM evaluate sampled positions."""
    os.makedirs(EVALS_DIR, exist_ok=True)

    random.shuffle(positions)
    mid_late = [p for p in positions if p.get('turn_count', 0) >= 3]
    if len(mid_late) < num_evals:
        mid_late = positions
    sampled = mid_late[:num_evals]

    evaluated = []
    t0 = time.time()
    successes = 0

    for i, pos in enumerate(sampled):
        cw = parse_square(pos['cw']) if pos['cw'] else None
        cb = parse_square(pos['cb']) if pos['cb'] else None
        tc = pos.get('turn_count', 0)

        board = chess.Board(pos['fen'])
        side = "White" if board.turn == chess.WHITE else "Black"
        board_text = _board_to_text(pos['fen'], cw, cb)

        w_dist = courier_distance_to_goal(cw, 'white') if cw is not None else 99
        b_dist = courier_distance_to_goal(cb, 'black') if cb is not None else 99

        prompt = f"""{COURIER_RULES_SHORT}

Position (Turn {tc+1}/80, {side} to move):
{board_text}

White Courier: {square_name(cw) if cw is not None else 'CAPTURED'} ({w_dist} ranks from goal)
Black Courier: {square_name(cb) if cb is not None else 'CAPTURED'} ({b_dist} ranks from goal)

Evaluate for the side to move. Scale: -1.0 (losing) to +1.0 (winning).
Consider: courier distance, safety, piece activity, material.
Reply with ONLY a number between -1.0 and +1.0."""

        response = _ollama_chat(model, prompt)
        val = _parse_eval(response)

        if val is not None:
            pos_copy = dict(pos)
            pos_copy['llm_eval'] = val
            evaluated.append(pos_copy)
            successes += 1

        if (i + 1) % 10 == 0:
            elapsed = time.time() - t0
            rate = (i + 1) / elapsed
            eta = (len(sampled) - i - 1) / rate if rate > 0 else 0
            print(f"  Evaluated {i+1}/{len(sampled)} "
                  f"({successes} ok, {elapsed:.0f}s, ETA {eta:.0f}s)")

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    outfile = os.path.join(EVALS_DIR, f"evals_{timestamp}_{len(evaluated)}pos.json")
    with open(outfile, 'w') as f:
        json.dump(evaluated, f)

    elapsed = time.time() - t0
    print(f"\n  {len(evaluated)} evaluations saved in {elapsed:.0f}s")
    print(f"  Success rate: {successes}/{len(sampled)} ({successes/max(len(sampled),1)*100:.0f}%)")
    print(f"  Saved: {outfile}")
    return outfile


# ══════════════════════════════════════════════════════════════
#  STEP 3: NEURAL NETWORK TRAINING
# ══════════════════════════════════════════════════════════════

def board_to_tensor(fen, cw_sq, cb_sq):
    """14-plane 8x8 tensor: 12 pieces + 2 courier markers."""
    planes = np.zeros((14, 8, 8), dtype=np.float32)
    board = chess.Board(fen)
    for sq in chess.SQUARES:
        p = board.piece_at(sq)
        if p:
            idx = PIECE_PLANES.get(p.symbol())
            if idx is not None:
                planes[idx][chess.square_rank(sq)][chess.square_file(sq)] = 1.0
    if cw_sq is not None:
        planes[12][chess.square_rank(cw_sq)][chess.square_file(cw_sq)] = 1.0
    if cb_sq is not None:
        planes[13][chess.square_rank(cb_sq)][chess.square_file(cb_sq)] = 1.0
    return planes


class CourierNet(nn.Module):
    """Residual CNN for Courier Run evaluation."""
    def __init__(self, num_filters=128, num_blocks=4):
        super().__init__()
        self.input_conv = nn.Conv2d(14, num_filters, 3, padding=1)
        self.input_bn = nn.BatchNorm2d(num_filters)
        self.res_blocks = nn.ModuleList()
        for _ in range(num_blocks):
            self.res_blocks.append(nn.Sequential(
                nn.Conv2d(num_filters, num_filters, 3, padding=1),
                nn.BatchNorm2d(num_filters),
                nn.ReLU(inplace=True),
                nn.Conv2d(num_filters, num_filters, 3, padding=1),
                nn.BatchNorm2d(num_filters),
            ))
        self.value_conv = nn.Conv2d(num_filters, 4, 1)
        self.value_bn = nn.BatchNorm2d(4)
        self.value_fc1 = nn.Linear(4 * 8 * 8, 128)
        self.value_fc2 = nn.Linear(128, 1)

    def forward(self, x):
        x = F.relu(self.input_bn(self.input_conv(x)))
        for block in self.res_blocks:
            residual = x
            x = block(x)
            x = F.relu(x + residual)
        v = F.relu(self.value_bn(self.value_conv(x)))
        v = v.view(v.size(0), -1)
        v = F.relu(self.value_fc1(v))
        v = torch.tanh(self.value_fc2(v))
        return v


def load_all_data():
    """Load all game and evaluation data."""
    all_data = []

    for d in (GAMES_DIR,):
        if not os.path.exists(d):
            continue
        for f in os.listdir(d):
            if f.endswith('.json'):
                with open(os.path.join(d, f)) as fh:
                    for pos in json.load(fh):
                        all_data.append({
                            'fen': pos['fen'],
                            'cw': pos.get('cw'),
                            'cb': pos.get('cb'),
                            'target': pos['result'],
                            'weight': 1.0,
                        })

    if os.path.exists(EVALS_DIR):
        for f in os.listdir(EVALS_DIR):
            if f.endswith('.json'):
                with open(os.path.join(EVALS_DIR, f)) as fh:
                    for pos in json.load(fh):
                        if 'llm_eval' in pos:
                            all_data.append({
                                'fen': pos['fen'],
                                'cw': pos.get('cw'),
                                'cb': pos.get('cb'),
                                'target': pos['llm_eval'],
                                'weight': 3.0,
                            })

    return all_data


def train_network(epochs=40, batch_size=256, lr=0.001):
    """Train the value network on all data."""
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"  Device: {device}")
    if device.type == 'cuda':
        print(f"  GPU: {torch.cuda.get_device_name(0)}")

    all_data = load_all_data()
    if not all_data:
        print("  No training data found.")
        return None

    random.shuffle(all_data)
    print(f"  Total samples: {len(all_data)}")

    game_count = sum(1 for d in all_data if d['weight'] == 1.0)
    llm_count = sum(1 for d in all_data if d['weight'] == 3.0)
    print(f"  Game outcomes: {game_count}, LLM evaluations: {llm_count}")

    X_list, y_list, w_list = [], [], []
    for d in all_data:
        cw = parse_square(d['cw']) if d['cw'] else None
        cb = parse_square(d['cb']) if d['cb'] else None
        X_list.append(board_to_tensor(d['fen'], cw, cb))
        y_list.append(d['target'])
        w_list.append(d['weight'])

    X = torch.tensor(np.array(X_list), dtype=torch.float32)
    y = torch.tensor(y_list, dtype=torch.float32).unsqueeze(1)
    w = torch.tensor(w_list, dtype=torch.float32).unsqueeze(1)

    n = len(X)
    split = int(n * 0.9)
    X_train, X_val = X[:split].to(device), X[split:].to(device)
    y_train, y_val = y[:split].to(device), y[split:].to(device)
    w_train = w[:split].to(device)

    model = CourierNet(num_filters=128, num_blocks=4).to(device)

    checkpoint_path = os.path.join(DATA_DIR, "courier_net_latest.pt")
    if os.path.exists(checkpoint_path):
        try:
            model.load_state_dict(torch.load(checkpoint_path, map_location=device, weights_only=True))
            print("  Resumed from checkpoint")
        except Exception:
            print("  Fresh model (checkpoint incompatible)")

    optimizer = optim.Adam(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)

    train_ds = torch.utils.data.TensorDataset(X_train, y_train, w_train)
    train_loader = torch.utils.data.DataLoader(
        train_ds, batch_size=batch_size, shuffle=True, pin_memory=False)

    best_val = float('inf')
    t0 = time.time()

    for epoch in range(epochs):
        model.train()
        total_loss = 0
        batches = 0
        for xb, yb, wb in train_loader:
            pred = model(xb)
            loss = (wb * (pred - yb) ** 2).mean()
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
            batches += 1

        model.eval()
        with torch.no_grad():
            val_pred = model(X_val)
            val_loss = ((val_pred - y_val) ** 2).mean().item()

        avg_train = total_loss / max(batches, 1)
        lr_now = scheduler.get_last_lr()[0]

        marker = " *" if val_loss < best_val else ""
        print(f"  Epoch {epoch+1:3d}/{epochs}  "
              f"Train: {avg_train:.6f}  Val: {val_loss:.6f}  "
              f"LR: {lr_now:.6f}{marker}")

        if val_loss < best_val:
            best_val = val_loss
            torch.save(model.state_dict(), checkpoint_path)

        scheduler.step()

    elapsed = time.time() - t0
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    torch.save(model.state_dict(), os.path.join(DATA_DIR, f"courier_net_{ts}.pt"))
    torch.save(model.state_dict(), checkpoint_path)
    print(f"\n  Training done in {elapsed:.0f}s. Best val loss: {best_val:.6f}")
    return model


def export_for_live():
    """Export trained weights as TorchScript for the live AI."""
    checkpoint = os.path.join(DATA_DIR, "courier_net_latest.pt")
    if not os.path.exists(checkpoint):
        print("  No trained model found.")
        return False

    export_path = os.path.join("app", "services", "courier_weights.pt")
    model = CourierNet(num_filters=128, num_blocks=4)
    model.load_state_dict(torch.load(checkpoint, map_location='cpu', weights_only=True))
    model.eval()

    dummy = torch.randn(1, 14, 8, 8)
    traced = torch.jit.trace(model, dummy)
    traced.save(export_path)

    size_mb = os.path.getsize(export_path) / (1024 * 1024)
    print(f"  Exported to {export_path} ({size_mb:.1f} MB)")
    return True


# ══════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Courier Run — Full Training Pipeline")
    parser.add_argument("--games", type=int, default=200,
                        help="Self-play games to generate (default: 200)")
    parser.add_argument("--evals", type=int, default=200,
                        help="Positions for LLM to evaluate (default: 200)")
    parser.add_argument("--epochs", type=int, default=40,
                        help="NN training epochs (default: 40)")
    parser.add_argument("--model", default="mistral-nemo:12b",
                        help="Ollama model name")
    parser.add_argument("--skip-ollama", action="store_true",
                        help="Skip Ollama evaluation step")
    parser.add_argument("--skip-selfplay", action="store_true",
                        help="Skip self-play (use existing data)")
    parser.add_argument("--train-only", action="store_true",
                        help="Only train + export on existing data")
    args = parser.parse_args()

    for d in (DATA_DIR, GAMES_DIR, EVALS_DIR):
        os.makedirs(d, exist_ok=True)

    print("=" * 60)
    print("COURIER RUN — AI TRAINING PIPELINE")
    print("=" * 60)

    all_positions = []

    # Step 1: Self-play
    if not args.train_only and not args.skip_selfplay:
        print(f"\n{'='*60}")
        print(f"STEP 1: Self-play ({args.games} games, depth 1-2)")
        print(f"{'='*60}")
        outfile = run_self_play(args.games)
        with open(outfile) as f:
            all_positions = json.load(f)
    else:
        for f in os.listdir(GAMES_DIR):
            if f.endswith('.json'):
                with open(os.path.join(GAMES_DIR, f)) as fh:
                    all_positions.extend(json.load(fh))
        if all_positions:
            print(f"\n  Loaded {len(all_positions)} existing positions")

    # Step 2: Ollama evaluation
    if not args.train_only and not args.skip_ollama and all_positions:
        if not HAS_REQUESTS:
            print("\n  Skipping Ollama (requests not installed)")
        else:
            try:
                resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
                if resp.status_code == 200:
                    models = [m['name'] for m in resp.json().get('models', [])]
                    print(f"\n{'='*60}")
                    print(f"STEP 2: Ollama evaluation ({args.evals} positions)")
                    print(f"  Model: {args.model}")
                    print(f"  Available: {', '.join(models)}")
                    print(f"{'='*60}")
                    evaluate_with_ollama(args.model, all_positions, args.evals)
                else:
                    print("\n  Ollama not responding, skipping evaluations")
            except Exception:
                print("\n  Ollama not available, skipping evaluations")

    # Step 3: Train
    print(f"\n{'='*60}")
    print(f"STEP 3: Training neural network ({args.epochs} epochs)")
    print(f"{'='*60}")
    model = train_network(epochs=args.epochs)

    if model is not None:
        # Step 4: Export
        print(f"\n{'='*60}")
        print("STEP 4: Exporting for live AI")
        print(f"{'='*60}")
        export_for_live()

    print(f"\n{'='*60}")
    print("DONE! Enoch's Courier Run AI has been trained.")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
