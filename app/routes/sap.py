"""Routes for Spectacle Lake — Enoch's Maple Forest mode."""

import json
import random
from datetime import datetime, timezone

from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user

from app.models import db, User, SapGame
from app.services.sap_dialogue import (
    ENTRY_COST, POINTS_PER_TREE, MAX_RATING_POINTS, ABILITIES,
)

sap_bp = Blueprint('sap', __name__)


@sap_bp.route('/sap/start', methods=['POST'])
@login_required
def start_sap():
    active = SapGame.query.filter_by(
        user_id=current_user.id, status='active').first()
    if active:
        return jsonify({'error': 'You already have an active run', 'game_id': active.id}), 400

    if current_user.rating < ENTRY_COST:
        return jsonify({'error': f'Need {ENTRY_COST} rating points to enter'}), 400

    current_user.rating -= ENTRY_COST
    seed = random.randint(100000, 999999)
    game = SapGame(
        user_id=current_user.id,
        map_seed=seed,
        status='active',
    )
    db.session.add(game)
    db.session.commit()

    return jsonify({'game_id': game.id, 'seed': seed})


@sap_bp.route('/sap/<int:game_id>')
@login_required
def view_sap(game_id):
    game = SapGame.query.get_or_404(game_id)
    if game.user_id != current_user.id:
        return "Not your game", 403

    return render_template(
        'sap.html',
        game=game,
        abilities_catalog=json.dumps(ABILITIES),
    )


@sap_bp.route('/sap/<int:game_id>/harvest', methods=['POST'])
@login_required
def complete_harvest(game_id):
    game = SapGame.query.get_or_404(game_id)
    if game.user_id != current_user.id or game.status != 'active':
        return jsonify({'error': 'Invalid game'}), 400

    game.trees_harvested += 1
    earned = POINTS_PER_TREE
    total_rating_earned = game.trees_harvested * POINTS_PER_TREE

    if total_rating_earned <= MAX_RATING_POINTS:
        current_user.rating += earned
        game.rating_earned = (game.rating_earned or 0) + earned
    else:
        gold = earned * 2
        game.gold_earned = (game.gold_earned or 0) + gold
        current_user.roman_gold = (current_user.roman_gold or 0) + gold

    game.difficulty += 1
    db.session.commit()

    return jsonify({
        'trees': game.trees_harvested,
        'rating_earned': game.rating_earned or 0,
        'gold_earned': game.gold_earned or 0,
        'difficulty': game.difficulty,
        'total_rating': current_user.rating,
        'total_gold': current_user.roman_gold or 0,
    })


@sap_bp.route('/sap/<int:game_id>/cashout', methods=['POST'])
@login_required
def cashout_sap(game_id):
    game = SapGame.query.get_or_404(game_id)
    if game.user_id != current_user.id or game.status != 'active':
        return jsonify({'error': 'Invalid game'}), 400

    game.status = 'cashed_out'
    game.completed_at = datetime.now(timezone.utc)
    db.session.commit()

    return jsonify({
        'trees': game.trees_harvested,
        'rating_earned': game.rating_earned or 0,
        'gold_earned': game.gold_earned or 0,
        'total_rating': current_user.rating,
    })


@sap_bp.route('/sap/<int:game_id>/gameover', methods=['POST'])
@login_required
def gameover_sap(game_id):
    game = SapGame.query.get_or_404(game_id)
    if game.user_id != current_user.id or game.status != 'active':
        return jsonify({'error': 'Invalid game'}), 400

    game.status = 'defeated'
    game.completed_at = datetime.now(timezone.utc)
    db.session.commit()

    return jsonify({
        'trees': game.trees_harvested,
        'rating_earned': game.rating_earned or 0,
        'gold_earned': game.gold_earned or 0,
        'total_rating': current_user.rating,
    })


@sap_bp.route('/sap/<int:game_id>/buy', methods=['POST'])
@login_required
def buy_ability(game_id):
    game = SapGame.query.get_or_404(game_id)
    if game.user_id != current_user.id or game.status != 'active':
        return jsonify({'error': 'Invalid game'}), 400

    data = request.get_json(silent=True) or {}
    ability_id = data.get('ability')
    if ability_id not in ABILITIES:
        return jsonify({'error': 'Unknown ability'}), 400

    cost = ABILITIES[ability_id]['cost']
    gold = current_user.roman_gold or 0
    if gold < cost:
        return jsonify({'error': 'Not enough Roman gold'}), 400

    current_user.roman_gold = gold - cost
    abilities = json.loads(game.abilities or '[]')
    abilities.append(ability_id)
    game.abilities = json.dumps(abilities)
    db.session.commit()

    return jsonify({
        'abilities': abilities,
        'gold': current_user.roman_gold,
    })
