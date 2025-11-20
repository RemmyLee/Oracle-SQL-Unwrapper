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

    # Mail
    mail.init_app(app)

    # Cache
    cache.init_app(app)

    # CORS
    cors.init_app(app, origins=app.config.get('CORS_ORIGINS', ['*']))

    return app
