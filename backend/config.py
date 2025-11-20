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

    # JWT Configuration
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or SECRET_KEY
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_TOKEN_LOCATION = ['headers', 'cookies']
    JWT_COOKIE_SECURE = False  # Set to True in production
    JWT_COOKIE_CSRF_PROTECT = True
    JWT_COOKIE_SAMESITE = 'Lax'

    # Email Configuration (Flask-Mail)
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'localhost')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'false').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@plsql-workbench.local')

    # Cache Configuration
    CACHE_TYPE = 'simple'  # Use Redis in production
    CACHE_DEFAULT_TIMEOUT = 300  # 5 minutes
    CACHE_KEY_PREFIX = 'plsql_workbench:'

    # User Management
    PASSWORD_MIN_LENGTH = 8
    PASSWORD_REQUIRE_UPPERCASE = True
    PASSWORD_REQUIRE_LOWERCASE = True
    PASSWORD_REQUIRE_DIGITS = True
    PASSWORD_REQUIRE_SPECIAL = True
    ACCOUNT_LOCKOUT_ATTEMPTS = 5
    ACCOUNT_LOCKOUT_DURATION = timedelta(minutes=30)
    EMAIL_VERIFICATION_REQUIRED = True
    EMAIL_VERIFICATION_TOKEN_EXPIRES = timedelta(days=1)
    PASSWORD_RESET_TOKEN_EXPIRES = timedelta(hours=1)

    # Dashboard Settings (Phase 5)
    DASHBOARD_MAX_COMPONENTS = int(os.environ.get('DASHBOARD_MAX_COMPONENTS', 50))
    DASHBOARD_MAX_DATA_SOURCES = int(os.environ.get('DASHBOARD_MAX_DATA_SOURCES', 20))
    DASHBOARD_CACHE_DEFAULT_TTL = int(os.environ.get('DASHBOARD_CACHE_DEFAULT_TTL', 300))
    DASHBOARD_QUERY_TIMEOUT = int(os.environ.get('DASHBOARD_QUERY_TIMEOUT', 30))
    DASHBOARD_MAX_VERSIONS = int(os.environ.get('DASHBOARD_MAX_VERSIONS', 50))
    DASHBOARD_AUTO_VERSION = os.environ.get('DASHBOARD_AUTO_VERSION', 'false').lower() == 'true'

    # Rate Limiting
    RATELIMIT_ENABLED = True
    RATELIMIT_STORAGE_URL = os.environ.get('REDIS_URL', 'memory://')
    RATELIMIT_STRATEGY = 'fixed-window'
    RATELIMIT_HEADERS_ENABLED = True
    RATELIMIT_DEFAULT = os.environ.get('RATELIMIT_DEFAULT', '100 per minute')
    RATELIMIT_API_STRICT = os.environ.get('RATELIMIT_API_STRICT', '1000 per hour')
    RATELIMIT_AUTH = os.environ.get('RATELIMIT_AUTH', '5 per minute')
    RATELIMIT_PUBLIC = os.environ.get('RATELIMIT_PUBLIC', '50 per minute')

    # Health Check & Monitoring
    HEALTH_CHECK_ENABLED = True
    METRICS_ENABLED = True
    METRICS_PORT = int(os.environ.get('METRICS_PORT', 9090))

    # API Documentation
    ENABLE_API_DOCS = os.environ.get('ENABLE_API_DOCS', 'false').lower() == 'true'
    API_HOST = os.environ.get('API_HOST', 'localhost:8000')
    SWAGGER = {
        'title': 'PL/SQL Workbench API',
        'version': '1.0.0',
        'description': 'Enterprise Dashboard & Query Management System for Oracle Databases',
        'termsOfService': '',
        'contact': {
            'name': 'API Support',
            'email': 'support@plsqlworkbench.com'
        },
        'specs_route': '/api/docs/',
        'securityDefinitions': {
            'Bearer': {
                'type': 'apiKey',
                'name': 'Authorization',
                'in': 'header',
                'description': 'JWT Authorization header using the Bearer scheme. Example: "Authorization: Bearer {token}"'
            }
        },
        'security': [{'Bearer': []}]
    }

    # Database Pool Settings (Production)
    SQLALCHEMY_POOL_SIZE = int(os.environ.get('DB_POOL_SIZE', 10))
    SQLALCHEMY_MAX_OVERFLOW = int(os.environ.get('DB_MAX_OVERFLOW', 20))
    SQLALCHEMY_POOL_TIMEOUT = int(os.environ.get('DB_POOL_TIMEOUT', 30))
    SQLALCHEMY_POOL_RECYCLE = int(os.environ.get('DB_POOL_RECYCLE', 3600))
    SQLALCHEMY_ECHO = False

    # Background Tasks
    SCHEDULER_API_ENABLED = True
    SCHEDULER_TIMEZONE = os.environ.get('SCHEDULER_TIMEZONE', 'UTC')

    # Security Headers
    TALISMAN_FORCE_HTTPS = os.environ.get('FORCE_HTTPS', 'false').lower() == 'true'
    TALISMAN_STRICT_TRANSPORT_SECURITY = True
    TALISMAN_CONTENT_SECURITY_POLICY = {
        'default-src': "'self'",
        'script-src': ["'self'", "'unsafe-inline'"],
        'style-src': ["'self'", "'unsafe-inline'"],
        'img-src': ["'self'", 'data:', 'https:'],
        'font-src': ["'self'", 'data:']
    }


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False

    # More verbose logging in development
    LOG_LEVEL = 'DEBUG'

    # Relaxed security for development
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True

    # Disable rate limiting in development
    RATELIMIT_ENABLED = False

    # Disable security headers in development
    TALISMAN_FORCE_HTTPS = False

    # Enable API documentation in development
    ENABLE_API_DOCS = True

    # More lenient limits for development
    DASHBOARD_MAX_COMPONENTS = 100
    DASHBOARD_MAX_DATA_SOURCES = 50


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

    # JWT security in production
    JWT_COOKIE_SECURE = True

    # Require environment variables in production
    SECRET_KEY = os.environ.get('SECRET_KEY')
    ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY')
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or SECRET_KEY

    # Cache with Redis in production
    CACHE_TYPE = 'redis'
    CACHE_REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

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
