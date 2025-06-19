from flask import jsonify
from werkzeug.exceptions import HTTPException
import traceback
import logging

logger = logging.getLogger(__name__)

def handle_bad_request(e):
    """Handle 400 errors"""
    return jsonify(error="Bad Request", message=str(e)), 400

def handle_unauthorized(e):
    """Handle 401 errors"""
    return jsonify(error="Unauthorized", message="Authentication required"), 401

def handle_forbidden(e):
    """Handle 403 errors"""
    return jsonify(error="Forbidden", message="You don't have permission to access this resource"), 403

def handle_not_found(e):
    """Handle 404 errors"""
    return jsonify(error="Not Found", message="The requested resource was not found"), 404

def handle_method_not_allowed(e):
    """Handle 405 errors"""
    return jsonify(error="Method Not Allowed", message="The method is not allowed for this resource"), 405

def handle_conflict(e):
    """Handle 409 errors"""
    return jsonify(error="Conflict", message=str(e)), 409

def handle_too_many_requests(e):
    """Handle 429 errors"""
    return jsonify(error="Too Many Requests", message="Rate limit exceeded"), 429

def handle_internal_server_error(e):
    """Handle 500 errors"""
    # Log the full error with traceback for debugging
    logger.error(f"Internal Server Error: {str(e)}")
    logger.error(traceback.format_exc())
    
    # Return generic error message to client
    return jsonify(
        error="Internal Server Error", 
        message="An unexpected error occurred"
    ), 500

def register_error_handlers(app):
    """Register error handlers with Flask app"""
    app.register_error_handler(400, handle_bad_request)
    app.register_error_handler(401, handle_unauthorized)
    app.register_error_handler(403, handle_forbidden)
    app.register_error_handler(404, handle_not_found)
    app.register_error_handler(405, handle_method_not_allowed)
    app.register_error_handler(409, handle_conflict)
    app.register_error_handler(429, handle_too_many_requests)
    app.register_error_handler(500, handle_internal_server_error)
    
    # Generic handler for all HTTPExceptions
    @app.errorhandler(HTTPException)
    def handle_http_exception(e):
        response = e.get_response()
        response.data = jsonify(
            error=e.name,
            message=e.description
        ).data
        response.content_type = "application/json"
        return response
    
    # Catch-all for unhandled exceptions
    @app.errorhandler(Exception)
    def handle_exception(e):
        return handle_internal_server_error(e)