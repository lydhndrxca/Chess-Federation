import os
from datetime import timedelta

basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'chess-federation-dev-key')
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'sqlite:///' + os.path.join(basedir, 'data', 'chess_federation.db')
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    REMEMBER_COOKIE_DURATION = timedelta(days=90)
    REMEMBER_COOKIE_SECURE = False
    REMEMBER_COOKIE_HTTPONLY = True
    UPLOAD_FOLDER = os.path.join(basedir, 'app', 'static', 'uploads', 'avatars')
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024  # 2 MB
    FEDERATION_TIMEZONE = 'America/Chicago'
