"""
extensions.py
=============
Shared Flask extension instances (SQLAlchemy db + AppLogger).

All Blueprints import from here to avoid circular imports.

Initialization order (enforced in app.py):
    1.  db = SQLAlchemy()           -- created here at module level
    2.  app.py configures Flask app
    3.  db.init_app(app)            -- called in app.py
    4.  set_db(db)                  -- unpacks model classes
    5.  init_logger(app, db)        -- binds logger_handler here
    6.  Blueprints are registered
"""

from flask_sqlalchemy import SQLAlchemy
from logger_handler import AppLogger

# ---------------------------------------------------------------------------
# Database — single shared instance
# ---------------------------------------------------------------------------
db = SQLAlchemy()

# ---------------------------------------------------------------------------
# Application-level logger — initialized via init_logger() below
# ---------------------------------------------------------------------------
logger_handler: "AppLogger | None" = None


def init_logger(app, database) -> AppLogger:
    """
    Instantiate AppLogger and bind it to the module-level ``logger_handler``
    variable so every Blueprint that does ``from extensions import logger_handler``
    receives the same fully-initialized instance.
    """
    global logger_handler
    logger_handler = AppLogger(app, database)
    return logger_handler
