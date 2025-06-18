from flask import Flask
from pymongo import MongoClient
from flask_cors import CORS
import os
import logging
from logging.handlers import RotatingFileHandler

# Initialize extensions
mongo_client = None

def create_app():
    """Create and configure the Flask application"""
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object('app.config.settings.Config')
    
    # Override with environment variables
    app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['MONGO_URI'] = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/auth_db')
    app.config['ACCESS_TOKEN_EXPIRE_MINUTES'] = int(os.environ.get('ACCESS_TOKEN_EXPIRE_MINUTES', 15))
    app.config['TOKEN_EXPIRE_HOURS'] = int(os.environ.get('TOKEN_EXPIRE_HOURS', 24))
    
    # Setup logging
    if not os.path.exists('logs'):
        os.mkdir('logs')
    file_handler = RotatingFileHandler('logs/auth_service.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('Auth service startup')
    
    # Initialize MongoDB
    global mongo_client
    mongo_client = MongoClient(app.config['MONGO_URI'])
    app.mongo = mongo_client
    app.db = mongo_client.get_database()
    
    # Setup CORS
    CORS(app, resources={
        r"/auth/*": {"origins": "*"},  # JWT auth endpoints can be called from anywhere
        r"/users/*": {"origins": os.environ.get('ALLOWED_ORIGINS', '*').split(',')}  # User endpoints more restricted
    })
    
    # Initialize models (create indexes)
    with app.app_context():
        from app.models.user import UserModel
        from app.models.role import RoleModel
        from app.models.token import TokenModel
        
        UserModel.create_indexes()
        RoleModel.create_indexes()
        TokenModel.create_indexes()
        
        # Create default roles
        RoleModel.create_default_roles()
    
    # Register API blueprints
    from app.api import init_app as init_api
    init_api(app)
    
    # Additional security headers
    @app.after_request
    def add_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['Content-Security-Policy'] = "default-src 'self'"
        return response
    
    return app

# Create application instance
app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True)