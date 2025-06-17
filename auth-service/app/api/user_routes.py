from flask import request, jsonify, current_app
from werkzeug.exceptions import BadRequest, Unauthorized, Forbidden, NotFound
from marshmallow import Schema, fields, validate, ValidationError
from . import users_bp
from ..services.user_service import UserService
from ..services.jwt_service import JWTService
from functools import wraps

# Schema validation for endpoints
class UpdateUserSchema(Schema):
    first_name = fields.Str(required=False)
    last_name = fields.Str(required=False)
    active = fields.Bool(required=False)

class ChangePasswordSchema(Schema):
    current_password = fields.Str(required=True)
    new_password = fields.Str(required=True, validate=validate.Length(min=8))

# Utils for authentication
def auth_required(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            # Get token from Authorization header
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                raise Unauthorized("Missing or invalid Authorization header")
            
            token = auth_header.split(' ')[1]
            
            # Validate token
            payload = JWTService.validate_access_token(token)
            if not payload:
                raise Unauthorized("Invalid or expired token")
            
            # Add user_id to request context
            request.user_id = payload.get('sub')
            request.user_roles = payload.get('roles', [])
            request.user_permissions = payload.get('permissions', [])
            
            return f(*args, **kwargs)
            
        except Unauthorized as e:
            # Re-raise to be handled by error handler
            raise
        except Exception as e:
            current_app.logger.error(f"Authentication error: {str(e)}")
            raise Unauthorized("Authentication failed")
    
    return decorated

def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    @auth_required
    def decorated(*args, **kwargs):
        if 'admin' not in request.user_roles:
            raise Forbidden("Admin access required")
        return f(*args, **kwargs)
    
    return decorated

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

@users_bp.route('/me', methods=['GET'])
@auth_required
def get_current_user():
    """Get current user profile"""
    try:
        success, result = UserService.get_user(request.user_id)
        
        if not success:
            raise NotFound(result['error'])
        
        return jsonify(result), 200
        
    except NotFound as e:
        # Re-raise to be handled by error handler
        raise
    except Exception as e:
        current_app.logger.error(f"Get current user error: {str(e)}")
        raise BadRequest("Failed to retrieve user profile")

@users_bp.route('/me', methods=['PUT'])
@auth_required
def update_current_user():
    """Update current user profile"""
    try:
        # Validate request data
        data = validate_request(UpdateUserSchema)
        
        # Remove 'active' from normal user updates (only admins can change this)
        if 'admin' not in request.user_roles and 'active' in data:
            del data['active']
        
        # Update user
        success, result = UserService.update_user(
            user_id=request.user_id,
            update_data=data,
            current_user_id=request.user_id
        )
        
        if not success:
            raise BadRequest(result['error'])
        
        return jsonify(result), 200
        
    except BadRequest as e:
        # Re-raise to be handled by error handler
        raise
    except Exception as e:
        current_app.logger.error(f"Update current user error: {str(e)}")
        raise BadRequest("Failed to update user profile")

@users_bp.route('/me/password', methods=['PUT'])
@auth_required
def change_current_user_password():
    """Change current user password"""
    try:
        # Validate request data
        data = validate_request(ChangePasswordSchema)
        
        # Change password
        success, result = UserService.change_password(
            user_id=request.user_id,
            current_password=data['current_password'],
            new_password=data['new_password'],
            current_user_id=request.user_id
        )
        
        if not success:
            raise BadRequest(result['error'])
        
        return jsonify(result), 200
        
    except BadRequest as e:
        # Re-raise to be handled by error handler
        raise
    except Exception as e:
        current_app.logger.error(f"Change password error: {str(e)}")
        raise BadRequest("Failed to change password")

@users_bp.route('/<user_id>', methods=['GET'])
@admin_required
def get_user(user_id):
    """Get user by ID (admin only)"""
    try:
        success, result = UserService.get_user(user_id)
        
        if not success:
            raise NotFound(result['error'])
        
        return jsonify(result), 200
        
    except NotFound as e:
        # Re-raise to be handled by error handler
        raise
    except Exception as e:
        current_app.logger.error(f"Get user error: {str(e)}")
        raise BadRequest("Failed to retrieve user")

@users_bp.route('/<user_id>', methods=['PUT'])
@admin_required
def update_user(user_id):
    """Update user (admin only)"""
    try:
        # Validate request data
        data = validate_request(UpdateUserSchema)
        
        # Update user
        success, result = UserService.update_user(
            user_id=user_id,
            update_data=data,
            current_user_id=request.user_id
        )
        
        if not success:
            raise BadRequest(result['error'])
        
        return jsonify(result), 200
        
    except BadRequest as e:
        # Re-raise to be handled by error handler
        raise
    except Exception as e:
        current_app.logger.error(f"Update user error: {str(e)}")
        raise BadRequest("Failed to update user")

@users_bp.route('', methods=['GET'])
@admin_required
def list_users():
    """List users (admin only)"""
    try:
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 10, type=int), 50)  # Limit max per_page
        search = request.args.get('search', None)
        active_only = request.args.get('active_only', False, type=bool)
        
        # Get users
        success, result = UserService.list_users(
            page=page,
            per_page=per_page,
            search=search,
            active_only=active_only
        )
        
        if not success:
            raise BadRequest(result['error'])
        
        return jsonify(result), 200
        
    except BadRequest as e:
        # Re-raise to be handled by error handler
        raise
    except Exception as e:
        current_app.logger.error(f"List users error: {str(e)}")
        raise BadRequest("Failed to retrieve users")