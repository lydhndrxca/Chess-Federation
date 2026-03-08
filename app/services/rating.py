import math

from app.models import db, User

TIERS = [
    (1,  200, 'Ordained Laborer of the Stables and Bishop\'s Vestments'),
    (2,  522, 'Most Subordinate to the Relative Command of the Bishop with Holiness'),
    (3,  844, 'Most Delicate Acolyte to the Bishop with Holiness'),
    (4, 1167, 'Living Bishop with Holiness'),
    (5, 1489, 'Esteemed Supreme Grandmaster – Level 1'),
    (6, 1811, 'Esteemed Supreme Grandmaster – Level 2'),
    (7, 2133, 'Esteemed Supreme Grandmaster – Level 3'),
    (8, 2456, 'Most Esteemed Subordinate to the Keeper of the Light of the Lord of Schools'),
    (9, 2778, 'Keeper of the Light of the Lord of Schools'),
    (10, 3100, 'Lord of Schools'),
]

RATING_FLOOR = 200

RESULT_BASE = {
    'win': 40,
    'draw': 10,
    'loss': -32,
    'forfeit_win': 28,
    'forfeit_loss': -28,
}

OPPONENT_MOD_RANGE = 12


def get_tier(rating):
    level = 1
    name = TIERS[0][2]
    for lvl, threshold, title in TIERS:
        if rating >= threshold:
            level = lvl
            name = title
    return {'level': level, 'name': name, 'tier': f'Level {level}'}


def expected_score(player_rating, opponent_rating):
    return 1.0 / (1.0 + math.pow(10, (opponent_rating - player_rating) / 400.0))


def opponent_modifier(player_rating, opponent_rating, won):
    e = expected_score(player_rating, opponent_rating)
    if won:
        raw = (1 - e) * OPPONENT_MOD_RANGE * 2 - OPPONENT_MOD_RANGE
    else:
        raw = (0 - e) * OPPONENT_MOD_RANGE * 2 + OPPONENT_MOD_RANGE
    return max(-OPPONENT_MOD_RANGE, min(OPPONENT_MOD_RANGE, round(raw, 1)))


def get_material_modifier(user_id):
    """Return the seasonal material band modifier for a player.
    Placeholder that returns 0 until Phase 3 is wired up."""
    try:
        from app.services.material import get_season_modifier
        return get_season_modifier(user_id)
    except (ImportError, Exception):
        return 0


def calculate_rating_change(winner_rating, loser_rating,
                            winner_id=None, loser_id=None,
                            result_type='checkmate', is_draw=False,
                            is_forfeit=False):
    if is_draw:
        base = RESULT_BASE['draw']
        opp_mod_w = opponent_modifier(winner_rating, loser_rating, won=True)
        opp_mod_b = opponent_modifier(loser_rating, winner_rating, won=True)
        mat_w = get_material_modifier(winner_id) if winner_id else 0
        mat_b = get_material_modifier(loser_id) if loser_id else 0
        change_w = round(base + opp_mod_w * 0.3 + mat_w, 1)
        change_b = round(base + opp_mod_b * 0.3 + mat_b, 1)
        return change_w, change_b

    if is_forfeit:
        base_w = RESULT_BASE['forfeit_win']
        base_l = RESULT_BASE['forfeit_loss']
        opp_w = opponent_modifier(winner_rating, loser_rating, won=True)
        opp_l = opponent_modifier(loser_rating, winner_rating, won=False)
        return round(base_w + opp_w * 0.5, 1), round(base_l + opp_l * 0.5, 1)

    base_w = RESULT_BASE['win']
    base_l = RESULT_BASE['loss']
    opp_w = opponent_modifier(winner_rating, loser_rating, won=True)
    opp_l = opponent_modifier(loser_rating, winner_rating, won=False)
    mat_w = get_material_modifier(winner_id) if winner_id else 0
    mat_l = get_material_modifier(loser_id) if loser_id else 0

    return round(base_w + opp_w + mat_w, 1), round(base_l + opp_l + mat_l, 1)


def apply_result(game):
    """Apply rating changes and update player stats for a completed game."""
    white = db.session.get(User, game.white_id)
    black = db.session.get(User, game.black_id)

    old_tier_white = get_tier(white.rating)
    old_tier_black = get_tier(black.rating)

    is_forfeit = game.result_type in ('timeout', 'forfeit')

    if game.result == '1/2-1/2':
        change_w, change_b = calculate_rating_change(
            white.rating, black.rating,
            winner_id=white.id, loser_id=black.id,
            is_draw=True,
        )
        white.draws += 1
        black.draws += 1

    elif game.result == '1-0':
        change_w, change_b = calculate_rating_change(
            white.rating, black.rating,
            winner_id=white.id, loser_id=black.id,
            result_type=game.result_type,
            is_forfeit=is_forfeit,
        )
        white.wins += 1
        black.losses += 1
        if is_forfeit:
            black.forfeits += 1

    elif game.result == '0-1':
        change_b, change_w = calculate_rating_change(
            black.rating, white.rating,
            winner_id=black.id, loser_id=white.id,
            result_type=game.result_type,
            is_forfeit=is_forfeit,
        )
        black.wins += 1
        white.losses += 1
        if is_forfeit:
            white.forfeits += 1
    else:
        return

    game.rating_change_white = change_w
    game.rating_change_black = change_b
    white.rating = max(RATING_FLOOR, round(white.rating + change_w))
    black.rating = max(RATING_FLOOR, round(black.rating + change_b))

    new_tier_white = get_tier(white.rating)
    new_tier_black = get_tier(black.rating)

    try:
        from app.services.enoch import announce_match_result, announce_promotion
        announce_match_result(game, white, black, change_w, change_b)
        if new_tier_white['level'] > old_tier_white['level']:
            announce_promotion(white, new_tier_white)
        if new_tier_black['level'] > old_tier_black['level']:
            announce_promotion(black, new_tier_black)
    except (ImportError, Exception):
        pass
