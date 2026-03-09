"""Routes for casual game challenges between players."""

from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from sqlalchemy import or_, and_

from app.models import Challenge, Game, User, db
from app.services.matchmaking import _count_white_games, get_current_week, get_current_season

challenge_bp = Blueprint('challenge', __name__)


def _active_casual_between(user_a_id, user_b_id):
    """Return an active casual game between two players, if any."""
    return Game.query.filter(
        Game.game_type == 'casual',
        Game.is_practice == False,
        Game.status.in_(['pending', 'active']),
        or_(
            and_(Game.white_id == user_a_id, Game.black_id == user_b_id),
            and_(Game.white_id == user_b_id, Game.black_id == user_a_id),
        ),
    ).first()


def _assign_casual_colors(player_a_id, player_b_id):
    """Pick white/black so the player who has been white less often gets white."""
    a_whites = _count_white_games(player_a_id)
    b_whites = _count_white_games(player_b_id)
    if a_whites <= b_whites:
        return player_a_id, player_b_id
    return player_b_id, player_a_id


@challenge_bp.route('/challenge/send', methods=['POST'])
@login_required
def send_challenge():
    data = request.get_json() or {}
    target_id = data.get('user_id')
    if not target_id:
        return jsonify({'error': 'Missing user_id'}), 400

    target = db.session.get(User, target_id)
    if not target or target.is_bot or target.id == current_user.id:
        return jsonify({'error': 'Invalid target'}), 400

    if _active_casual_between(current_user.id, target.id):
        return jsonify({'error': 'You already have an active casual game with this player'}), 400

    existing = Challenge.query.filter_by(
        challenger_id=current_user.id,
        challenged_id=target.id,
        status='pending',
    ).first()
    if existing:
        return jsonify({'error': 'Challenge already pending'}), 400

    reverse = Challenge.query.filter_by(
        challenger_id=target.id,
        challenged_id=current_user.id,
        status='pending',
    ).first()
    if reverse:
        return _accept_challenge(reverse)

    ch = Challenge(
        challenger_id=current_user.id,
        challenged_id=target.id,
    )
    db.session.add(ch)
    db.session.commit()

    return jsonify({'success': True, 'challenge_id': ch.id,
                    'message': f'Challenge sent to {target.username}'})


@challenge_bp.route('/challenge/<int:challenge_id>/accept', methods=['POST'])
@login_required
def accept_challenge(challenge_id):
    ch = Challenge.query.get_or_404(challenge_id)
    if ch.challenged_id != current_user.id or ch.status != 'pending':
        return jsonify({'error': 'Cannot accept this challenge'}), 400
    return _accept_challenge(ch)


@challenge_bp.route('/challenge/<int:challenge_id>/decline', methods=['POST'])
@login_required
def decline_challenge(challenge_id):
    ch = Challenge.query.get_or_404(challenge_id)
    if ch.challenged_id != current_user.id or ch.status != 'pending':
        return jsonify({'error': 'Cannot decline this challenge'}), 400
    ch.status = 'declined'
    db.session.commit()
    return jsonify({'success': True})


def _accept_challenge(ch):
    """Accept a challenge and create the casual game."""
    if _active_casual_between(ch.challenger_id, ch.challenged_id):
        ch.status = 'declined'
        db.session.commit()
        return jsonify({'error': 'Already have an active casual game'}), 400

    white_id, black_id = _assign_casual_colors(ch.challenger_id, ch.challenged_id)

    week = get_current_week()
    year, month = get_current_season()
    season_key = year * 100 + month

    game = Game(
        white_id=white_id,
        black_id=black_id,
        week_number=week,
        season=season_key,
        game_type='casual',
        is_practice=False,
    )
    db.session.add(game)
    db.session.flush()

    ch.status = 'accepted'
    ch.game_id = game.id
    db.session.commit()

    return jsonify({
        'success': True,
        'game_id': game.id,
        'url': f'/game/{game.id}',
    })


@challenge_bp.route('/challenge/pending')
@login_required
def pending_challenges():
    """Return pending challenges for the current user."""
    incoming = Challenge.query.filter_by(
        challenged_id=current_user.id, status='pending'
    ).all()
    outgoing = Challenge.query.filter_by(
        challenger_id=current_user.id, status='pending'
    ).all()

    return jsonify({
        'incoming': [{
            'id': c.id,
            'challenger': c.challenger.username,
            'challenger_id': c.challenger_id,
            'challenger_rating': c.challenger.rating,
        } for c in incoming],
        'outgoing': [{
            'id': c.id,
            'challenged': c.challenged.username,
            'challenged_id': c.challenged_id,
        } for c in outgoing],
    })
