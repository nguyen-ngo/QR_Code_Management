"""
config.py
=========
Centralised application configuration.

All environment variable reads happen here — once, at startup.
Blueprints and helpers that need a config value use:

    from flask import current_app
    value = current_app.config['KEY']

Or for values needed at module import time (before app context):

    from config import Config
    value = Config.COMPANY_NAME
"""

import os
from datetime import timedelta


class Config:
    # ------------------------------------------------------------------ #
    # Core Flask
    # ------------------------------------------------------------------ #
    SECRET_KEY = os.environ.get('SECRET_KEY', 'change-me-in-production')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', '')
    SQLALCHEMY_TRACK_MODIFICATIONS = (
        os.environ.get('SQLALCHEMY_TRACK_MODIFICATIONS', 'False').lower() == 'true'
    )
    TEMPLATES_AUTO_RELOAD = (
        os.environ.get('TEMPLATES_AUTO_RELOAD', 'True').lower() == 'true'
    )
    DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'

    # ------------------------------------------------------------------ #
    # Session / cookies
    # ------------------------------------------------------------------ #
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)
    SESSION_COOKIE_SECURE = (
        os.environ.get('SESSION_COOKIE_SECURE', 'false').lower() == 'true'
    )
    SESSION_COOKIE_HTTPONLY = (
        os.environ.get('SESSION_COOKIE_HTTPONLY', 'true').lower() == 'true'
    )
    SESSION_COOKIE_SAMESITE = os.environ.get('SESSION_COOKIE_SAMESITE', 'Lax')

    # ------------------------------------------------------------------ #
    # Application identity
    # ------------------------------------------------------------------ #
    COMPANY_NAME    = os.environ.get('COMPANY_NAME',    'QR Code Management System')
    CONTRACT_NAME   = os.environ.get('CONTRACT_NAME',   'Default Contract')

    # ------------------------------------------------------------------ #
    # File uploads
    # ------------------------------------------------------------------ #
    UPLOAD_FOLDER   = os.environ.get('UPLOAD_FOLDER', '/tmp')

    # ------------------------------------------------------------------ #
    # Photo verification
    # ------------------------------------------------------------------ #
    PHOTO_VERIFICATION_ENABLED = (
        os.environ.get('ENABLE_PHOTO_VERIFICATION', 'true').lower() == 'true'
    )
    DISTANCE_THRESHOLD_FOR_VERIFICATION = float(
        os.environ.get('PHOTO_VERIFICATION_DISTANCE_THRESHOLD', '0.3')
    )
    VERIFICATION_PHOTO_MAX_SIZE = int(
        os.environ.get('VERIFICATION_PHOTO_MAX_SIZE', str(5 * 1024 * 1024))
    )

    # ------------------------------------------------------------------ #
    # Check-in interval
    # ------------------------------------------------------------------ #
    TIME_INTERVAL = int(os.environ.get('TIME_INTERVAL', '30'))

    # ------------------------------------------------------------------ #
    # Server
    # ------------------------------------------------------------------ #
    FLASK_HOST  = os.environ.get('FLASK_HOST',  '0.0.0.0')
    FLASK_PORT  = int(os.environ.get('FLASK_PORT', '5000'))
    THREADED    = os.environ.get('THREADED', 'True').lower() == 'true'

    # ------------------------------------------------------------------ #
    # Default admin (used only on first boot)
    # ------------------------------------------------------------------ #
    DEFAULT_ADMIN_PASSWORD = os.environ.get('DEFAULT_ADMIN_PASSWORD', 'admin123')


class DevelopmentConfig(Config):
    DEBUG = True
    SESSION_COOKIE_SECURE = False


class ProductionConfig(Config):
    DEBUG = False
    TEMPLATES_AUTO_RELOAD = False


# Active config selected by environment variable
_config_map = {
    'development': DevelopmentConfig,
    'production':  ProductionConfig,
    'default':     Config,
}

def get_config():
    """Return the active Config class based on FLASK_ENV."""
    env = os.environ.get('FLASK_ENV', 'default').lower()
    return _config_map.get(env, Config)
