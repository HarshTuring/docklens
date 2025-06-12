from flask import Flask
import os
from app.config import get_config

def create_app(config_name=None):
    """Application factory function."""
    app = Flask(__name__)
    
    # Load config
    app.config.from_object(get_config())
    
    # Ensure upload directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Register blueprints
    from app.api.routes import api_bp
    app.register_blueprint(api_bp)
    
    return app