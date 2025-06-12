from flask import Blueprint
from app.api.endpoints.image_endpoints import image_bp

# Main API blueprint
api_bp = Blueprint('api', __name__, url_prefix='/api')

# Register all endpoints
api_bp.register_blueprint(image_bp, url_prefix='/images')

# Health check endpoint
@api_bp.route('/health', methods=['GET'])
def health_check():
    from flask import jsonify
    return jsonify({'status': 'OK'}), 200