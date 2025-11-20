"""
Configuration management for PL/SQL Workbench
Supports multiple environments: development, testing, production
"""

import os
from datetime import timedelta


class Config:
    """Base configuration"""

    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'

    # Database (for app metadata, not Oracle connections)
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///plsql_workbench.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Encryption key for storing Oracle connection passwords
    ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY') or 'dev-encryption-key-change-in-production'

    # Redis (for caching and Celery)
    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/0'

    # Session
    SESSION_TYPE = 'filesystem'
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)

    # Security
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max upload

    # Unwrapper settings
    UNWRAP_MAX_INPUT_SIZE = 10 * 1024 * 1024  # 10MB
    UNWRAP_MAX_LINE_LENGTH = 32768
    UNWRAP_TIMEOUT_SECONDS = 30

    # Query execution settings
    QUERY_MAX_RESULT_ROWS = 10000
    QUERY_TIMEOUT_SECONDS = 300  # 5 minutes
    QUERY_FETCH_SIZE = 1000

    # Connection pool settings
    CONNECTION_POOL_MIN = 2
    CONNECTION_POOL_MAX = 10
    CONNECTION_POOL_INCREMENT = 1

    # API settings
    API_RATE_LIMIT = '100/minute'
    API_PAGINATION_DEFAULT = 50
    API_PAGINATION_MAX = 1000

    # CORS
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False

    # More verbose logging in development
    LOG_LEVEL = 'DEBUG'

    # Relaxed security for development
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True


class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = False
    TESTING = True

    # Use in-memory database for tests
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

    # Disable CSRF for testing
    WTF_CSRF_ENABLED = False

    # Faster for tests
    UNWRAP_TIMEOUT_SECONDS = 5
    QUERY_TIMEOUT_SECONDS = 10


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False

    # Strict security in production
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # Require environment variables in production
    SECRET_KEY = os.environ.get('SECRET_KEY')
    ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY')

    # Logging
    LOG_LEVEL = 'INFO'

    # Must use PostgreSQL in production
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')

    if not SECRET_KEY or not ENCRYPTION_KEY:
        raise ValueError("SECRET_KEY and ENCRYPTION_KEY must be set in production")


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}


def get_config(env=None):
    """Get configuration for specified environment"""
    if env is None:
        env = os.environ.get('FLASK_ENV', 'development')
    return config.get(env, config['default'])
