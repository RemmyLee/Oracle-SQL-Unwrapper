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

# Initialize extensions (without app context)
db = SQLAlchemy()
login_manager = LoginManager()
cors = CORS()
jwt = JWTManager()
mail = Mail()
cache = Cache()


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

    # CORS
    cors.init_app(app, origins=app.config.get('CORS_ORIGINS', ['*']))

    return app
