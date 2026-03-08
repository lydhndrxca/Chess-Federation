from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

from app.models import WeeklySchedule, db
from app.services.matchmaking import get_current_week, get_current_season

decree_bp = Blueprint('decree', __name__)


@decree_bp.route('/decree')
@login_required
def decree_page():
    week = get_current_week()
    year, month = get_current_season()

    schedule = WeeklySchedule.query.filter_by(
        week_number=week, season=year * 100 + month
    ).first()

    past_decrees = WeeklySchedule.query.filter(
        WeeklySchedule.rule_declaration.isnot(None)
    ).order_by(WeeklySchedule.created_at.desc()).limit(20).all()

    return render_template(
        'decree.html',
        schedule=schedule,
        week=week,
        past_decrees=past_decrees,
    )


@decree_bp.route('/decree', methods=['POST'])
@login_required
def post_decree():
    week = get_current_week()
    year, month = get_current_season()

    schedule = WeeklySchedule.query.filter_by(
        week_number=week, season=year * 100 + month
    ).first()

    if not schedule or schedule.power_position_holder_id != current_user.id:
        flash('Only the current Power Position holder may issue a decree.', 'error')
        return redirect(url_for('decree.decree_page'))

    text = request.form.get('decree', '').strip()
    if not text:
        flash('Decree cannot be empty.', 'error')
        return redirect(url_for('decree.decree_page'))

    schedule.rule_declaration = text
    db.session.commit()

    try:
        from app.services.enoch import announce_decree
        announce_decree(current_user, text)
    except (ImportError, Exception):
        pass

    flash('Decree issued.', 'success')
    return redirect(url_for('decree.decree_page'))
