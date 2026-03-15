#!/usr/bin/env python3
"""Courier Run — Ollama-powered AI training pipeline.

Uses a local LLM (via Ollama) to play Courier Run games and generate
high-quality position evaluations, then trains a lightweight CNN that
runs in the live game as Enoch's brain for this mode.

Pipeline:
  1. LLM plays full games (LLM vs heuristic, LLM vs LLM)
  2. LLM evaluates sampled positions with reasoning
  3. CNN trains on (board_state → evaluation) pairs
  4. Trained weights exported for live use

Requirements:
  pip install torch numpy requests

Hardware: NVIDIA RTX 5090 (CUDA) + Ollama running locally

Usage:
  python train_courier_ollama.py                          # full pipeline
  python train_courier_ollama.py --llm-games 200          # LLM plays 200 games
  python train_courier_ollama.py --evaluate-positions 500  # LLM scores 500 positions
  python train_courier_ollama.py --train-only              # train on existing data
  python train_courier_ollama.py --export                  # export weights for live AI
  python train_courier_ollama.py --model mistral           # use specific Ollama model
  python train_courier_ollama.py --benchmark               # test LLM vs heuristic
"""

import argparse
import json
import os
import random
import re
import sys
import time
from datetime import datetime

import chess
import requests

# Insert services dir so we can import engine/ai without triggering Flask app init
_root = os.path.dirname(os.path.abspath(__file__))
_svc = os.path.join(_root, "app", "services")
sys.path.insert(0, _svc)
sys.path.insert(0, _root)

from courier_engine import (
    initial_fen, get_legal_moves, make_move, check_game_over,
    parse_square, square_name, PIECE_VALUES, courier_distance_to_goal,
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

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
DEFAULT_MODEL = "mistral"

DATA_DIR = os.path.join("data", "courier_training")
GAMES_DIR = os.path.join(DATA_DIR, "ollama_games")
EVALS_DIR = os.path.join(DATA_DIR, "ollama_evals")
CHECKPOINT_DIR = DATA_DIR

PIECE_SYMBOLS = {
    'P': '♙', 'N': '♘', 'B': '♗', 'R': '♖', 'Q': '♕', 'K': '♔',
    'p': '♟', 'n': '♞', 'b': '♝', 'r': '♜', 'q': '♛', 'k': '♚',
}

COURIER_RULES = """COURIER RUN RULES:
- Standard 8x8 chess board with all normal pieces
- Each side has designated one pawn as their "Courier"
- All pieces move normally (standard chess movement)
- There is NO check, NO checkmate, NO castling, NO en passant, NO promotion
- The king is just another piece — it cannot be checked or checkmated
- WIN CONDITIONS: Deliver your Courier pawn to the enemy's back rank (rank 8 for White, rank 1 for Black) OR capture the enemy's Courier pawn
- If 80 full turns pass: the side whose Courier is closer to the goal wins; if tied, higher material wins; if still tied, draw
- The Courier pawn is marked with [C] on the board

STRATEGY GUIDANCE:
- Escort your Courier forward while blocking the enemy Courier
- Use pieces to screen (protect) your Courier's advance
- Look for opportunities to capture the enemy Courier
- Sacrifice material if it helps your Courier advance or stops the enemy's
- Control the lanes (files) around both Couriers
- The king is free to participate since there is no check — use it!
- Pawns flanking the Courier provide diagonal capture defense
- Knights and bishops are excellent escorts and interceptors"""


def _board_to_text(fen, courier_white_sq, courier_black_sq):
    """Render the board as readable text for the LLM."""
    board = chess.Board(fen)
    lines = []
    lines.append("    a   b   c   d   e   f   g   h")
    lines.append("  +---+---+---+---+---+---+---+---+")
    for rank in range(7, -1, -1):
        row = f"{rank+1} |"
        for file in range(8):
            sq = chess.square(file, rank)
            p = board.piece_at(sq)
            if p:
                sym = p.symbol()
                is_courier = False
                if courier_white_sq is not None and sq == courier_white_sq:
                    is_courier = True
                if courier_black_sq is not None and sq == courier_black_sq:
                    is_courier = True
                if is_courier:
                    cell = f"[{sym}]"
                else:
                    cell = f" {sym} "
            else:
                cell = "   "
            row += cell + "|"
        row += f" {rank+1}"
        lines.append(row)
        lines.append("  +---+---+---+---+---+---+---+---+")
    lines.append("    a   b   c   d   e   f   g   h")
    return "\n".join(lines)


def _legal_moves_text(fen, courier_white_sq, courier_black_sq):
    """Format legal moves for the LLM."""
    legal = get_legal_moves(fen, courier_white_sq, courier_black_sq)
    board = chess.Board(fen)
    moves = []
    my_courier = courier_white_sq if board.turn == chess.WHITE else courier_black_sq
    enemy_courier = courier_black_sq if board.turn == chess.WHITE else courier_white_sq

    for m in legal:
        uci = m.uci()
        piece = board.piece_at(m.from_square)
        piece_name = chess.piece_name(piece.piece_type).capitalize() if piece else "?"
        is_capture = board.piece_at(m.to_square) is not None
        is_courier_move = m.from_square == my_courier
        captures_courier = is_capture and m.to_square == enemy_courier

        label = uci
        if is_courier_move:
            label += " (COURIER move)"
        if captures_courier:
            label += " (CAPTURES enemy Courier!)"
        elif is_capture:
            label += " (capture)"

        moves.append(label)

    return moves


def _ollama_chat(model, messages, temperature=0.3):
    """Send a chat request to Ollama and return the response text."""
    try:
        resp = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model": model,
                "messages": messages,
                "stream": False,
                "options": {"temperature": temperature, "num_predict": 1024},
            },
            timeout=120,
        )
        if resp.status_code == 200:
            data = resp.json()
            return data.get("message", {}).get("content", "")
        else:
            print(f"  Ollama error {resp.status_code}: {resp.text[:200]}")
            return None
    except requests.exceptions.ConnectionError:
        print("  ERROR: Cannot connect to Ollama. Is it running? (ollama serve)")
        return None
    except Exception as e:
        print(f"  Ollama exception: {e}")
        return None


def _parse_move_from_llm(response, legal_ucis):
    """Extract a UCI move from the LLM's response."""
    if not response:
        return None

    text = response.strip().lower()

    # Try to find a UCI move directly (e.g. e2e4, b1c3)
    for uci in legal_ucis:
        if uci in text:
            return uci

    # Try algebraic-style patterns
    move_pattern = re.findall(r'\b([a-h][1-8][a-h][1-8])\b', text)
    for m in move_pattern:
        if m in legal_ucis:
            return m

    # Look for "move: X" or "I choose X" patterns
    choice_patterns = [
        r'(?:move|choice|play|choose|pick|select)[:\s]+([a-h][1-8][a-h][1-8])',
        r'([a-h][1-8][a-h][1-8])',
    ]
    for pat in choice_patterns:
        matches = re.findall(pat, text)
        for m in matches:
            if m in legal_ucis:
                return m

    return None


def _parse_eval_from_llm(response):
    """Extract a numeric evaluation from the LLM's response."""
    if not response:
        return None

    # Look for a score between -1.0 and 1.0
    patterns = [
        r'(?:score|evaluation|eval|rating)[:\s]+([-+]?\d*\.?\d+)',
        r'([-+]?\d*\.?\d+)\s*(?:/\s*1|out of 1)',
        r'\*\*([-+]?\d*\.?\d+)\*\*',
        r':\s*([-+]?\d*\.?\d+)',
    ]
    for pat in patterns:
        matches = re.findall(pat, response)
        for m in matches:
            try:
                val = float(m)
                if -1.0 <= val <= 1.0:
                    return val
            except ValueError:
                continue

    # Fallback: look for any float in range
    all_floats = re.findall(r'([-+]?\d*\.\d+)', response)
    for f in all_floats:
        try:
            val = float(f)
            if -1.0 <= val <= 1.0:
                return val
        except ValueError:
            continue

    return None


# ══════════════════════════════════════════════════════════════
#  LLM GAME PLAYER
# ══════════════════════════════════════════════════════════════

def llm_pick_courier(model, fen, color):
    """Have the LLM choose which pawn to designate as Courier."""
    board = chess.Board(fen)
    side = chess.WHITE if color == 'white' else chess.BLACK
    pawns = list(board.pieces(chess.PAWN, side))
    pawn_names = [chess.square_name(sq) for sq in pawns]

    prompt = f"""{COURIER_RULES}

You are playing as {color.upper()}.
The board is in the starting position.

You must choose ONE of your pawns to be your Courier.
Your pawns are at: {', '.join(pawn_names)}

Consider:
- Center pawns (d,e) have more flexibility
- Look for open lanes ahead
- Flanking pawns on c,f have good diagonal support
- Edge pawns (a,h) are easier to block

Which pawn do you choose as your Courier? Reply with just the square name (e.g. "d2" or "e7")."""

    response = _ollama_chat(model, [{"role": "user", "content": prompt}])
    if response:
        text = response.strip().lower()
        for sq in pawn_names:
            if sq in text:
                return parse_square(sq)

    # Fallback to heuristic
    return pick_courier_for_ai(fen, color)


def llm_pick_move(model, fen, courier_white_sq, courier_black_sq, turn_count, move_history=""):
    """Have the LLM choose a move."""
    board = chess.Board(fen)
    color = "White" if board.turn == chess.WHITE else "Black"
    my_courier = courier_white_sq if board.turn == chess.WHITE else courier_black_sq
    enemy_courier = courier_black_sq if board.turn == chess.WHITE else courier_white_sq

    board_text = _board_to_text(fen, courier_white_sq, courier_black_sq)
    legal = get_legal_moves(fen, courier_white_sq, courier_black_sq)
    legal_ucis = [m.uci() for m in legal]
    moves_text = _legal_moves_text(fen, courier_white_sq, courier_black_sq)

    my_dist = courier_distance_to_goal(my_courier, 'white' if board.turn == chess.WHITE else 'black') if my_courier else 99
    enemy_dist = courier_distance_to_goal(enemy_courier, 'black' if board.turn == chess.WHITE else 'white') if enemy_courier else 99

    prompt = f"""{COURIER_RULES}

CURRENT POSITION (Turn {turn_count + 1}/80):
{board_text}

You are {color}. [C] marks each Courier pawn.
Your Courier: {square_name(my_courier) if my_courier else 'CAPTURED'} ({my_dist} ranks from goal)
Enemy Courier: {square_name(enemy_courier) if enemy_courier else 'CAPTURED'} ({enemy_dist} ranks from goal)

LEGAL MOVES:
{chr(10).join(moves_text[:40])}
{f'... and {len(moves_text)-40} more moves' if len(moves_text) > 40 else ''}

Think step by step:
1. Can I capture the enemy Courier this move?
2. Can I deliver my Courier this move?
3. Is my Courier in danger? How can I protect it?
4. Can I advance my Courier safely?
5. Can I block or threaten the enemy Courier?
6. What's the best move considering all factors?

Reply with your chosen move in UCI format (e.g. "e2e4"). State the move clearly."""

    response = _ollama_chat(model, [{"role": "user", "content": prompt}], temperature=0.2)
    move_uci = _parse_move_from_llm(response, legal_ucis)

    if move_uci:
        for m in legal:
            if m.uci() == move_uci:
                return m, response

    # Fallback to heuristic if LLM fails
    return pick_move_minimax(fen, courier_white_sq, courier_black_sq, turn_count, depth=2, time_limit=1.0), None


def play_llm_game(model, llm_color='both', heuristic_depth=3, verbose=True):
    """Play a complete Courier Run game with the LLM.

    llm_color: 'white', 'black', or 'both'
    """
    _tt.clear()
    fen = initial_fen()
    board = chess.Board(fen)

    if llm_color in ('white', 'both'):
        w_sq = llm_pick_courier(model, fen, 'white')
    else:
        w_sq = pick_courier_for_ai(fen, 'white')

    if llm_color in ('black', 'both'):
        b_sq = llm_pick_courier(model, fen, 'black')
    else:
        b_sq = pick_courier_for_ai(fen, 'black')

    if verbose:
        print(f"  White Courier: {square_name(w_sq)}, Black Courier: {square_name(b_sq)}")

    positions = []
    turn_count = 0
    move_num = 0
    move_history = []

    while True:
        over, winner, reason = check_game_over(fen, w_sq, b_sq, turn_count)
        if over:
            result_val = 1.0 if winner == 'white' else (-1.0 if winner == 'black' else 0.0)
            for pos in positions:
                pos['result'] = result_val if pos['turn'] == 'white' else -result_val
            if verbose:
                print(f"  Game over: {winner} ({reason}) after {move_num} moves")
            return positions, winner, reason

        current_turn = 'white' if board.turn == chess.WHITE else 'black'
        use_llm = (llm_color == 'both' or llm_color == current_turn)

        positions.append({
            'fen': fen,
            'courier_w': square_name(w_sq) if w_sq else None,
            'courier_b': square_name(b_sq) if b_sq else None,
            'turn': current_turn,
            'result': 0.0,
        })

        if use_llm:
            move, reasoning = llm_pick_move(model, fen, w_sq, b_sq, turn_count,
                                            ",".join(move_history[-10:]))
            if verbose and move:
                print(f"  [{current_turn}] LLM: {move.uci()}")
        else:
            move = pick_move_minimax(fen, w_sq, b_sq, turn_count,
                                     depth=heuristic_depth, time_limit=2.0)
            reasoning = None
            if verbose and move:
                print(f"  [{current_turn}] Heuristic: {move.uci()}")

        if move is None:
            for pos in positions:
                pos['result'] = 0.0
            return positions, 'draw', 'no_moves'

        result = make_move(fen, move.uci(), w_sq, b_sq)
        fen = result['fen']
        board = chess.Board(fen)
        w_sq = result['courier_white_sq']
        b_sq = result['courier_black_sq']
        move_history.append(move.uci())

        if current_turn == 'black':
            turn_count += 1
        move_num += 1


# ══════════════════════════════════════════════════════════════
#  LLM POSITION EVALUATOR
# ══════════════════════════════════════════════════════════════

def llm_evaluate_position(model, fen, courier_white_sq, courier_black_sq, turn_count):
    """Have the LLM evaluate a position on a -1.0 to 1.0 scale."""
    board = chess.Board(fen)
    color = "White" if board.turn == chess.WHITE else "Black"
    board_text = _board_to_text(fen, courier_white_sq, courier_black_sq)

    w_sq = courier_white_sq
    b_sq = courier_black_sq
    w_dist = courier_distance_to_goal(w_sq, 'white') if w_sq else 99
    b_dist = courier_distance_to_goal(b_sq, 'black') if b_sq else 99

    prompt = f"""{COURIER_RULES}

POSITION TO EVALUATE (Turn {turn_count + 1}/80, {color} to move):
{board_text}

White Courier: {square_name(w_sq) if w_sq else 'CAPTURED'} ({w_dist} ranks from goal)
Black Courier: {square_name(b_sq) if b_sq else 'CAPTURED'} ({b_dist} ranks from goal)

Evaluate this position for the side to move on a scale from -1.0 to +1.0:
  +1.0 = winning/already won
  +0.5 = clearly better
   0.0 = equal
  -0.5 = clearly worse
  -1.0 = losing/already lost

Consider: Courier distance to goal, Courier safety, piece activity around Couriers,
interception potential, material balance, escort formation quality.

Give your evaluation as a single number between -1.0 and +1.0. Be precise."""

    response = _ollama_chat(model, [{"role": "user", "content": prompt}], temperature=0.1)
    val = _parse_eval_from_llm(response)
    return val, response


def evaluate_positions_batch(model, positions, verbose=True):
    """Evaluate a batch of positions using the LLM."""
    evaluated = []
    total = len(positions)

    for i, pos in enumerate(positions):
        if verbose and i % 10 == 0:
            print(f"  Evaluating position {i+1}/{total}...")

        cw = parse_square(pos['cw']) if pos['cw'] else None
        cb = parse_square(pos['cb']) if pos['cb'] else None
        tc = pos.get('turn_count', 0)

        val, reasoning = llm_evaluate_position(model, pos['fen'], cw, cb, tc)

        if val is not None:
            pos_copy = dict(pos)
            pos_copy['llm_eval'] = val
            evaluated.append(pos_copy)
        else:
            if verbose:
                print(f"    Failed to parse evaluation for position {i+1}")

        # Brief pause to avoid overwhelming Ollama
        time.sleep(0.1)

    return evaluated


# ══════════════════════════════════════════════════════════════
#  DATA COLLECTION
# ══════════════════════════════════════════════════════════════

def collect_llm_games(model, num_games=50, llm_color='both', heuristic_depth=3, verbose=True):
    """Play games with the LLM and save position data."""
    os.makedirs(GAMES_DIR, exist_ok=True)
    stats = {'white': 0, 'black': 0, 'draw': 0}
    all_positions = []

    for g in range(num_games):
        print(f"\n=== Game {g+1}/{num_games} ===")

        # Alternate LLM color for diversity
        if llm_color == 'alternate':
            color = 'white' if g % 2 == 0 else 'black'
        else:
            color = llm_color

        positions, winner, reason = play_llm_game(
            model, llm_color=color,
            heuristic_depth=heuristic_depth, verbose=verbose,
        )
        all_positions.extend(positions)
        stats[winner] += 1

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    outfile = os.path.join(GAMES_DIR, f"ollama_{model}_{timestamp}_{num_games}g.json")

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


def collect_llm_evaluations(model, num_positions=200, verbose=True):
    """Sample positions from existing game data and have the LLM evaluate them."""
    os.makedirs(EVALS_DIR, exist_ok=True)

    # Load existing game data
    all_positions = []
    for d in (GAMES_DIR, os.path.join(DATA_DIR, "games")):
        if not os.path.exists(d):
            continue
        for f in os.listdir(d):
            if f.endswith('.json'):
                with open(os.path.join(d, f)) as fh:
                    all_positions.extend(json.load(fh))

    if not all_positions:
        print("No existing game data found. Run --llm-games first.")
        return None

    # Sample diverse positions (avoid early game repetition)
    random.shuffle(all_positions)
    # Prefer mid-game and late-game positions
    weighted = []
    for pos in all_positions:
        board = chess.Board(pos['fen'])
        move_num = board.fullmove_number
        weight = min(move_num, 20) / 20.0  # ramp up weight with game progress
        if random.random() < weight:
            weighted.append(pos)
    sampled = weighted[:num_positions]

    print(f"Evaluating {len(sampled)} positions with LLM...")
    evaluated = evaluate_positions_batch(model, sampled, verbose=verbose)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    outfile = os.path.join(EVALS_DIR, f"evals_{model}_{timestamp}_{len(evaluated)}pos.json")

    with open(outfile, 'w') as f:
        json.dump(evaluated, f)

    print(f"Saved {len(evaluated)} evaluated positions to: {outfile}")
    return outfile


# ══════════════════════════════════════════════════════════════
#  NEURAL NETWORK TRAINING
# ══════════════════════════════════════════════════════════════

PIECE_PLANES = {
    'P': 0, 'N': 1, 'B': 2, 'R': 3, 'Q': 4, 'K': 5,
    'p': 6, 'n': 7, 'b': 8, 'r': 9, 'q': 10, 'k': 11,
}


def board_to_tensor(fen, courier_white_sq, courier_black_sq):
    """14-plane 8x8 tensor: 12 piece planes + 2 courier markers."""
    planes = np.zeros((14, 8, 8), dtype=np.float32)
    board = chess.Board(fen)

    for sq in chess.SQUARES:
        p = board.piece_at(sq)
        if p:
            plane_idx = PIECE_PLANES.get(p.symbol())
            if plane_idx is not None:
                rank = chess.square_rank(sq)
                file = chess.square_file(sq)
                planes[plane_idx][rank][file] = 1.0

    if courier_white_sq is not None:
        r, f = chess.square_rank(courier_white_sq), chess.square_file(courier_white_sq)
        planes[12][r][f] = 1.0
    if courier_black_sq is not None:
        r, f = chess.square_rank(courier_black_sq), chess.square_file(courier_black_sq)
        planes[13][r][f] = 1.0

    return planes


if HAS_TORCH:
    class CourierNet(nn.Module):
        """Residual CNN for Courier Run evaluation.

        Input: 14 x 8 x 8
        Output: scalar [-1, 1]
        """
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

    def train_network(epochs=30, batch_size=256, lr=0.001):
        """Train the value network on all collected data."""
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        print(f"Training on: {device}")
        if device.type == 'cuda':
            print(f"  GPU: {torch.cuda.get_device_name(0)}")

        # Load all data sources
        all_data = []

        # Game results (position → outcome)
        for d in (GAMES_DIR, os.path.join(DATA_DIR, "games")):
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

        # LLM evaluations (position → LLM score) — weighted higher
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
                                    'weight': 2.0,  # LLM evals are higher quality
                                })

        if not all_data:
            print("No training data found.")
            return

        random.shuffle(all_data)
        print(f"Total training samples: {len(all_data)}")

        # Build tensors
        X_list = []
        y_list = []
        w_list = []
        for d in all_data:
            cw = parse_square(d['cw']) if d['cw'] else None
            cb = parse_square(d['cb']) if d['cb'] else None
            X_list.append(board_to_tensor(d['fen'], cw, cb))
            y_list.append(d['target'])
            w_list.append(d['weight'])

        X = torch.tensor(np.array(X_list), dtype=torch.float32)
        y = torch.tensor(y_list, dtype=torch.float32).unsqueeze(1)
        w = torch.tensor(w_list, dtype=torch.float32).unsqueeze(1)

        # Train/val split
        n = len(X)
        split = int(n * 0.9)
        X_train, X_val = X[:split].to(device), X[split:].to(device)
        y_train, y_val = y[:split].to(device), y[split:].to(device)
        w_train = w[:split].to(device)

        model = CourierNet(num_filters=128, num_blocks=4).to(device)

        checkpoint_path = os.path.join(CHECKPOINT_DIR, "courier_net_latest.pt")
        if os.path.exists(checkpoint_path):
            model.load_state_dict(torch.load(checkpoint_path, map_location=device, weights_only=True))
            print("Resumed from checkpoint")

        optimizer = optim.Adam(model.parameters(), lr=lr, weight_decay=1e-4)
        scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)

        train_ds = torch.utils.data.TensorDataset(X_train, y_train, w_train)
        train_loader = torch.utils.data.DataLoader(train_ds, batch_size=batch_size, shuffle=True)

        best_val_loss = float('inf')

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

            # Validation
            model.eval()
            with torch.no_grad():
                val_pred = model(X_val)
                val_loss = ((val_pred - y_val) ** 2).mean().item()

            avg_train = total_loss / max(batches, 1)
            lr_now = scheduler.get_last_lr()[0]
            print(f"  Epoch {epoch+1}/{epochs}  Train: {avg_train:.6f}  Val: {val_loss:.6f}  LR: {lr_now:.6f}")

            if val_loss < best_val_loss:
                best_val_loss = val_loss
                torch.save(model.state_dict(), checkpoint_path)

            scheduler.step()

        # Save final + timestamped
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        torch.save(model.state_dict(), os.path.join(CHECKPOINT_DIR, f"courier_net_{ts}.pt"))
        torch.save(model.state_dict(), checkpoint_path)
        print(f"Model saved. Best val loss: {best_val_loss:.6f}")

    def export_for_live():
        """Export trained weights as a compact file for the live AI."""
        checkpoint_path = os.path.join(CHECKPOINT_DIR, "courier_net_latest.pt")
        if not os.path.exists(checkpoint_path):
            print("No trained model found. Run training first.")
            return

        export_path = os.path.join("app", "services", "courier_weights.pt")
        model = CourierNet(num_filters=128, num_blocks=4)
        model.load_state_dict(torch.load(checkpoint_path, map_location='cpu', weights_only=True))
        model.eval()

        # Save with torch.jit for faster loading
        dummy = torch.randn(1, 14, 8, 8)
        traced = torch.jit.trace(model, dummy)
        traced.save(export_path)

        size_mb = os.path.getsize(export_path) / (1024 * 1024)
        print(f"Exported to {export_path} ({size_mb:.1f} MB)")
        print("The live AI will automatically use this if present.")


# ══════════════════════════════════════════════════════════════
#  BENCHMARK
# ══════════════════════════════════════════════════════════════

def benchmark_llm_vs_heuristic(model, num_games=20, heuristic_depth=3):
    """Benchmark the LLM against the heuristic AI."""
    stats = {'llm_wins': 0, 'heuristic_wins': 0, 'draws': 0}

    for g in range(num_games):
        color = 'white' if g % 2 == 0 else 'black'
        print(f"\nGame {g+1}/{num_games} — LLM plays {color}")

        positions, winner, reason = play_llm_game(
            model, llm_color=color,
            heuristic_depth=heuristic_depth, verbose=True,
        )

        llm_won = (color == 'white' and winner == 'white') or \
                  (color == 'black' and winner == 'black')
        if winner == 'draw':
            stats['draws'] += 1
        elif llm_won:
            stats['llm_wins'] += 1
        else:
            stats['heuristic_wins'] += 1

    total = max(num_games, 1)
    print(f"\n{'='*40}")
    print(f"BENCHMARK RESULTS ({model} vs heuristic depth-{heuristic_depth}):")
    print(f"  LLM wins:       {stats['llm_wins']} ({stats['llm_wins']/total*100:.0f}%)")
    print(f"  Heuristic wins:  {stats['heuristic_wins']} ({stats['heuristic_wins']/total*100:.0f}%)")
    print(f"  Draws:           {stats['draws']} ({stats['draws']/total*100:.0f}%)")


# ══════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Courier Run — Ollama AI Training")
    parser.add_argument("--model", default=DEFAULT_MODEL,
                        help=f"Ollama model name (default: {DEFAULT_MODEL})")
    parser.add_argument("--llm-games", type=int, default=0,
                        help="Number of games for LLM to play")
    parser.add_argument("--llm-color", default="alternate",
                        choices=["white", "black", "both", "alternate"],
                        help="Which side the LLM plays")
    parser.add_argument("--evaluate-positions", type=int, default=0,
                        help="Number of positions for LLM to evaluate")
    parser.add_argument("--heuristic-depth", type=int, default=3,
                        help="Heuristic opponent search depth")
    parser.add_argument("--train-only", action="store_true",
                        help="Only train on existing data")
    parser.add_argument("--epochs", type=int, default=30,
                        help="Training epochs")
    parser.add_argument("--export", action="store_true",
                        help="Export trained model for live use")
    parser.add_argument("--benchmark", action="store_true",
                        help="Benchmark LLM vs heuristic")
    args = parser.parse_args()

    for d in (DATA_DIR, GAMES_DIR, EVALS_DIR, CHECKPOINT_DIR):
        os.makedirs(d, exist_ok=True)

    # Check Ollama is running
    if not args.train_only and not args.export:
        try:
            resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
            if resp.status_code == 200:
                models = [m['name'] for m in resp.json().get('models', [])]
                print(f"Ollama connected. Available models: {', '.join(models) or 'none'}")
                if not any(args.model in m for m in models):
                    print(f"WARNING: Model '{args.model}' not found. Pull it with: ollama pull {args.model}")
            else:
                print("WARNING: Ollama responded but may have issues.")
        except requests.exceptions.ConnectionError:
            print("ERROR: Cannot connect to Ollama at", OLLAMA_URL)
            print("Start it with: ollama serve")
            if not args.train_only:
                sys.exit(1)

    if args.benchmark:
        benchmark_llm_vs_heuristic(args.model, num_games=20,
                                    heuristic_depth=args.heuristic_depth)
        return

    if args.export:
        if HAS_TORCH:
            export_for_live()
        else:
            print("PyTorch required for export.")
        return

    # Step 1: LLM plays games
    if args.llm_games > 0:
        print(f"\n{'='*50}")
        print(f"STEP 1: LLM ({args.model}) playing {args.llm_games} games")
        print(f"{'='*50}")
        collect_llm_games(args.model, num_games=args.llm_games,
                          llm_color=args.llm_color,
                          heuristic_depth=args.heuristic_depth)

    # Step 2: LLM evaluates positions
    if args.evaluate_positions > 0:
        print(f"\n{'='*50}")
        print(f"STEP 2: LLM evaluating {args.evaluate_positions} positions")
        print(f"{'='*50}")
        collect_llm_evaluations(args.model, num_positions=args.evaluate_positions)

    # Step 3: Train neural network
    if args.train_only or args.llm_games > 0 or args.evaluate_positions > 0:
        if HAS_TORCH:
            print(f"\n{'='*50}")
            print(f"STEP 3: Training neural network ({args.epochs} epochs)")
            print(f"{'='*50}")
            train_network(epochs=args.epochs)

            print(f"\n{'='*50}")
            print("STEP 4: Exporting for live use")
            print(f"{'='*50}")
            export_for_live()
        else:
            print("\nPyTorch not installed — skipping training.")
            print("Install with: pip install torch numpy")

    # Default: run the full pipeline
    if args.llm_games == 0 and args.evaluate_positions == 0 and not args.train_only:
        print("Running full pipeline: 50 LLM games → 200 evaluations → train → export")
        print("Use --llm-games N or --evaluate-positions N to customize.\n")

        collect_llm_games(args.model, num_games=50, llm_color='alternate',
                          heuristic_depth=args.heuristic_depth)
        collect_llm_evaluations(args.model, num_positions=200)

        if HAS_TORCH:
            train_network(epochs=args.epochs)
            export_for_live()

    print("\nDone!")


if __name__ == "__main__":
    main()
