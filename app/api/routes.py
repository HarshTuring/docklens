from flask import Blueprint, jsonify, current_app
from app.api.endpoints.image_endpoints import image_bp
from flasgger import swag_from

# Main API blueprint
api_bp = Blueprint('api', __name__, url_prefix='/api')

# Register all endpoints
api_bp.register_blueprint(image_bp, url_prefix='/images')

# Health check endpoint
@api_bp.route('/health', methods=['GET'])
@swag_from({
    "tags": ["System"],
    "summary": "Health check endpoint",
    "description": "Used to check if the API is running",
    "produces": ["application/json"],
    "responses": {
        "200": {
            "description": "API is healthy",
            "schema": {
                "type": "object",
                "properties": {
                    "status": {"type": "string"}
                }
            }
        }
    }
})
def health_check():
    """Health check endpoint for Docker."""
    try:
        # Check MongoDB connection
        db_ping = current_app.db.command('ping')
        mongodb_status = 'ok' if db_ping.get('ok') == 1.0 else 'error'
        
        # Check Redis connection
        redis_status = 'ok' if current_app.redis.ping() else 'error'
        
        if mongodb_status == 'ok' and redis_status == 'ok':
            return jsonify({
                'status': 'healthy',
                'mongodb': mongodb_status,
                'redis': redis_status
            }), 200
        else:
            return jsonify({
                'status': 'degraded',
                'mongodb': mongodb_status,
                'redis': redis_status
            }), 500
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

# API index endpoint
@api_bp.route('/', methods=['GET'])
@swag_from({
    "tags": ["System"],
    "summary": "API root endpoint",
    "description": "Returns basic API information and available endpoints",
    "produces": ["application/json"],
    "responses": {
        "200": {
            "description": "API information",
            "schema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "version": {"type": "string"},
                    "description": {"type": "string"},
                    "endpoints": {
                        "type": "object",
                        "properties": {
                            "health": {"type": "string"},
                            "docs": {"type": "string"},
                            "images": {"type": "object"}
                        }
                    }
                }
            }
        }
    }
})
def api_index():
    return jsonify({
        'name': 'Image Processing API',
        'version': '1.0.0',
        'description': 'API for image processing operations including upload and grayscale conversion',
        'endpoints': {
            'health': '/api/health',
            'docs': '/docs',
            'images': {
                'upload': '/api/images/upload',
                'grayscale': '/api/images/grayscale',
                'grayscale_url': '/api/images/grayscale-url',
                'logs': '/api/images/logs'
            }
        }
    }), 200