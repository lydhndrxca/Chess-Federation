from datetime import datetime, timezone

from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user, login_required

from app.models import Commendation, Game, Move, PlayerCollectible, User, db
from app.services.chess_engine import ChessEngine
from app.services.enoch import get_move_commentary, comment_game_start, get_title
from app.services.sequences import get_sequence_info, name_sequence
from app.services.collectibles_catalog import CATALOG_BY_ID

game_bp = Blueprint('game', __name__)


def _player_color(game):
    if current_user.id == game.white_id:
        return 'white'
    if current_user.id == game.black_id:
        return 'black'
    return None


def _my_rating_change(game, user_id):
    if user_id == game.white_id and game.rating_change_white is not None:
        return round(game.rating_change_white, 1)
    if user_id == game.black_id and game.rating_change_black is not None:
        return round(game.rating_change_black, 1)
    return None


def _get_earned_items(game_id, user_id):
    rows = PlayerCollectible.query.filter_by(game_id=game_id, user_id=user_id).all()
    items = []
    for r in rows:
        cat = CATALOG_BY_ID.get(r.item_id)
        if cat:
            items.append({
                'id': cat['id'],
                'name': cat['name'],
                'collection': cat['collection'],
                'desc': cat['desc'],
                'enoch': cat['enoch'],
            })
    return items


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

    last_move_uci = moves[-1].move_uci if moves else None

    opponent = game.black if player_color == 'white' else game.white
    me = game.white if player_color == 'white' else game.black

    seq_info = get_sequence_info(game.id)

    has_commended = False
    if player_color and game.status in ('completed', 'forfeited'):
        has_commended = Commendation.query.filter_by(
            game_id=game.id, author_id=current_user.id
        ).first() is not None

    opening_name = seq_info['match']['name'] if seq_info.get('match') else None
    last_san = moves[-1].move_san if moves else None
    is_over = game.status in ('completed', 'forfeited')
    enoch_line = None
    if last_san:
        enoch_line = get_move_commentary(
            last_san, len(moves), is_over, game.result_type,
            opening_name=opening_name)
    elif game.move_count == 0:
        enoch_line = comment_game_start()

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
        last_move_uci=last_move_uci,
        opponent=opponent,
        me=me,
        seq_match=seq_info.get('match'),
        has_commended=has_commended,
        enoch_line=enoch_line,
        enoch_title=get_title(),
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

    seq = get_sequence_info(game.id)
    opening_name = seq['match']['name'] if seq.get('match') else None

    enoch_line = get_move_commentary(
        result['san'], game.move_count, is_over, result_type,
        opening_name=opening_name)

    resp = {
        'success': True,
        'fen': result['fen'],
        'san': result['san'],
        'turn': result['turn'],
        'game_over': is_over,
        'result': game.result if is_over else None,
        'result_type': result_type,
        'move_number': result['move_number'],
    }
    if enoch_line:
        resp['enoch'] = enoch_line
    if is_over:
        resp['rating_change'] = _my_rating_change(game, current_user.id)
        resp['show_commend'] = True
        resp['earned_items'] = _get_earned_items(game.id, current_user.id)

    if seq.get('match'):
        resp['sequence'] = seq['match']
    if seq.get('can_name') and current_user.can_name_openings:
        resp['can_name_sequence'] = seq['can_name']

    return jsonify(resp)


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
        'rating_change': _my_rating_change(game, current_user.id),
        'show_commend': True,
        'earned_items': _get_earned_items(game.id, current_user.id),
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

    seq = get_sequence_info(game.id)
    opening_name = seq['match']['name'] if seq.get('match') else None
    is_over = game.status in ('completed', 'forfeited')

    enoch_line = None
    if last_move:
        enoch_line = get_move_commentary(
            last_move.move_san, game.move_count, is_over, game.result_type,
            opening_name=opening_name)

    resp = {
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
    }
    if enoch_line:
        resp['enoch'] = enoch_line
    if is_over and player_color:
        resp['rating_change'] = _my_rating_change(game, current_user.id)
        resp['show_commend'] = True
        resp['earned_items'] = _get_earned_items(game.id, current_user.id)
    if seq.get('match'):
        resp['sequence'] = seq['match']

    return jsonify(resp)


@game_bp.route('/game/<int:game_id>/commend', methods=['POST'])
@login_required
def commend_player(game_id):
    game = Game.query.get_or_404(game_id)
    player_color = _player_color(game)
    if not player_color:
        return jsonify({'error': 'Not a participant'}), 403
    if game.status not in ('completed', 'forfeited'):
        return jsonify({'error': 'Game is not finished'}), 400

    existing = Commendation.query.filter_by(
        game_id=game.id, author_id=current_user.id
    ).first()
    if existing:
        return jsonify({'error': 'You have already submitted for this game'}), 409

    data = request.get_json()
    kind = (data.get('kind') or '').strip() if data else ''
    text = (data.get('text') or '').strip() if data else ''

    if kind not in ('commend', 'condemn'):
        return jsonify({'error': 'Invalid type'}), 400
    if not text or len(text) > 300:
        return jsonify({'error': 'Text must be 1-300 characters'}), 400

    opponent_id = game.black_id if player_color == 'white' else game.white_id

    comm = Commendation(
        game_id=game.id,
        author_id=current_user.id,
        subject_id=opponent_id,
        kind=kind,
        text=text,
    )
    db.session.add(comm)

    commend_earned = []
    try:
        from app.services.collectibles_engagement import evaluate_commendation_triggers
        commend_earned = evaluate_commendation_triggers(current_user.id) or []
    except Exception:
        pass

    db.session.commit()

    resp = {'success': True}
    if commend_earned:
        resp['earned_items'] = [{
            'id': it['id'], 'name': it['name'],
            'collection': it['collection'], 'desc': it['desc'],
            'enoch': it['enoch'],
        } for it in commend_earned]

    return jsonify(resp)


@game_bp.route('/game/<int:game_id>/name-sequence', methods=['POST'])
@login_required
def name_game_sequence(game_id):
    game = Game.query.get_or_404(game_id)
    player_color = _player_color(game)
    if not player_color:
        return jsonify({'error': 'Not a participant'}), 403
    if not current_user.can_name_openings:
        return jsonify({'error': 'Naming is disabled in your settings'}), 403

    data = request.get_json()
    seq_name = (data.get('name') or '').strip() if data else ''
    moves_key = (data.get('moves_key') or '').strip() if data else ''
    half_moves = data.get('half_moves', 0) if data else 0
    category = (data.get('category') or '').strip() if data else ''

    if not seq_name or len(seq_name) > 100:
        return jsonify({'error': 'Name must be 1-100 characters'}), 400
    if not moves_key or not half_moves or category not in ('Opening', 'Variation'):
        return jsonify({'error': 'Invalid sequence data'}), 400

    seq = name_sequence(current_user.id, seq_name, moves_key, half_moves, category)
    if not seq:
        return jsonify({'error': 'This sequence has already been named'}), 409

    try:
        from app.services.collectibles_engagement import evaluate_naming_triggers
        evaluate_naming_triggers(current_user.id)
        db.session.flush()
    except Exception:
        pass

    return jsonify({
        'success': True,
        'sequence': {
            'name': seq.name,
            'category': seq.category,
            'creator': current_user.username,
        },
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

    try:
        from app.services.collectibles import evaluate_collectibles
        from app.models import PlayerCollectible
        for color in ('white', 'black'):
            uid = game.white_id if color == 'white' else game.black_id
            earned = evaluate_collectibles(game, all_moves, color)
            for item in earned:
                pc = PlayerCollectible(
                    user_id=uid, item_id=item['id'], game_id=game.id)
                db.session.add(pc)
    except Exception:
        pass

    try:
        from app.services.collectibles_engagement import evaluate_milestone_triggers
        evaluate_milestone_triggers(game.white_id, game.id)
        evaluate_milestone_triggers(game.black_id, game.id)
    except Exception:
        pass
