"""Routes for Courier Run — Enoch's escort game mode."""

import random
from datetime import datetime, timezone

from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user, login_required

from app.models import CourierGame, db
from app.services.courier_engine import (
    initial_fen, get_pawn_squares, get_legal_moves_dests,
    make_move, check_game_over, parse_square,
    square_name, courier_distance_to_goal,
)
from app.services.courier_ai import (
    pick_move_minimax, pick_courier_for_ai,
)
from app.services.courier_dialogue import (
    COURIER_GAME_START, COURIER_SELECTION, COURIER_PLAYER_ADVANCE,
    COURIER_AI_ADVANCE, COURIER_PLAYER_THREAT, COURIER_AI_THREAT,
    COURIER_CAPTURE, COURIER_CAPTURED_BY_PLAYER, COURIER_DELIVERY_WIN,
    COURIER_DELIVERY_LOSS, COURIER_TIEBREAK, COURIER_DRAW, COURIER_IDLE,
)

courier_bp = Blueprint('courier', __name__)

REWARD_DOLLARS = 50
MAX_DAILY_GAMES = 3


def _daily_game_count(user_id):
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    return CourierGame.query.filter(
        CourierGame.user_id == user_id,
        CourierGame.started_at >= today_start,
    ).count()


def _line(pool):
    return random.choice(pool)


# ── Page ──

@courier_bp.route('/courier')
@login_required
def courier_page():
    active = CourierGame.query.filter_by(
        user_id=current_user.id, status='selecting'
    ).first() or CourierGame.query.filter_by(
        user_id=current_user.id, status='active'
    ).first()

    daily_count = _daily_game_count(current_user.id)
    can_play = daily_count < MAX_DAILY_GAMES

    return render_template(
        'courier.html',
        active_game=active,
        daily_count=daily_count,
        max_daily=MAX_DAILY_GAMES,
        can_play=can_play,
        reward=REWARD_DOLLARS,
    )


# ── API: New Game ──

@courier_bp.route('/courier/api/new', methods=['POST'])
@login_required
def api_new_game():
    daily = _daily_game_count(current_user.id)
    if daily >= MAX_DAILY_GAMES:
        return jsonify(error='Daily limit reached (3 games).'), 400

    existing = CourierGame.query.filter(
        CourierGame.user_id == current_user.id,
        CourierGame.status.in_(['selecting', 'active']),
    ).first()
    if existing:
        return jsonify(error='You already have an active Courier Run.'), 400

    game = CourierGame(
        user_id=current_user.id,
        fen=initial_fen(),
        status='selecting',
    )
    db.session.add(game)
    db.session.commit()

    pawns = get_pawn_squares(game.fen, 'white')

    return jsonify(
        ok=True,
        game_id=game.id,
        pawns=pawns,
        enoch=_line(COURIER_GAME_START),
    )


# ── API: Select Courier ──

@courier_bp.route('/courier/api/<int:game_id>/select', methods=['POST'])
@login_required
def api_select_courier(game_id):
    game = CourierGame.query.filter_by(
        id=game_id, user_id=current_user.id, status='selecting',
    ).first()
    if not game:
        return jsonify(error='Game not found.'), 404

    data = request.get_json(force=True)
    sq_name = data.get('square', '').strip().lower()

    pawns = get_pawn_squares(game.fen, 'white')
    if sq_name not in pawns:
        return jsonify(error='Invalid pawn square.'), 400

    game.courier_white_sq = sq_name

    # AI picks its courier
    ai_sq = pick_courier_for_ai(game.fen, 'black')
    game.courier_black_sq = square_name(ai_sq) if ai_sq else 'e7'

    game.status = 'active'
    db.session.commit()

    w_sq = parse_square(game.courier_white_sq)
    b_sq = parse_square(game.courier_black_sq)
    dests = get_legal_moves_dests(game.fen, w_sq, b_sq)

    return jsonify(
        ok=True,
        courier_white=game.courier_white_sq,
        courier_black=game.courier_black_sq,
        dests=dests,
        turn='white',
        enoch=_line(COURIER_SELECTION),
    )


# ── API: Make Move ──

@courier_bp.route('/courier/api/<int:game_id>/move', methods=['POST'])
@login_required
def api_move(game_id):
    game = CourierGame.query.filter_by(
        id=game_id, user_id=current_user.id, status='active',
    ).first()
    if not game:
        return jsonify(error='Game not found.'), 404
    if game.turn != 'white':
        return jsonify(error='Not your turn.'), 400

    data = request.get_json(force=True)
    uci = data.get('uci', '').strip()
    if not uci:
        return jsonify(error='Missing move.'), 400

    w_sq = parse_square(game.courier_white_sq) if game.courier_white_sq else None
    b_sq = parse_square(game.courier_black_sq) if game.courier_black_sq else None

    try:
        result = make_move(game.fen, uci, w_sq, b_sq)
    except ValueError as e:
        return jsonify(error=str(e)), 400

    game.fen = result['fen']
    game.turn = result['turn']
    game.move_count += 1
    if game.courier_white_sq and result['courier_white_sq'] is not None:
        game.courier_white_sq = square_name(result['courier_white_sq'])
    if result['captured_courier'] == 'black':
        game.courier_black_sq = None
    if result['courier_black_sq'] is not None and game.courier_black_sq:
        game.courier_black_sq = square_name(result['courier_black_sq'])

    history = game.move_history or ''
    game.move_history = (history + ',' + uci) if history else uci

    # Check game over after player move
    new_w = parse_square(game.courier_white_sq) if game.courier_white_sq else None
    new_b = parse_square(game.courier_black_sq) if game.courier_black_sq else None

    over, winner, reason = check_game_over(game.fen, new_w, new_b, game.turn_count)
    if over:
        return _finish_game(game, winner, reason, result)

    # Enoch's turn
    enoch_result, enoch_line = _make_enoch_move(game)
    if enoch_result is None:
        db.session.commit()
        dests = get_legal_moves_dests(game.fen, new_w, new_b)
        return jsonify(
            ok=True,
            player_san=result['san'],
            player_from=result['from_sq'],
            player_to=result['to_sq'],
            enoch_move=None,
            fen=game.fen,
            courier_white=game.courier_white_sq,
            courier_black=game.courier_black_sq,
            dests=dests,
            turn_count=game.turn_count,
            move_count=game.move_count,
            game_over=False,
            enoch=_line(COURIER_IDLE),
        )

    return enoch_result


def _make_enoch_move(game):
    """AI makes a move for black."""
    w_sq = parse_square(game.courier_white_sq) if game.courier_white_sq else None
    b_sq = parse_square(game.courier_black_sq) if game.courier_black_sq else None

    ai_move = pick_move_minimax(game.fen, w_sq, b_sq, game.turn_count, depth=4, time_limit=3.0)
    if ai_move is None:
        over, winner, reason = check_game_over(game.fen, w_sq, b_sq, game.turn_count)
        if over:
            return _finish_game(game, winner, reason, {
                'from_sq': '', 'to_sq': '', 'san': '',
            }), None
        return None, None

    try:
        result = make_move(game.fen, ai_move.uci(), w_sq, b_sq)
    except ValueError:
        return None, None

    game.fen = result['fen']
    game.turn = result['turn']
    game.move_count += 1
    game.turn_count += 1  # increment after black moves

    if result['captured_courier'] == 'white':
        game.courier_white_sq = None
    if game.courier_white_sq and result['courier_white_sq'] is not None:
        game.courier_white_sq = square_name(result['courier_white_sq'])
    if game.courier_black_sq and result['courier_black_sq'] is not None:
        game.courier_black_sq = square_name(result['courier_black_sq'])

    history = game.move_history or ''
    game.move_history = (history + ',' + ai_move.uci()) if history else ai_move.uci()

    new_w = parse_square(game.courier_white_sq) if game.courier_white_sq else None
    new_b = parse_square(game.courier_black_sq) if game.courier_black_sq else None

    over, winner, reason = check_game_over(game.fen, new_w, new_b, game.turn_count)
    if over:
        return _finish_game(game, winner, reason, result, enoch_uci=ai_move.uci()), None

    # Pick commentary
    enoch_line = _pick_commentary(result, game)

    db.session.commit()

    dests = get_legal_moves_dests(game.fen, new_w, new_b)

    resp = jsonify(
        ok=True,
        player_san=None,
        enoch_move={
            'from': result['from_sq'],
            'to': result['to_sq'],
            'san': result['san'],
        },
        fen=game.fen,
        courier_white=game.courier_white_sq,
        courier_black=game.courier_black_sq,
        dests=dests,
        turn_count=game.turn_count,
        move_count=game.move_count,
        game_over=False,
        enoch=enoch_line,
    )
    return resp, enoch_line


def _pick_commentary(result, game):
    """Select an appropriate Enoch quip based on what happened."""
    if result['captured_courier'] == 'white':
        return _line(COURIER_CAPTURE)
    if result['courier_delivered'] == 'black':
        return _line(COURIER_DELIVERY_LOSS)

    b_sq = parse_square(game.courier_black_sq) if game.courier_black_sq else None
    if b_sq is not None:
        dist = courier_distance_to_goal(b_sq, 'black')
        if dist <= 2:
            return _line(COURIER_AI_ADVANCE)

    return _line(COURIER_IDLE)


def _finish_game(game, winner, reason, last_result, enoch_uci=None):
    """Finalize a completed game and pay reward if player won."""
    game.status = 'completed'
    game.winner = winner
    game.end_reason = reason
    game.completed_at = datetime.now(timezone.utc)

    reward = 0
    player_won = (winner == 'white')
    if player_won and not game.reward_paid:
        game.reward_paid = True
        current_user.roman_gold += REWARD_DOLLARS
        reward = REWARD_DOLLARS

    db.session.commit()

    if winner == 'draw':
        enoch = _line(COURIER_DRAW)
    elif player_won:
        if reason == 'courier_delivered':
            enoch = _line(COURIER_DELIVERY_WIN)
        else:
            enoch = _line(COURIER_CAPTURED_BY_PLAYER)
    else:
        if reason == 'courier_delivered':
            enoch = _line(COURIER_DELIVERY_LOSS)
        else:
            enoch = _line(COURIER_CAPTURE)

    resp = {
        'ok': True,
        'game_over': True,
        'winner': winner,
        'end_reason': reason,
        'reward': reward,
        'enoch': enoch,
        'fen': game.fen,
        'courier_white': game.courier_white_sq,
        'courier_black': game.courier_black_sq,
        'turn_count': game.turn_count,
        'move_count': game.move_count,
    }
    if last_result.get('from_sq') and last_result.get('to_sq'):
        if enoch_uci:
            resp['enoch_move'] = {
                'from': last_result['from_sq'],
                'to': last_result['to_sq'],
                'san': last_result['san'],
            }
        else:
            resp['player_from'] = last_result['from_sq']
            resp['player_to'] = last_result['to_sq']
            resp['player_san'] = last_result['san']

    return jsonify(resp)


# ── API: Game State ──

@courier_bp.route('/courier/api/<int:game_id>/state')
@login_required
def api_state(game_id):
    game = CourierGame.query.filter_by(
        id=game_id, user_id=current_user.id,
    ).first()
    if not game:
        return jsonify(error='Game not found.'), 404

    w_sq = parse_square(game.courier_white_sq) if game.courier_white_sq else None
    b_sq = parse_square(game.courier_black_sq) if game.courier_black_sq else None

    dests = {}
    if game.status == 'active' and game.turn == 'white':
        dests = get_legal_moves_dests(game.fen, w_sq, b_sq)

    return jsonify(
        game_id=game.id,
        status=game.status,
        fen=game.fen,
        courier_white=game.courier_white_sq,
        courier_black=game.courier_black_sq,
        turn=game.turn,
        turn_count=game.turn_count,
        move_count=game.move_count,
        dests=dests,
        winner=game.winner,
        end_reason=game.end_reason,
    )
