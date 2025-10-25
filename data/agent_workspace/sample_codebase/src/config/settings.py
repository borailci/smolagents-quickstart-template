"""
Environment-based configuration settings
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """
    Application settings loaded from environment variables.
    """

    # Flask settings
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')

    # Database
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///taskflow.db')

    # API
    API_TITLE = 'TaskFlow API'
    API_VERSION = '0.1.0'

    # Server
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', 5000))

    @classmethod
    def from_env(cls):
        """Create settings instance from environment"""
        return cls()
