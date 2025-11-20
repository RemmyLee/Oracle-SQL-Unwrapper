"""
Flask extensions initialization
Extensions are initialized here and then imported by the app factory
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_mail import Mail
from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flasgger import Swagger

# Initialize extensions (without app context)
db = SQLAlchemy()
login_manager = LoginManager()
cors = CORS()
jwt = JWTManager()
mail = Mail()
cache = Cache()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100 per minute"],
    storage_uri="memory://"  # Will be overridden by config
)
swagger = Swagger()


def init_extensions(app):
    """Initialize Flask extensions with app context"""

    # SQLAlchemy
    db.init_app(app)

    # Login Manager (for web sessions)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'

    # Load user for Flask-Login
    from backend.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # JWT Manager (for API authentication)
    jwt.init_app(app)

    # JWT error handlers
    from flask import jsonify

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        """Handle expired JWT tokens"""
        return jsonify({
            'success': False,
            'error': 'Token has expired',
            'message': 'Please log in again to get a new token'
        }), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        """Handle invalid JWT tokens"""
        return jsonify({
            'success': False,
            'error': 'Invalid token',
            'message': 'The provided token is invalid'
        }), 401

    @jwt.unauthorized_loader
    def unauthorized_callback(error):
        """Handle missing JWT tokens"""
        return jsonify({
            'success': False,
            'error': 'Authorization required',
            'message': 'Please provide a valid access token'
        }), 401

    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        """Handle revoked JWT tokens"""
        return jsonify({
            'success': False,
            'error': 'Token has been revoked',
            'message': 'This token is no longer valid'
        }), 401

    @jwt.needs_fresh_token_loader
    def needs_fresh_token_callback(jwt_header, jwt_payload):
        """Handle requests requiring fresh tokens"""
        return jsonify({
            'success': False,
            'error': 'Fresh token required',
            'message': 'This action requires a fresh access token. Please log in again.'
        }), 401

    # Mail
    mail.init_app(app)

    # Cache
    cache.init_app(app)

    # Rate Limiter
    if app.config.get('RATELIMIT_ENABLED', True):
        limiter.init_app(app)
        # Override storage with config
        if app.config.get('RATELIMIT_STORAGE_URL'):
            limiter.storage_uri = app.config['RATELIMIT_STORAGE_URL']

    # CORS
    cors.init_app(app, origins=app.config.get('CORS_ORIGINS', ['*']))

    # Swagger API Documentation
    if app.config.get('ENABLE_API_DOCS', False):
        swagger_config = {
            "headers": [],
            "specs": [
                {
                    "endpoint": 'apispec',
                    "route": '/apispec.json',
                    "rule_filter": lambda rule: True,
                    "model_filter": lambda tag: True,
                }
            ],
            "static_url_path": "/flasgger_static",
            "swagger_ui": True,
            "specs_route": "/api/docs/"
        }

        swagger_template = {
            "swagger": "2.0",
            "info": {
                "title": "PL/SQL Workbench API",
                "description": "RESTful API for Oracle PL/SQL Unwrapping, Query Management, and Dashboard System",
                "version": "1.0.0",
                "contact": {
                    "name": "API Support",
                    "email": "support@plsqlworkbench.com"
                },
                "license": {
                    "name": "MIT",
                    "url": "https://opensource.org/licenses/MIT"
                }
            },
            "host": app.config.get('API_HOST', 'localhost:8000'),
            "basePath": "/api",
            "schemes": ["https" if app.config.get('FORCE_HTTPS') else "http"],
            "securityDefinitions": {
                "Bearer": {
                    "type": "apiKey",
                    "name": "Authorization",
                    "in": "header",
                    "description": "JWT Authorization header using the Bearer scheme. Example: 'Bearer {token}'"
                }
            },
            "security": [
                {"Bearer": []}
            ],
            "tags": [
                {"name": "Auth", "description": "Authentication and user management"},
                {"name": "Unwrap", "description": "PL/SQL code unwrapping"},
                {"name": "Connections", "description": "Oracle database connections"},
                {"name": "Queries", "description": "SQL query execution"},
                {"name": "Saved Queries", "description": "Saved query templates"},
                {"name": "Dashboards", "description": "Dashboard management"},
                {"name": "Templates", "description": "Dashboard templates"},
                {"name": "Health", "description": "Health checks and monitoring"}
            ]
        }

        swagger.init_app(app, config=swagger_config, template=swagger_template)

    return app
