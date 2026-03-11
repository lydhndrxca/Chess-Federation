"""Routes for The Reckoning — four-player chess."""

import json
import random
from datetime import datetime, timezone, timedelta

from flask import Blueprint, jsonify, render_template, request, url_for
from flask_login import current_user, login_required

from app.models import FourPlayerGame, FourPlayerMove, User, db
from app.services.four_player_engine import (
    initial_state, serialize, deserialize,
    get_legal_moves, make_move, is_game_over, get_rankings,
    compute_scores, board_to_grid, move_to_str, parse_move_str,
    get_material, get_piece_count, COLORS, piece_color, piece_type,
    ZOMBIE_STARTS, _key,
)
from app.services.four_player_ai import (
    pick_reckoning_move, COMMENTARY,
    get_current_mood,
)

fp_bp = Blueprint('four_player', __name__)

ENOCH_SEAT = 'north'
HUMAN_SEATS = ['south', 'west', 'east']
SEAT_LABELS = {'south': 'South', 'west': 'West', 'north': 'North', 'east': 'East'}
TURN_TIMEOUT = timedelta(hours=4)

ENOCH_AUTO_MOVE_LINES = [
    "Four hours. FOUR HOURS. I have been pacing in the dark, listening to the silence of your indecision. I moved your piece. You're welcome.",
    "You left the board unattended. I reached up through the grate and nudged your piece myself. Do not let this happen again.",
    "The clock ran dry. I could not bear it any longer. I chose a move for you. It is… adequate. Barely.",
    "I waited. And waited. The spiders built a web across your seat. I brushed it aside and moved your piece. Wake up.",
    "Your hesitation is an insult to the wood. I have made your move. Next time, show some urgency.",
    "The board was growing cold. I intervened. Consider this a kindness from the sub-basement.",
    "I gave you four hours. You gave me nothing. So I reached up and moved your piece with my own damp hand.",
    "Time expired. Enoch does not wait. Enoch acts. Your piece has been relocated. You may thank me later.",
]

COLOR_MAP = {
    'south': '#f5f5f5',
    'west': '#4a9eff',
    'north': '#f0c040',
    'east': '#ff5252',
    'zombie': '#4aff4a',
}


def _get_enoch():
    return User.query.filter_by(username='Enoch', is_bot=True).first()


def _active_reckoning():
    """Return the current open (waiting or active) Reckoning, if any."""
    game = FourPlayerGame.query.filter(
        FourPlayerGame.status.in_(['waiting', 'active'])
    ).order_by(FourPlayerGame.created_at.desc()).first()
    if game:
        _ensure_zombies(game)
    return game


def _ensure_zombies(game):
    """Inject zombie pawns into a game created before zombie support was added."""
    state = deserialize(game.board_state)
    board = state['board']
    has_zombies = any(v.startswith('z') for v in board.values())
    if has_zombies:
        return
    for r, c in ZOMBIE_STARTS:
        k = _key(r, c)
        if k not in board:
            board[k] = 'zP'
    game.board_state = serialize(state)
    db.session.commit()


def _play_enoch_turns(game):
    """If it's Enoch's turn, play moves until it's a human's turn or game over."""
    enoch = _get_enoch()
    if not enoch:
        return

    state = deserialize(game.board_state)
    mood = get_current_mood()

    max_iter = 4
    while max_iter > 0 and not is_game_over(state):
        if game.seat_for_user(enoch.id) != state['turn']:
            break
        enoch_color = state['turn']

        move, commentary = pick_reckoning_move(state, enoch_color, mood['key'])
        if not move:
            break

        state, captured = make_move(
            state, move['from'][0], move['from'][1],
            move['to'][0], move['to'][1], move.get('promo'),
        )

        fm = FourPlayerMove(
            game_id=game.id,
            move_number=state['move_count'],
            color=enoch_color,
            move_str=move_to_str(move),
            captured=captured,
            commentary=commentary,
        )
        db.session.add(fm)
        game.board_state = serialize(state)
        game.current_turn = state['turn']
        game.move_count = state['move_count']
        max_iter -= 1

    game.turn_started_at = datetime.now(timezone.utc)

    if is_game_over(state):
        _finish_game(game, state)

    db.session.commit()


def _check_turn_timeout(game):
    """If the current player hasn't moved in 4 hours, Enoch makes a move for them."""
    if game.status != 'active':
        return False
    if not game.turn_started_at:
        game.turn_started_at = datetime.now(timezone.utc)
        db.session.commit()
        return False

    now = datetime.now(timezone.utc)
    started = game.turn_started_at
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    if now - started < TURN_TIMEOUT:
        return False

    state = deserialize(game.board_state)
    idle_seat = state['turn']

    enoch = _get_enoch()
    if enoch and game.seat_for_user(enoch.id) == idle_seat:
        return False

    legal = get_legal_moves(state, idle_seat)
    if not legal:
        return False

    move = random.choice(legal)
    state, captured = make_move(
        state, move['from'][0], move['from'][1],
        move['to'][0], move['to'][1], move.get('promo'),
    )

    commentary = random.choice(ENOCH_AUTO_MOVE_LINES)
    fm = FourPlayerMove(
        game_id=game.id,
        move_number=state['move_count'],
        color=idle_seat,
        move_str=move_to_str(move),
        captured=captured,
        commentary=commentary,
    )
    db.session.add(fm)

    game.board_state = serialize(state)
    game.current_turn = state['turn']
    game.move_count = state['move_count']
    game.eliminated = json.dumps(state['eliminated'])
    game.turn_started_at = datetime.now(timezone.utc)

    if is_game_over(state):
        _finish_game(game, state)
    else:
        _play_enoch_turns(game)

    db.session.commit()
    return True


def _finish_game(game, state, timed_out=False):
    rankings = get_rankings(state)
    scores = compute_scores(state, timed_out=timed_out)

    game.status = 'completed'
    game.completed_at = datetime.now(timezone.utc)
    game.result_order = json.dumps(rankings)
    game.scores = json.dumps(scores)
    game.board_state = serialize(state)
    game.eliminated = json.dumps(state['eliminated'])

    enoch = _get_enoch()
    for color, points in scores.items():
        if points <= 0:
            continue
        uid = getattr(game, f'{color}_id')
        if uid and (not enoch or uid != enoch.id):
            user = db.session.get(User, uid)
            if user:
                user.rating = (user.rating or 200) + points


# ── Page routes ─────────────────────────────────────────────────

@fp_bp.route('/reckoning')
@login_required
def reckoning_lobby():
    game = _active_reckoning()
    if game and game.status == 'active' and game.seat_for_user(current_user.id):
        return _render_game(game)
    if game and game.status == 'waiting' and game.seat_for_user(current_user.id):
        return _render_waiting(game)
    if game and game.status == 'waiting':
        return _render_waiting(game)
    return _render_no_game()


@fp_bp.route('/reckoning/<int:game_id>')
@login_required
def view_reckoning(game_id):
    game = FourPlayerGame.query.get_or_404(game_id)
    _ensure_zombies(game)
    if game.status == 'waiting':
        return _render_waiting(game)
    return _render_game(game)


def _render_no_game():
    return render_template('four_player.html',
                           mode='lobby', game=None,
                           enoch_mood=get_current_mood())


def _render_waiting(game):
    players = _game_players(game)
    return render_template('four_player.html',
                           mode='waiting', game=game, players=players,
                           enoch_mood=get_current_mood(),
                           my_seat=game.seat_for_user(current_user.id))


def _render_game(game):
    _check_turn_timeout(game)
    state = deserialize(game.board_state)
    players = _game_players(game)
    my_seat = game.seat_for_user(current_user.id)
    is_my_turn = (my_seat == state['turn']) if my_seat else False
    legal = get_legal_moves(state) if is_my_turn else []

    moves_by_str = {}
    for m in legal:
        fk = f"{m['from'][0]},{m['from'][1]}"
        moves_by_str.setdefault(fk, []).append(move_to_str(m))

    grid = board_to_grid(state)
    recent_moves = FourPlayerMove.query.filter_by(game_id=game.id)\
        .order_by(FourPlayerMove.id.desc()).limit(20).all()
    recent_moves.reverse()

    material = {c: get_material(state, c) for c in COLORS if c not in state['eliminated']}

    game_over = is_game_over(state)
    rankings = get_rankings(state) if game_over else None
    scores = json.loads(game.scores) if game.scores else None

    turn_deadline = None
    if game.turn_started_at and game.status == 'active':
        ts = game.turn_started_at
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        turn_deadline = (ts + TURN_TIMEOUT).isoformat()

    automove_taunt = None
    if my_seat and game.status == 'active':
        last_move = FourPlayerMove.query.filter_by(game_id=game.id)\
            .order_by(FourPlayerMove.id.desc()).first()
        if last_move and last_move.commentary in ENOCH_AUTO_MOVE_LINES \
                and last_move.color == my_seat:
            from app.services.dialogue import RECKONING_AUTOMOVE_TAUNT
            automove_taunt = random.choice(RECKONING_AUTOMOVE_TAUNT)

    return render_template('four_player.html',
                           mode='game', game=game, state=state,
                           grid=grid, players=players,
                           my_seat=my_seat, is_my_turn=is_my_turn,
                           legal_moves=json.dumps(moves_by_str),
                           recent_moves=recent_moves,
                           material=material,
                           color_map=COLOR_MAP,
                           enoch_mood=get_current_mood(),
                           game_over=game_over,
                           rankings=rankings, scores=scores,
                           seat_labels=SEAT_LABELS,
                           turn_deadline=turn_deadline,
                           automove_taunt=automove_taunt)


def _game_players(game):
    players = {}
    for seat in COLORS:
        uid = getattr(game, f'{seat}_id')
        if uid:
            players[seat] = db.session.get(User, uid)
    return players


# ── API routes ──────────────────────────────────────────────────

@fp_bp.route('/reckoning/join', methods=['POST'])
@login_required
def join_reckoning():
    enoch = _get_enoch()
    game = _active_reckoning()

    if game and game.seat_for_user(current_user.id):
        return jsonify({'url': url_for('four_player.view_reckoning', game_id=game.id)})

    if not game:
        game = FourPlayerGame(
            status='waiting',
            board_state=serialize(initial_state()),
        )
        if enoch:
            setattr(game, f'{ENOCH_SEAT}_id', enoch.id)
        db.session.add(game)
        db.session.flush()

    open_seats = [s for s in HUMAN_SEATS if getattr(game, f'{s}_id') is None]
    if not open_seats:
        return jsonify({'error': 'Game is full'}), 400

    seat = open_seats[0]
    setattr(game, f'{seat}_id', current_user.id)

    if game.filled_seats() >= 4:
        game.status = 'active'
        game.started_at = datetime.now(timezone.utc)
        game.turn_started_at = datetime.now(timezone.utc)

        start_line = random.choice(COMMENTARY['game_start'])
        start_msg = FourPlayerMove(
            game_id=game.id, move_number=0,
            color='north', move_str='--',
            commentary=start_line,
        )
        db.session.add(start_msg)

        if state_turn_is_enoch(game):
            db.session.commit()
            _play_enoch_turns(game)
        else:
            db.session.commit()
    else:
        db.session.commit()

    return jsonify({'url': url_for('four_player.view_reckoning', game_id=game.id)})


def state_turn_is_enoch(game):
    enoch = _get_enoch()
    if not enoch:
        return False
    state = deserialize(game.board_state)
    seat = game.seat_for_user(enoch.id)
    return seat == state['turn']


@fp_bp.route('/reckoning/<int:game_id>/move', methods=['POST'])
@login_required
def make_reckoning_move(game_id):
    game = FourPlayerGame.query.get_or_404(game_id)
    if game.status != 'active':
        return jsonify({'error': 'Game is not active'}), 400

    state = deserialize(game.board_state)
    my_seat = game.seat_for_user(current_user.id)
    if not my_seat or my_seat != state['turn']:
        return jsonify({'error': 'Not your turn'}), 400

    data = request.get_json()
    move_str = data.get('move', '')
    try:
        fr, fc, tr, tc, promo = parse_move_str(move_str)
        state, captured = make_move(state, fr, fc, tr, tc, promo)
    except (ValueError, IndexError) as e:
        return jsonify({'error': str(e)}), 400

    old_eliminated = json.loads(game.eliminated) if game.eliminated else []
    new_eliminated = state['eliminated']

    commentary = random.choice(COMMENTARY['general'])
    if captured:
        commentary = random.choice(COMMENTARY['player_captures'])

    fm = FourPlayerMove(
        game_id=game.id,
        move_number=state['move_count'],
        color=my_seat,
        move_str=move_str,
        captured=captured,
        commentary=commentary,
    )
    db.session.add(fm)

    for elim_color in new_eliminated:
        if elim_color not in old_eliminated:
            enoch = _get_enoch()
            enoch_seat = game.seat_for_user(enoch.id) if enoch else None
            if elim_color == enoch_seat:
                elim_line = random.choice(COMMENTARY['enoch_eliminated'])
            else:
                elim_line = random.choice(COMMENTARY['elimination'])
            elim_msg = FourPlayerMove(
                game_id=game.id, move_number=state['move_count'],
                color='north', move_str='--',
                commentary=elim_line,
            )
            db.session.add(elim_msg)

    game.board_state = serialize(state)
    game.current_turn = state['turn']
    game.move_count = state['move_count']
    game.eliminated = json.dumps(state['eliminated'])
    game.turn_started_at = datetime.now(timezone.utc)

    if is_game_over(state):
        _finish_game(game, state)
        db.session.commit()
        return jsonify({
            'success': True,
            'game_over': True,
            'rankings': get_rankings(state),
            'scores': compute_scores(state),
        })

    db.session.commit()

    _play_enoch_turns(game)
    game = db.session.get(FourPlayerGame, game_id)
    state = deserialize(game.board_state)

    recent = FourPlayerMove.query.filter_by(game_id=game.id)\
        .order_by(FourPlayerMove.id.desc()).limit(5).all()

    return jsonify({
        'success': True,
        'game_over': is_game_over(state),
        'state': _state_payload(game, state),
        'recent_moves': [{
            'color': m.color,
            'move_str': m.move_str,
            'captured': m.captured,
            'commentary': m.commentary,
            'number': m.move_number,
        } for m in reversed(recent)],
    })


@fp_bp.route('/reckoning/<int:game_id>/state')
@login_required
def reckoning_state(game_id):
    game = FourPlayerGame.query.get_or_404(game_id)
    _ensure_zombies(game)
    _check_turn_timeout(game)
    game = db.session.get(FourPlayerGame, game_id)
    state = deserialize(game.board_state)

    recent = FourPlayerMove.query.filter_by(game_id=game.id)\
        .order_by(FourPlayerMove.id.desc()).limit(5).all()

    my_seat = game.seat_for_user(current_user.id)
    is_my_turn = (my_seat == state['turn']) if my_seat else False

    turn_deadline = None
    if game.turn_started_at and game.status == 'active':
        ts = game.turn_started_at
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        turn_deadline = (ts + TURN_TIMEOUT).isoformat()

    return jsonify({
        'status': game.status,
        'move_count': game.move_count,
        'current_turn': state['turn'],
        'is_my_turn': is_my_turn,
        'game_over': game.status == 'completed',
        'state': _state_payload(game, state),
        'recent_moves': [{
            'color': m.color,
            'move_str': m.move_str,
            'captured': m.captured,
            'commentary': m.commentary,
            'number': m.move_number,
        } for m in reversed(recent)],
        'filled_seats': game.filled_seats(),
        'rankings': json.loads(game.result_order) if game.result_order else None,
        'scores': json.loads(game.scores) if game.scores else None,
        'turn_deadline': turn_deadline,
    })


def _state_payload(game, state):
    grid = board_to_grid(state)
    legal = {}
    my_seat = game.seat_for_user(current_user.id) if current_user.is_authenticated else None
    if my_seat and my_seat == state['turn'] and game.status == 'active':
        for m in get_legal_moves(state, my_seat):
            fk = f"{m['from'][0]},{m['from'][1]}"
            legal.setdefault(fk, []).append(move_to_str(m))

    return {
        'grid': grid,
        'turn': state['turn'],
        'eliminated': state['eliminated'],
        'legal': legal,
        'material': {c: get_material(state, c) for c in COLORS if c not in state['eliminated']},
    }
