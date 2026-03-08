import math

from app.models import db, User

TIERS = [
    (0, 399, 'Tier I', 'Initiate'),
    (400, 699, 'Tier II', 'Apprentice'),
    (700, 999, 'Tier III', 'Journeyman'),
    (1000, 1399, 'Tier IV', 'Adept'),
    (1400, 1799, 'Tier V', 'Scholar'),
    (1800, 2199, 'Tier VI', 'Master'),
    (2200, 2599, 'Tier VII', 'Grandmaster'),
    (2600, 2999, 'Tier VIII', 'Archmage'),
    (3000, 3499, 'Tier IX', 'Sovereign'),
    (3500, 4000, 'Tier X', 'Lord of Schools'),
]

K_FACTOR = 32


def get_tier(rating):
    for low, high, tier_label, name in TIERS:
        if low <= rating <= high:
            return {'tier': tier_label, 'name': name}
    if rating > 4000:
        return {'tier': 'Tier X', 'name': 'Lord of Schools'}
    return {'tier': 'Tier I', 'name': 'Initiate'}


def expected_score(player_rating, opponent_rating):
    return 1.0 / (1.0 + math.pow(10, (opponent_rating - player_rating) / 400.0))


def material_modifier(winner_material, loser_material, base_change):
    """Modifier based on final material imbalance. Capped at 20% of base."""
    delta = winner_material - loser_material
    max_mod = abs(base_change) * 0.2

    if delta < 0:
        return min(abs(delta) * 0.5, max_mod)
    return 0.0


def calculate_rating_change(winner_rating, loser_rating,
                            winner_material=None, loser_material=None,
                            result_type='checkmate', is_draw=False):
    if is_draw:
        e = expected_score(winner_rating, loser_rating)
        change = K_FACTOR * (0.5 - e)
        return round(change, 1), round(-change, 1)

    e_winner = expected_score(winner_rating, loser_rating)
    e_loser = expected_score(loser_rating, winner_rating)

    base_winner = K_FACTOR * (1 - e_winner)
    base_loser = K_FACTOR * (0 - e_loser)

    mat_mod = 0.0
    if result_type not in ('timeout', 'forfeit') and \
       winner_material is not None and loser_material is not None:
        mat_mod = material_modifier(winner_material, loser_material, base_winner)

    return round(base_winner + mat_mod, 1), round(base_loser - mat_mod, 1)


def apply_result(game):
    """Apply rating changes and update player stats for a completed game."""
    white = db.session.get(User, game.white_id)
    black = db.session.get(User, game.black_id)

    if game.result == '1/2-1/2':
        change_w, change_b = calculate_rating_change(
            white.rating, black.rating, is_draw=True
        )
        white.draws += 1
        black.draws += 1

    elif game.result == '1-0':
        change_w, change_b = calculate_rating_change(
            white.rating, black.rating,
            winner_material=game.material_white,
            loser_material=game.material_black,
            result_type=game.result_type,
        )
        white.wins += 1
        black.losses += 1
        if game.result_type == 'timeout':
            black.forfeits += 1

    elif game.result == '0-1':
        change_b, change_w = calculate_rating_change(
            black.rating, white.rating,
            winner_material=game.material_black,
            loser_material=game.material_white,
            result_type=game.result_type,
        )
        black.wins += 1
        white.losses += 1
        if game.result_type == 'timeout':
            white.forfeits += 1
    else:
        return

    game.rating_change_white = change_w
    game.rating_change_black = change_b
    white.rating = max(100, round(white.rating + change_w))
    black.rating = max(100, round(black.rating + change_b))
