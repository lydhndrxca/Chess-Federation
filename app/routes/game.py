from datetime import datetime, timezone

from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user, login_required

from app.models import Game, Move, db
from app.services.chess_engine import ChessEngine

game_bp = Blueprint('game', __name__)


def _player_color(game):
    if current_user.id == game.white_id:
        return 'white'
    if current_user.id == game.black_id:
        return 'black'
    return None


@game_bp.route('/game/<int:game_id>')
@login_required
def view_game(game_id):
    game = Game.query.get_or_404(game_id)
    player_color = _player_color(game)

    legal_moves = []
    is_player_turn = False
    if game.status in ('pending', 'active') and player_color \
       and game.current_turn == player_color:
        legal_moves = ChessEngine.get_legal_moves(game.fen_current)
        is_player_turn = True

    board_state = ChessEngine.get_board_state(game.fen_current)
    moves = Move.query.filter_by(game_id=game.id).order_by(Move.id).all()

    deadline_iso = None
    if game.deadline:
        deadline_iso = game.deadline.strftime('%Y-%m-%dT%H:%M:%S') + 'Z'

    return render_template(
        'game.html',
        game=game,
        board_state=board_state,
        legal_moves=legal_moves,
        is_participant=(player_color is not None),
        player_color=player_color,
        is_player_turn=is_player_turn,
        moves=moves,
        deadline_iso=deadline_iso,
    )


@game_bp.route('/game/<int:game_id>/move', methods=['POST'])
@login_required
def make_move(game_id):
    game = Game.query.get_or_404(game_id)
    player_color = _player_color(game)
    if not player_color:
        return jsonify({'error': 'Not a participant'}), 403
    if game.current_turn != player_color:
        return jsonify({'error': 'Not your turn'}), 400
    if game.status not in ('pending', 'active'):
        return jsonify({'error': 'Game is not active'}), 400

    data = request.get_json()
    uci_move = data.get('uci') if data else None
    if not uci_move:
        return jsonify({'error': 'No move provided'}), 400

    try:
        result = ChessEngine.make_move(game.fen_current, uci_move)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    if game.status == 'pending':
        game.status = 'active'
        game.started_at = datetime.now(timezone.utc)

    move = Move(
        game_id=game.id,
        move_number=result['move_number'],
        color=player_color,
        move_san=result['san'],
        move_uci=uci_move,
        fen_after=result['fen'],
    )
    db.session.add(move)

    game.fen_current = result['fen']
    game.current_turn = result['turn']
    game.move_count += 1

    is_over, result_type = ChessEngine.is_game_over(result['fen'])
    if is_over:
        _finish_game(game, result_type, player_color)

    db.session.commit()

    return jsonify({
        'success': True,
        'fen': result['fen'],
        'san': result['san'],
        'turn': result['turn'],
        'game_over': is_over,
        'result': game.result if is_over else None,
        'result_type': result_type,
        'move_number': result['move_number'],
    })


@game_bp.route('/game/<int:game_id>/resign', methods=['POST'])
@login_required
def resign(game_id):
    game = Game.query.get_or_404(game_id)
    player_color = _player_color(game)
    if not player_color:
        return jsonify({'error': 'Not a participant'}), 403
    if game.status not in ('pending', 'active'):
        return jsonify({'error': 'Game is not active'}), 400

    game.result = '0-1' if player_color == 'white' else '1-0'
    _finish_game(game, 'resignation', player_color)
    db.session.commit()

    return jsonify({
        'success': True,
        'result': game.result,
        'result_type': 'resignation',
    })


@game_bp.route('/game/<int:game_id>/state')
@login_required
def game_state(game_id):
    game = Game.query.get_or_404(game_id)
    player_color = _player_color(game)

    is_your_turn = False
    legal_moves = []
    if player_color and game.current_turn == player_color \
       and game.status in ('pending', 'active'):
        is_your_turn = True
        legal_moves = ChessEngine.get_legal_moves(game.fen_current)

    last_move = Move.query.filter_by(
        game_id=game.id
    ).order_by(Move.id.desc()).first()

    return jsonify({
        'fen': game.fen_current,
        'turn': game.current_turn,
        'is_your_turn': is_your_turn,
        'legal_moves': legal_moves,
        'status': game.status,
        'result': game.result,
        'result_type': game.result_type,
        'move_count': game.move_count,
        'last_move': {
            'san': last_move.move_san,
            'uci': last_move.move_uci,
            'color': last_move.color,
        } if last_move else None,
    })


def _finish_game(game, result_type, last_mover):
    game.status = 'completed'
    game.completed_at = datetime.now(timezone.utc)
    game.fen_final = game.fen_current
    game.result_type = result_type

    material = ChessEngine.get_material(game.fen_current)
    game.material_white = material['white']
    game.material_black = material['black']

    if result_type == 'checkmate':
        game.result = '1-0' if last_mover == 'white' else '0-1'
    elif result_type in ('stalemate', 'draw'):
        game.result = '1/2-1/2'

    db.session.flush()
    all_moves = Move.query.filter_by(game_id=game.id).order_by(Move.id).all()
    game.pgn = ChessEngine.build_pgn(all_moves, game)

    try:
        from app.services.material import record_material
        white_diff = material['white'] - material['black']
        record_material(game.white_id, white_diff)
        record_material(game.black_id, -white_diff)
    except (ImportError, Exception):
        pass

    from app.services.rating import apply_result
    apply_result(game)
