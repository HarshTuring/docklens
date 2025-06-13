from flask import Blueprint, jsonify, current_app
from app.api.endpoints.image_endpoints import image_bp
from flasgger import swag_from
import datetime
import traceback

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
                'logs': '/api/images/logs',
                'history': '/api/images/history'
            }
        }
    }), 200

@api_bp.route('/test/connections', methods=['GET'])
def test_connections():
    """
    Test connections to MongoDB and Redis.
    Returns status of each connection with details.
    """
    result = {
        'timestamp': datetime.datetime.now().isoformat(),
        'mongodb': {
            'status': 'unknown',
            'details': None
        },
        'redis': {
            'status': 'unknown',
            'details': None
        },
        'overall': 'unknown'
    }
    
    # Test MongoDB connection
    try:
        # Get server info and ping to test connection
        server_info = current_app.db.command('serverStatus')
        ping_result = current_app.db.command('ping')
        
        if ping_result.get('ok') == 1.0:
            result['mongodb']['status'] = 'connected'
            result['mongodb']['details'] = {
                'version': server_info.get('version', 'unknown'),
                'uptime_seconds': server_info.get('uptime', 0),
                'connections': server_info.get('connections', {}).get('current', 0)
            }
        else:
            result['mongodb']['status'] = 'error'
            result['mongodb']['details'] = 'Ping command failed'
    except Exception as e:
        result['mongodb']['status'] = 'error'
        result['mongodb']['details'] = {
            'error': str(e),
            'traceback': traceback.format_exc()
        }
    
    # Test Redis connection
    try:
        # Ping Redis and get some info
        ping_response = current_app.redis.ping()
        info = current_app.redis.info()
        
        if ping_response:
            result['redis']['status'] = 'connected'
            result['redis']['details'] = {
                'version': info.get('redis_version', 'unknown'),
                'uptime_seconds': info.get('uptime_in_seconds', 0),
                'connected_clients': info.get('connected_clients', 0),
                'used_memory_human': info.get('used_memory_human', 'unknown')
            }
        else:
            result['redis']['status'] = 'error'
            result['redis']['details'] = 'Ping returned false'
    except Exception as e:
        result['redis']['status'] = 'error'
        result['redis']['details'] = {
            'error': str(e),
            'traceback': traceback.format_exc()
        }
    
    # Determine overall status
    if result['mongodb']['status'] == 'connected' and result['redis']['status'] == 'connected':
        result['overall'] = 'all_connected'
    elif result['mongodb']['status'] == 'error' and result['redis']['status'] == 'error':
        result['overall'] = 'all_failed'
    else:
        result['overall'] = 'partial'
    
    # Return status code based on overall status
    status_code = 200 if result['overall'] == 'all_connected' else 500
    
    return jsonify(result), status_code