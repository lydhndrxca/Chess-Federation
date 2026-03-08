from flask import Blueprint, flash, redirect, url_for, request
from flask_login import login_required

from app.models import User, WeeklySchedule, db
from app.services.matchmaking import (
    check_forfeits, generate_weekly_pairings,
    get_current_week, get_current_season,
)
from app.services.power import ensure_rotation_order, get_rotation_order, set_rotation_order

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/generate-week', methods=['POST'])
@login_required
def generate_week():
    ensure_rotation_order()
    result = generate_weekly_pairings()
    if result['games_created'] > 0:
        flash(
            f'Generated {result["games_created"]} match(es) for week {result["week"]}.',
            'success',
        )
    else:
        flash(result.get('message', 'No matches generated.'), 'info')
    return redirect(url_for('main.standings'))


@admin_bp.route('/check-forfeits', methods=['POST'])
@login_required
def run_forfeit_check():
    result = check_forfeits()
    flash(f'Forfeit check complete. {result["forfeited"]} game(s) forfeited.', 'info')
    return redirect(url_for('main.standings'))


@admin_bp.route('/rotation', methods=['POST'])
@login_required
def set_rotation():
    """Set the power rotation order from a comma-separated list of user IDs."""
    ids_raw = request.form.get('order', '')
    try:
        user_ids = [int(x.strip()) for x in ids_raw.split(',') if x.strip()]
    except ValueError:
        flash('Invalid rotation order.', 'error')
        return redirect(url_for('main.standings'))

    valid = User.query.filter(User.id.in_(user_ids)).all()
    valid_ids = {u.id for u in valid}
    user_ids = [uid for uid in user_ids if uid in valid_ids]

    if not user_ids:
        flash('No valid users in rotation order.', 'error')
        return redirect(url_for('main.standings'))

    set_rotation_order(user_ids)
    flash('Power rotation order updated.', 'success')
    return redirect(url_for('main.standings'))


@admin_bp.route('/set-decree', methods=['POST'])
@login_required
def set_decree():
    """Admin override: assign decree holder and decree text for the current week."""
    holder_name = request.form.get('holder', '').strip()
    decree_text = request.form.get('decree', '').strip()

    holder = User.query.filter_by(username=holder_name).first()
    if not holder:
        flash(f'User "{holder_name}" not found.', 'error')
        return redirect(url_for('main.standings'))

    week = get_current_week()
    year, month = get_current_season()
    season_key = year * 100 + month

    schedule = WeeklySchedule.query.filter_by(
        week_number=week, season=season_key
    ).first()
    if not schedule:
        schedule = WeeklySchedule(week_number=week, season=season_key)
        db.session.add(schedule)

    schedule.power_position_holder_id = holder.id
    if decree_text:
        schedule.rule_declaration = decree_text
    db.session.commit()
    flash(f'Decree holder set to {holder.username}.', 'success')
    return redirect(url_for('main.standings'))
