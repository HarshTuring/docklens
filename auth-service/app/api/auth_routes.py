from flask import request, jsonify, current_app
from werkzeug.exceptions import BadRequest, Unauthorized
from marshmallow import Schema, fields, validate, ValidationError
from . import auth_bp
from ..services.auth_service import AuthService
from functools import wraps
import time
from flasgger import swag_from


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
@swag_from({
    "tags": ["Authentication"],
    "summary": "Register a new user",
    "description": "Creates a new user account with the provided details",
    "parameters": [
        {
            "name": "body",
            "in": "body",
            "required": True,
            "schema": {
                "type": "object",
                "required": ["email", "password", "first_name", "last_name"],
                "properties": {
                    "email": {
                        "type": "string",
                        "format": "email",
                        "description": "User's email address"
                    },
                    "password": {
                        "type": "string",
                        "description": "Password (min 8 characters)"
                    },
                    "first_name": {
                        "type": "string",
                        "description": "User's first name"
                    },
                    "last_name": {
                        "type": "string",
                        "description": "User's last name"
                    }
                }
            }
        }
    ],
    "responses": {
        "201": {
            "description": "User successfully registered",
            "schema": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "example": "User registered successfully"
                    },
                    "user_id": {
                        "type": "string",
                        "example": "60d21b4667d0d8992e610c85"
                    },
                    "email": {
                        "type": "string",
                        "example": "user@example.com"
                    }
                }
            }
        },
        "400": {
            "description": "Bad request - invalid input",
            "schema": {
                "type": "object",
                "properties": {
                    "error": {
                        "type": "string",
                        "example": "Email already registered"
                    }
                }
            }
        },
        "429": {
            "description": "Rate limit exceeded",
            "schema": {
                "type": "object",
                "properties": {
                    "error": {
                        "type": "string",
                        "example": "Too Many Requests"
                    },
                    "message": {
                        "type": "string",
                        "example": "Rate limit exceeded"
                    }
                }
            }
        }
    }
})
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
@swag_from({
    "tags": ["Authentication"],
    "summary": "Login user",
    "description": "Authenticate user and get access/refresh tokens",
    "parameters": [
        {
            "name": "body",
            "in": "body",
            "required": True,
            "schema": {
                "type": "object",
                "required": ["email", "password"],
                "properties": {
                    "email": {
                        "type": "string",
                        "format": "email",
                        "description": "User's email address"
                    },
                    "password": {
                        "type": "string",
                        "description": "User's password"
                    }
                }
            }
        }
    ],
    "responses": {
        "200": {
            "description": "Login successful",
            "schema": {
                "type": "object",
                "properties": {
                    "access_token": {
                        "type": "string",
                        "example": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
                    },
                    "refresh_token": {
                        "type": "string",
                        "example": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
                    },
                    "expires_in": {
                        "type": "integer",
                        "example": 900
                    },
                    "token_type": {
                        "type": "string",
                        "example": "Bearer"
                    }
                }
            }
        },
        "401": {
            "description": "Authentication failed",
            "schema": {
                "type": "object",
                "properties": {
                    "error": {
                        "type": "string",
                        "example": "Invalid email or password"
                    }
                }
            }
        },
        "429": {
            "description": "Rate limit exceeded",
            "schema": {
                "type": "object",
                "properties": {
                    "error": {
                        "type": "string",
                        "example": "Too Many Requests"
                    },
                    "message": {
                        "type": "string",
                        "example": "Rate limit exceeded"
                    }
                }
            }
        }
    }
})
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
@swag_from({
    "tags": ["Authentication"],
    "summary": "Refresh access token",
    "description": "Get a new access token using a valid refresh token",
    "parameters": [
        {
            "name": "body",
            "in": "body",
            "required": True,
            "schema": {
                "type": "object",
                "required": ["refresh_token"],
                "properties": {
                    "refresh_token": {
                        "type": "string",
                        "description": "Valid refresh token"
                    }
                }
            }
        }
    ],
    "responses": {
        "200": {
            "description": "Token refresh successful",
            "schema": {
                "type": "object",
                "properties": {
                    "access_token": {
                        "type": "string",
                        "example": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
                    },
                    "expires_in": {
                        "type": "integer",
                        "example": 900
                    },
                    "token_type": {
                        "type": "string",
                        "example": "Bearer"
                    }
                }
            }
        },
        "401": {
            "description": "Invalid refresh token",
            "schema": {
                "type": "object",
                "properties": {
                    "error": {
                        "type": "string",
                        "example": "Invalid or expired refresh token"
                    }
                }
            }
        }
    }
})
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
@swag_from({
    "tags": ["Authentication"],
    "summary": "Logout user",
    "description": "Invalidate refresh token to implement logout",
    "parameters": [
        {
            "name": "body",
            "in": "body",
            "required": True,
            "schema": {
                "type": "object",
                "required": ["refresh_token"],
                "properties": {
                    "refresh_token": {
                        "type": "string",
                        "description": "Refresh token to invalidate"
                    }
                }
            }
        }
    ],
    "responses": {
        "200": {
            "description": "Logout successful",
            "schema": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "example": "Successfully logged out"
                    }
                }
            }
        },
        "400": {
            "description": "Bad request",
            "schema": {
                "type": "object",
                "properties": {
                    "error": {
                        "type": "string",
                        "example": "Refresh token required"
                    }
                }
            }
        }
    }
})
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
@swag_from({
    "tags": ["Password Management"],
    "summary": "Request password reset",
    "description": "Request a password reset link to be sent to user's email",
    "parameters": [
        {
            "name": "body",
            "in": "body",
            "required": True,
            "schema": {
                "type": "object",
                "required": ["email"],
                "properties": {
                    "email": {
                        "type": "string",
                        "format": "email",
                        "description": "Email address for account recovery"
                    }
                }
            }
        }
    ],
    "responses": {
        "200": {
            "description": "Password reset request successful",
            "schema": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "example": "If your email is registered, you will receive a password reset link"
                    }
                }
            }
        },
        "429": {
            "description": "Rate limit exceeded",
            "schema": {
                "type": "object",
                "properties": {
                    "error": {
                        "type": "string",
                        "example": "Too Many Requests"
                    },
                    "message": {
                        "type": "string",
                        "example": "Rate limit exceeded"
                    }
                }
            }
        }
    }
})
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
@swag_from({
    "tags": ["Password Management"],
    "summary": "Reset password",
    "description": "Reset password using the token provided in the reset link",
    "parameters": [
        {
            "name": "body",
            "in": "body",
            "required": True,
            "schema": {
                "type": "object",
                "required": ["token", "new_password"],
                "properties": {
                    "token": {
                        "type": "string",
                        "description": "Password reset token received via email"
                    },
                    "new_password": {
                        "type": "string",
                        "description": "New password (min 8 characters)"
                    }
                }
            }
        }
    ],
    "responses": {
        "200": {
            "description": "Password reset successful",
            "schema": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "example": "Password reset successful. You can now login with your new password."
                    }
                }
            }
        },
        "400": {
            "description": "Bad request - invalid token or password",
            "schema": {
                "type": "object",
                "properties": {
                    "error": {
                        "type": "string",
                        "example": "Invalid or expired token"
                    }
                }
            }
        }
    }
})
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
@swag_from({
    "tags": ["Account Management"],
    "summary": "Verify email address",
    "description": "Verify user's email address using token sent to their email",
    "parameters": [
        {
            "name": "token",
            "in": "path",
            "type": "string",
            "required": True,
            "description": "Verification token"
        }
    ],
    "responses": {
        "200": {
            "description": "Email verification successful",
            "schema": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "example": "Email verified successfully"
                    }
                }
            }
        },
        "400": {
            "description": "Bad request - invalid token",
            "schema": {
                "type": "object",
                "properties": {
                    "error": {
                        "type": "string",
                        "example": "Invalid or expired verification token"
                    }
                }
            }
        }
    }
})
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
@swag_from({
    "tags": ["Token Management"],
    "summary": "Validate access token",
    "description": "Validate a JWT access token (for internal service use)",
    "parameters": [
        {
            "name": "Authorization",
            "in": "header",
            "type": "string",
            "required": True,
            "description": "Bearer token to validate"
        }
    ],
    "responses": {
        "200": {
            "description": "Token validation successful",
            "schema": {
                "type": "object",
                "properties": {
                    "valid": {
                        "type": "boolean",
                        "example": True
                    },
                    "user_id": {
                        "type": "string",
                        "example": "60d21b4667d0d8992e610c85"
                    },
                    "roles": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        },
                        "example": ["user"]
                    },
                    "permissions": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        },
                        "example": ["read:profile", "update:profile"]
                    }
                }
            }
        },
        "401": {
            "description": "Invalid token",
            "schema": {
                "type": "object",
                "properties": {
                    "error": {
                        "type": "string",
                        "example": "Invalid or expired token"
                    }
                }
            }
        }
    }
})
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
@swag_from({
    "tags": ["System"],
    "summary": "Service health check",
    "description": "Check if the auth service is running correctly and connected to MongoDB",
    "responses": {
        "200": {
            "description": "Service is healthy",
            "schema": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "example": "healthy"
                    },
                    "timestamp": {
                        "type": "number",
                        "example": 1625176047.433459
                    },
                    "service": {
                        "type": "string",
                        "example": "auth"
                    }
                }
            }
        },
        "500": {
            "description": "Service is unhealthy",
            "schema": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "example": "unhealthy"
                    },
                    "message": {
                        "type": "string",
                        "example": "Database connection failed"
                    },
                    "timestamp": {
                        "type": "number",
                        "example": 1625176047.433459
                    },
                    "service": {
                        "type": "string",
                        "example": "auth"
                    }
                }
            }
        }
    }
})
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