import requests
from flask import request, g, jsonify, current_app
from functools import wraps
import logging

def get_user_from_token():
    """
    Validate the JWT token from Authorization header with the auth service
    
    Returns:
        dict: User information if token is valid, None otherwise
    """
    # Check if we've already validated in this request
    if hasattr(g, 'current_user'):
        return g.current_user
        
    # Get token from Authorization header
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        current_app.logger.warning("No or invalid Authorization header")
        return None
    
    token = auth_header.split(' ')[1]
    
    # Call auth service to validate token
    auth_service_url = current_app.config.get('AUTH_SERVICE_URL', 'http://auth-service:5002')
    current_app.logger.info(f"Calling auth service at: {auth_service_url}/auth/validate")
    
    try:
        response = requests.post(
            f"{auth_service_url}/auth/validate",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5  # 5 second timeout for auth service
        )
        current_app.logger.info(f"Auth service response: {response.status_code} {response.text}")
        
        if response.status_code == 200:
            user_info = response.json()
            
            # Store in Flask g object for this request
            g.current_user = user_info
            return user_info
        else:
            current_app.logger.warning(
                f"Token validation failed: Status {response.status_code}, Response: {response.text}"
            )
            return None
            
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Error communicating with auth service: {str(e)}")
        return None

def auth_required(f):
    """Decorator to require authentication for an endpoint"""
    @wraps(f)
    def decorated(*args, **kwargs):
        user_info = get_user_from_token()
        
        if not user_info:
            return jsonify({"error": "Authentication required"}), 401
        
        # Add the user_id to the request for convenience
        request.user_id = user_info.get('user_id')
        return f(*args, **kwargs)
    
    return decorated

def admin_required(f):
    """Decorator to require admin role for an endpoint"""
    @wraps(f)
    def decorated(*args, **kwargs):
        user_info = get_user_from_token()
        
        if not user_info:
            return jsonify({"error": "Authentication required"}), 401
            
        if 'admin' not in user_info.get('roles', []):
            return jsonify({"error": "Admin access required"}), 403
        
        # Add the user_id to the request for convenience
        request.user_id = user_info.get('user_id')
        return f(*args, **kwargs)
    
    return decorated

def optional_auth(f):
    """
    Decorator to handle optional authentication
    If token is present and valid, user info will be available
    If not, the request will continue without authentication
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        user_info = get_user_from_token()
        
        # Add the user_id to the request (could be None)
        request.user_id = user_info.get('user_id') if user_info else None
        return f(*args, **kwargs)
    
    return decorated