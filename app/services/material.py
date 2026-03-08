"""Seasonal Material Modifier system.

Tracks per-game material differentials monthly, computes a banded modifier
that slightly adjusts rating gains/losses."""

from datetime import datetime
from zoneinfo import ZoneInfo

from app.models import SeasonMaterialStat, db

FEDERATION_TZ = ZoneInfo('America/Chicago')

MATERIAL_BANDS = [
    (-999, -6, -3),   # far below average
    (-6,   -2, -1),   # below average
    (-2,    2,  0),   # neutral
    (2,     6,  2),   # above average
    (6,    12,  4),   # strongly above
    (12,  999,  5),   # exceptional
]


def _current_month():
    now = datetime.now(FEDERATION_TZ)
    return now.year, now.month


def record_material(user_id, material_diff):
    """Record a material differential for the current month."""
    year, month = _current_month()
    stat = SeasonMaterialStat.query.filter_by(
        user_id=user_id, season_year=year, season_month=month
    ).first()
    if not stat:
        stat = SeasonMaterialStat(
            user_id=user_id, season_year=year, season_month=month
        )
        db.session.add(stat)

    stat.total_diff += material_diff
    stat.games_count += 1
    stat.avg_diff = stat.total_diff / stat.games_count


def get_lifetime_avg(user_id):
    """Compute lifetime average material differential across all months."""
    stats = SeasonMaterialStat.query.filter_by(user_id=user_id).all()
    if not stats:
        return 0.0
    total_diff = sum(s.total_diff for s in stats)
    total_games = sum(s.games_count for s in stats)
    if total_games == 0:
        return 0.0
    return total_diff / total_games


def get_season_modifier(user_id):
    """Return the banded material modifier for the current month."""
    year, month = _current_month()
    stat = SeasonMaterialStat.query.filter_by(
        user_id=user_id, season_year=year, season_month=month
    ).first()

    if not stat or stat.games_count == 0:
        return 0

    lifetime_avg = get_lifetime_avg(user_id)
    delta = stat.avg_diff - lifetime_avg

    for low, high, modifier in MATERIAL_BANDS:
        if low <= delta < high:
            return modifier

    return 0
