"""
Flask extensions initialization
Extensions are initialized here and then imported by the app factory
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_cors import CORS

# Initialize extensions (without app context)
db = SQLAlchemy()
login_manager = LoginManager()
cors = CORS()


def init_extensions(app):
    """Initialize Flask extensions with app context"""

    # SQLAlchemy
    db.init_app(app)

    # Login Manager
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'

    # CORS
    cors.init_app(app, origins=app.config['CORS_ORIGINS'])

    return app
