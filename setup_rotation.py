"""
One-time script: set power rotation so andrewmuckerofstalls is the current
week's decree holder and defenderofknight is next.

Run on PythonAnywhere:
    python setup_rotation.py
"""
from app import create_app
from app.models import User, PowerRotationOrder, WeeklySchedule, db
from app.services.matchmaking import get_current_week, get_current_season
from app.services.power import set_rotation_order

app = create_app()

with app.app_context():
    week = get_current_week()
    year, month = get_current_season()
    season_key = year * 100 + month

    andrew = User.query.filter_by(username='andrewmuckerofstalls').first()
    defender = User.query.filter_by(username='defenderofknight').first()
    bunda = User.query.filter_by(username='BundaBomber69').first()

    if not andrew or not defender:
        print('Required users not found. Aborting.')
        exit(1)

    players = [p for p in [andrew, defender, bunda] if p]
    n = len(players)

    # We need:  week % n -> index of andrew,  (week+1) % n -> index of defender
    # With 3 players and week=11: 11%3=2, 12%3=0
    # So: pos 2 = andrew, pos 0 = defender, pos 1 = bunda
    order_ids = [None] * n
    order_ids[week % n] = andrew.id
    order_ids[(week + 1) % n] = defender.id
    remaining = [p.id for p in players if p.id not in order_ids]
    for i in range(n):
        if order_ids[i] is None and remaining:
            order_ids[i] = remaining.pop(0)

    set_rotation_order(order_ids)
    print(f'Rotation set: {order_ids}')

    # Create/update schedule for current week
    schedule = WeeklySchedule.query.filter_by(
        week_number=week, season=season_key
    ).first()
    if not schedule:
        schedule = WeeklySchedule(week_number=week, season=season_key)
        db.session.add(schedule)

    schedule.power_position_holder_id = andrew.id
    schedule.rule_declaration = (
        'Knights have lame knees — now the horses cannot move. '
        'They remain on the board but are frozen in place. '
        'This rule applies to all player-vs-player matches this week.'
    )
    db.session.commit()

    print(f'Week {week} decree holder: {andrew.username}')
    print(f'Next holder (week {week+1}): {defender.username}')
    print('Done.')
