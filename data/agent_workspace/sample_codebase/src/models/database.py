"""
Database module
"""


def init_db(app=None):
    """
    Initialize database.
    In production, would set up SQLAlchemy or similar ORM.
    For demo purposes, using in-memory storage.
    """
    if app:
        app.logger.info('Database initialized (in-memory)')
    return True
