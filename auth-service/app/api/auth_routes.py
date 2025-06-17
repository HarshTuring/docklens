from flask import request, jsonify, current_app
from werkzeug.exceptions import BadRequest, Unauthorized
from marshmallow import Schema, fields, validate, ValidationError
from . import auth_bp
from ..services.auth_service import AuthService
from functools import wraps
import time

# Schema validation for endpoints
class RegisterSchema(Schema):
    email = fields.Email(required=True)
    password = fields.Str(required=True, validate=validate.Length(min=8))
    first_name = fields.Str(required=True)
    last_name = fields.Str(required=True)

class LoginSchema(Schema):
    email = fields.Email(required=True)
    password = fields.Str(required=True)

class ResetRequestSchema(Schema):
    email = fields.Email(required=True)

class ResetPasswordSchema(Schema):
    token = fields.Str(required=True)
    new_password = fields.Str(required=True, validate=validate.Length(min=8))

class RefreshTokenSchema(Schema):
    refresh_token = fields.Str(required=True)

class LogoutSchema(Schema):
    refresh_token = fields.Str(required=True)

# Utility function for rate limiting
def rate_limited(max_per_minute=5):
    """Simple decorator for rate limiting"""
    def decorator(f):
        last_requests = {}
        
        @wraps(f)
        def wrapped(*args, **kwargs):
            # Get client IP
            client_ip = request.remote_addr
            
            # Check if client IP has made too many requests
            now = time.time()
            if client_ip in last_requests:
                requests = [t for t in last_requests[client_ip] if now - t < 60]
                if len(requests) >= max_per_minute:
                    raise TooManyRequests("Rate limit exceeded. Please try again later.")
                last_requests[client_ip] = requests + [now]
            else:
                last_requests[client_ip] = [now]
            
            return f(*args, **kwargs)
        return wrapped
    return decorator

# Custom exception for rate limiting
class TooManyRequests(Exception):
    pass

# Helper to validate request data
def validate_request(schema):
    """Validate request data against schema"""
    try:
        if not request.is_json:
            raise BadRequest("Content-Type must be application/json")
        
        # For empty request body
        if not request.data:
            raise BadRequest("Request body is required")
            
        data = schema().load(request.get_json())
        return data
    except ValidationError as e:
        # Format validation errors
        errors = {}
        for field, messages in e.messages.items():
            errors[field] = messages[0] if isinstance(messages, list) else messages
        
        raise BadRequest({"errors": errors})

@auth_bp.route('/register', methods=['POST'])
@rate_limited(max_per_minute=5)
def register():
    """Register a new user"""
    try:
        # Validate request data
        data = validate_request(RegisterSchema)
        
        # Register user
        success, result = AuthService.register(
            email=data['email'],
            password=data['password'],
            first_name=data['first_name'],
            last_name=data['last_name']
        )
        
        if not success:
            raise BadRequest(result['error'])
        
        return jsonify(result), 201
        
    except BadRequest as e:
        # Re-raise to be handled by error handler
        raise
    except Exception as e:
        current_app.logger.error(f"Registration error: {str(e)}")
        # Don't expose internal errors to client
        raise BadRequest("Registration failed. Please try again later.")

@auth_bp.route('/login', methods=['POST'])
@rate_limited(max_per_minute=10)
def login():
    """Authenticate user and generate tokens"""
    try:
        # Validate request data
        data = validate_request(LoginSchema)
        
        # Login user
        success, result = AuthService.login(
            email=data['email'],
            password=data['password']
        )
        
        if not success:
            raise Unauthorized(result['error'])
        
        return jsonify(result), 200
        
    except Unauthorized as e:
        # Re-raise to be handled by error handler
        raise
    except BadRequest as e:
        # Re-raise to be handled by error handler
        raise
    except Exception as e:
        current_app.logger.error(f"Login error: {str(e)}")
        # Don't expose internal errors to client
        raise BadRequest("Login failed. Please try again later.")

@auth_bp.route('/refresh', methods=['POST'])
def refresh_token():
    """Refresh access token"""
    try:
        # Validate request data
        data = validate_request(RefreshTokenSchema)
        
        # Refresh token
        success, result = AuthService.refresh_token(
            refresh_token=data['refresh_token']
        )
        
        if not success:
            raise Unauthorized(result['error'])
        
        return jsonify(result), 200
        
    except Unauthorized as e:
        # Re-raise to be handled by error handler
        raise
    except BadRequest as e:
        # Re-raise to be handled by error handler
        raise
    except Exception as e:
        current_app.logger.error(f"Token refresh error: {str(e)}")
        # Don't expose internal errors to client
        raise BadRequest("Token refresh failed. Please try again later.")

@auth_bp.route('/logout', methods=['POST'])
def logout():
    """Logout user by revoking refresh token"""
    try:
        # Validate request data
        data = validate_request(LogoutSchema)
        
        # Logout user
        success, result = AuthService.logout(
            refresh_token=data['refresh_token']
        )
        
        if not success:
            # Even if token is invalid, return success for security reasons
            return jsonify({"message": "Successfully logged out"}), 200
        
        return jsonify(result), 200
        
    except BadRequest as e:
        # Re-raise to be handled by error handler
        raise
    except Exception as e:
        current_app.logger.error(f"Logout error: {str(e)}")
        # Don't expose internal errors, just return success
        return jsonify({"message": "Successfully logged out"}), 200

@auth_bp.route('/password-reset/request', methods=['POST'])
@rate_limited(max_per_minute=3)
def request_password_reset():
    """Request password reset"""
    try:
        # Validate request data
        data = validate_request(ResetRequestSchema)
        
        # Request password reset
        success, result = AuthService.request_password_reset(
            email=data['email']
        )
        
        # Always return success for security (don't reveal if email exists)
        return jsonify(result), 200
        
    except BadRequest as e:
        # Re-raise to be handled by error handler
        raise
    except Exception as e:
        current_app.logger.error(f"Password reset request error: {str(e)}")
        # Return generic success message for security
        return jsonify({
            "message": "If your email is registered, you will receive a password reset link"
        }), 200

@auth_bp.route('/password-reset/confirm', methods=['POST'])
def reset_password():
    """Reset password using token"""
    try:
        # Validate request data
        data = validate_request(ResetPasswordSchema)
        
        # Reset password
        success, result = AuthService.reset_password(
            reset_token=data['token'],
            new_password=data['new_password']
        )
        
        if not success:
            raise BadRequest(result['error'])
        
        return jsonify(result), 200
        
    except BadRequest as e:
        # Re-raise to be handled by error handler
        raise
    except Exception as e:
        current_app.logger.error(f"Password reset confirm error: {str(e)}")
        # Don't expose internal errors to client
        raise BadRequest("Password reset failed. Please try again later.")

@auth_bp.route('/verify-email/<token>', methods=['GET'])
def verify_email(token):
    """Verify user's email using token"""
    try:
        if not token:
            raise BadRequest("Verification token is required")
        
        # Verify email
        success, result = AuthService.verify_email(token)
        
        if not success:
            raise BadRequest(result['error'])
        
        return jsonify(result), 200
        
    except BadRequest as e:
        # Re-raise to be handled by error handler
        raise
    except Exception as e:
        current_app.logger.error(f"Email verification error: {str(e)}")
        # Don't expose internal errors to client
        raise BadRequest("Email verification failed. Please try again later.")

@auth_bp.route('/validate', methods=['POST'])
def validate_token():
    """Validate an access token (for use by other services)"""
    try:
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            raise Unauthorized("Missing or invalid Authorization header")
        
        token = auth_header.split(' ')[1]
        
        # Validate token
        success, result = AuthService.validate_token(token)
        
        if not success:
            raise Unauthorized(result['error'])
        
        return jsonify(result), 200
        
    except Unauthorized as e:
        # Re-raise to be handled by error handler
        raise
    except Exception as e:
        current_app.logger.error(f"Token validation error: {str(e)}")
        # Don't expose internal errors to client
        raise Unauthorized("Token validation failed")

@auth_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    # Check MongoDB connection
    try:
        from ..models.user import UserModel
        UserModel.get_collection().find_one({}, {'_id': 1})
        return jsonify({
            "status": "healthy", 
            "timestamp": time.time(),
            "service": "auth"
        }), 200
    except Exception as e:
        current_app.logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            "status": "unhealthy",
            "message": str(e),
            "timestamp": time.time(),
            "service": "auth"
        }), 500