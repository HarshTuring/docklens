from flask import Blueprint

# Create auth blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# Create users blueprint
users_bp = Blueprint('users', __name__, url_prefix='/users')

# Import routes to register them with the blueprints
from . import auth_routes, user_routes

def init_app(app):
    """Register blueprints with the Flask app"""
    app.register_blueprint(auth_bp)
    app.register_blueprint(users_bp)
    
    # Register error handlers
    from .error_handlers import register_error_handlers
    register_error_handlers(app)