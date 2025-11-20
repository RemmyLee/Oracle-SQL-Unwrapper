"""
Main Flask application factory
Creates and configures the Flask application
"""

import os
from flask import Flask, jsonify, render_template
from backend.config import get_config
from backend.extensions import init_extensions, db


def create_app(config_name=None):
    """
    Application factory pattern

    Args:
        config_name: Configuration environment (development, testing, production)

    Returns:
        Configured Flask application
    """

    # Create Flask app
    app = Flask(__name__,
                template_folder='../templates',
                static_folder='../frontend/dist')

    # Load configuration
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    config_class = get_config(config_name)
    app.config.from_object(config_class)

    # Initialize extensions
    init_extensions(app)

    # Register blueprints
    register_blueprints(app)

    # Register error handlers
    register_error_handlers(app)

    # Create database tables
    with app.app_context():
        db.create_all()

    return app


def register_blueprints(app):
    """Register Flask blueprints (API routes)"""

    from backend.api.unwrap import unwrap_bp
    from backend.api.connections import connections_bp
    from backend.api.queries import queries_bp
    from backend.api.export import export_bp
    from backend.api.saved_queries import saved_queries_bp
    from backend.api.templates import templates_bp
    from backend.api.auth import auth_bp
    from backend.api.users import users_bp
    from backend.api.roles import roles_bp
    from backend.api.admin import admin_bp
    from backend.api.dashboards import dashboards_bp

    # Register API blueprints
    app.register_blueprint(unwrap_bp, url_prefix='/api')
    app.register_blueprint(connections_bp, url_prefix='/api')
    app.register_blueprint(queries_bp, url_prefix='/api')
    app.register_blueprint(export_bp, url_prefix='/api')
    app.register_blueprint(saved_queries_bp, url_prefix='/api')
    app.register_blueprint(templates_bp, url_prefix='/api')
    app.register_blueprint(auth_bp, url_prefix='/api')
    app.register_blueprint(users_bp, url_prefix='/api')
    app.register_blueprint(roles_bp, url_prefix='/api')
    app.register_blueprint(admin_bp, url_prefix='/api')
    app.register_blueprint(dashboards_bp, url_prefix='/api')

    # Root route for frontend
    @app.route('/')
    def index():
        """Serve main application page"""
        return render_template('index.html')

    return app


def register_error_handlers(app):
    """Register error handlers for common HTTP errors"""

    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': str(error)
        }), 400

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'The requested resource was not found'
        }), 404

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': 'An unexpected error occurred'
        }), 500

    @app.errorhandler(413)
    def request_entity_too_large(error):
        return jsonify({
            'success': False,
            'error': 'Request too large',
            'message': f"Maximum upload size is {app.config['MAX_CONTENT_LENGTH'] / (1024*1024)}MB"
        }), 413

    return app


# For running directly with python app.py
if __name__ == '__main__':
    app = create_app()
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 3117)),
        debug=app.config['DEBUG']
    )
