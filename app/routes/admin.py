from flask import Blueprint, flash, redirect, url_for
from flask_login import login_required

from app.services.matchmaking import check_forfeits, generate_weekly_pairings

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/generate-week', methods=['POST'])
@login_required
def generate_week():
    result = generate_weekly_pairings()
    if result['games_created'] > 0:
        flash(
            f'Generated {result["games_created"]} match(es) for week {result["week"]}.',
            'success',
        )
    else:
        flash(result.get('message', 'No matches generated.'), 'info')
    return redirect(url_for('main.dashboard'))


@admin_bp.route('/check-forfeits', methods=['POST'])
@login_required
def run_forfeit_check():
    result = check_forfeits()
    flash(f'Forfeit check complete. {result["forfeited"]} game(s) forfeited.', 'info')
    return redirect(url_for('main.dashboard'))
