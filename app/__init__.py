from flask import Flask
import os
from app.config import get_config
from flasgger import Swagger

def create_app(config_name=None):
    """Application factory function."""
    app = Flask(__name__)
    
    # Load config
    app.config.from_object(get_config())
    
    # Ensure directories exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(os.path.join(app.static_folder, 'processed_images'), exist_ok=True)
    os.makedirs(os.path.join(app.root_path, app.config['LOG_DIR']), exist_ok=True)
    
    # Register blueprints
    from app.api.routes import api_bp
    app.register_blueprint(api_bp)
    
    # Initialize Swagger documentation
    swagger_config = {
        "headers": [],
        "specs": [
            {
                "endpoint": "apispec",
                "route": "/apispec.json",
                "rule_filter": lambda rule: True,  # all in
                "model_filter": lambda tag: True,  # all in
            }
        ],
        "static_url_path": "/flasgger_static",
        "swagger_ui": True,
        "specs_route": "/docs"
    }
    
    swagger_template = {
        "info": {
            "title": "Image Processing API",
            "description": "API for image processing operations including upload and grayscale conversion",
            "version": "1.0.0",
            "contact": {
                "email": "support@example.com"
            }
        },
        "schemes": [
            "http",
            "https"
        ],
        "tags": [
            {
                "name": "Image Operations",
                "description": "Endpoints for uploading and processing images"
            },
            {
                "name": "Logs",
                "description": "Endpoints for accessing operation logs"
            }
        ],
        "components": {
            "schemas": {
                "Error": {
                    "type": "object",
                    "properties": {
                        "error": {
                            "type": "string",
                            "description": "Error message"
                        }
                    }
                },
                "UploadResponse": {
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "Status message"
                        },
                        "filename": {
                            "type": "string",
                            "description": "Stored filename"
                        },
                        "processing": {
                            "type": "object",
                            "description": "Processing details"
                        }
                    }
                }
            }
        }
    }
    
    swagger = Swagger(app, config=swagger_config, template=swagger_template)
    
    return app