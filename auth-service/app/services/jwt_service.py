from datetime import datetime, timedelta
import jwt
from flask import current_app
import time

class JWTService:
    """
    Service for JWT token generation and validation
    """
    
    @staticmethod
    def _get_secret_key():
        """Get the JWT secret key from app config"""
        return current_app.config.get('JWT_SECRET_KEY')
    
    @staticmethod
    def generate_access_token(user_data):
        """
        Generate a JWT access token
        
        Args:
            user_data: User data dictionary
            
        Returns:
            str: JWT access token
        """
        now = datetime.utcnow()
        expires_minutes = int(current_app.config.get('ACCESS_TOKEN_EXPIRE_MINUTES', 15))
        expires_at = now + timedelta(minutes=expires_minutes)
        
        # Get user roles
        role_ids = user_data.get('role_ids', [])
        
        # Get role names
        from ..models.role import RoleModel
        roles = RoleModel.get_roles_by_ids(role_ids)
        role_names = [role['name'] for role in roles]
        
        # Gather permissions
        permissions = []
        for role in roles:
            permissions.extend(role.get('permissions', []))
        permissions = list(set(permissions))  # Remove duplicates
        
        # Create payload
        payload = {
            'sub': user_data['_id'],  # subject (user ID)
            'iat': int(time.time()),  # issued at
            'exp': int(time.mktime(expires_at.timetuple())),  # expiration time
            'email': user_data['email'],
            'name': f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}".strip(),
            'roles': role_names,
            'permissions': permissions
        }
        
        # Generate token
        token = jwt.encode(
            payload,
            JWTService._get_secret_key(),
            algorithm='HS256'
        )
        
        return token
    
    @staticmethod
    def validate_access_token(token):
        """
        Validate a JWT access token
        
        Args:
            token: JWT token string
            
        Returns:
            dict: Token payload if valid, None otherwise
        """
        try:
            payload = jwt.decode(
                token,
                JWTService._get_secret_key(),
                algorithms=['HS256']
            )
            return payload
        except jwt.ExpiredSignatureError:
            current_app.logger.warning("Expired JWT token")
            return None
        except jwt.InvalidTokenError as e:
            current_app.logger.warning(f"Invalid JWT token: {str(e)}")
            return None
    
    @staticmethod
    def decode_token_without_verification(token):
        """
        Decode a JWT token without verifying signature (for debugging)
        
        Args:
            token: JWT token string
            
        Returns:
            dict: Token payload
        """
        try:
            # Skip verification for debugging purposes only
            payload = jwt.decode(
                token, 
                options={"verify_signature": False}
            )
            return payload
        except Exception as e:
            current_app.logger.error(f"Token decode error: {str(e)}")
            return None
    
    @staticmethod
    def has_permission(token, required_permission):
        """
        Check if token has the required permission
        
        Args:
            token: JWT token string
            required_permission: Permission to check
            
        Returns:
            bool: True if token has permission, False otherwise
        """
        payload = JWTService.validate_access_token(token)
        if not payload:
            return False
        
        permissions = payload.get('permissions', [])
        return required_permission in permissions
    
    @staticmethod
    def has_role(token, required_role):
        """
        Check if token has the required role
        
        Args:
            token: JWT token string
            required_role: Role to check
            
        Returns:
            bool: True if token has role, False otherwise
        """
        payload = JWTService.validate_access_token(token)
        if not payload:
            return False
        
        roles = payload.get('roles', [])
        return required_role in roles