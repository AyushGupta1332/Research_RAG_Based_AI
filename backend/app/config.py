"""
Research Agent — Configuration Classes

Environment-specific configuration using class inheritance.
All sensitive values are loaded from .env file.
"""

import os
from datetime import timedelta
from dotenv import load_dotenv

# Load .env file from the backend directory
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))


class BaseConfig:
    """Base configuration shared across all environments."""

    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

    # JWT
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-dev-secret-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        seconds=int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', 3600))
    )
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(
        seconds=int(os.getenv('JWT_REFRESH_TOKEN_EXPIRES', 2592000))
    )
    JWT_TOKEN_LOCATION = ['headers']
    JWT_HEADER_NAME = 'Authorization'
    JWT_HEADER_TYPE = 'Bearer'

    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///research_agent.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
    }

    # Server
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', 5000))

    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

    # Upload
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50 MB max upload
    UPLOAD_FOLDER = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        'uploads'
    )


class DevelopmentConfig(BaseConfig):
    """Development configuration."""
    DEBUG = True
    LOG_LEVEL = 'DEBUG'


class TestingConfig(BaseConfig):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(seconds=5)


class ProductionConfig(BaseConfig):
    """Production configuration."""
    DEBUG = False
    LOG_LEVEL = 'WARNING'

    # In production, these MUST be set via environment
    @property
    def SECRET_KEY(self):
        key = os.getenv('SECRET_KEY')
        if not key or key == 'dev-secret-key-change-in-production':
            raise ValueError("SECRET_KEY must be set in production!")
        return key


# Configuration registry
config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
}
