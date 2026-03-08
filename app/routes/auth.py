from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user

from app.models import User, db

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.standings'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            flash('Username and password are required.', 'error')
            return render_template('auth/register.html')

        if len(username) < 2 or len(username) > 30:
            flash('Username must be 2–30 characters.', 'error')
            return render_template('auth/register.html')

        if len(password) < 4:
            flash('Password must be at least 4 characters.', 'error')
            return render_template('auth/register.html')

        if User.query.filter_by(username=username).first():
            flash('Username already taken.', 'error')
            return render_template('auth/register.html')

        bio = request.form.get('bio', '').strip()[:300]

        user = User(username=username, bio=bio)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        login_user(user, remember=True)
        flash('Welcome to the Federation.', 'success')
        return redirect(url_for('main.standings'))

    return render_template('auth/register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.standings'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user, remember=True)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.standings'))

        flash('Invalid username or password.', 'error')

    return render_template('auth/login.html')


@auth_bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.index'))
