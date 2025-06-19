from datetime import datetime, timedelta
from bson import ObjectId
from flask import current_app, jsonify
import json

from ..models.user import UserModel
from ..models.token import TokenModel
from ..models.role import RoleModel

class AuthService:
    """
    Service for authentication-related operations
    """
    
    @staticmethod
    def register(email, password, first_name, last_name, role=None):
        """
        Register a new user
        
        Args:
            email: User email
            password: User password
            first_name: User first name
            last_name: User last name
            role: Optional role name (defaults to 'user')
            
        Returns:
            tuple: (success, result_data)
        """
        # If role is specified, get role ID
        role_ids = []
        if role:
            role_data = RoleModel.get_role_by_name(role)
            if role_data:
                role_ids = [ObjectId(role_data['_id'])]
        
        # Create user
        success, result = UserModel.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            roles=role_ids,
            email_verified=False
        )
        
        if not success:
            return False, {"error": result}
        
        # If registration is successful, create email verification token
        user_id = result
        token, expires_at = TokenModel.create_token(
            user_id=user_id,
            token_type=TokenModel.TOKEN_TYPE_VERIFY_EMAIL,
            expires_in_hours=24
        )
        
        # In a real application, you would send an email with the verification link
        # For now, we'll just return the token in the response
        return True, {
            "message": "User registered successfully",
            "user_id": user_id,
            "verification_token": token,
            "token_expires_at": expires_at.isoformat()
        }
    
    @staticmethod
    def login(email, password):
        """
        Authenticate a user and generate tokens
        
        Args:
            email: User email
            password: User password
            
        Returns:
            tuple: (success, result_data)
        """
        # Authenticate user
        success, result = UserModel.authenticate_user(email, password)
        
        if not success:
            return False, {"error": result}
        
        user_data = result
        user_id = user_data['_id']
        
        # Generate access token using JWT service
        from .jwt_service import JWTService
        access_token = JWTService.generate_access_token(user_data)
        
        # Generate refresh token
        refresh_token, refresh_expires_at = TokenModel.create_token(
            user_id=user_id,
            token_type=TokenModel.TOKEN_TYPE_REFRESH,
            expires_in_hours=int(current_app.config.get('TOKEN_EXPIRE_HOURS', 24))
        )
        
        # Get user roles information
        roles = RoleModel.get_roles_by_ids(user_data.get('role_ids', []))
        role_names = [role['name'] for role in roles]
        permissions = set()
        for role in roles:
            permissions.update(role.get('permissions', []))
        
        # Return tokens and user information
        return True, {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": int(current_app.config.get('ACCESS_TOKEN_EXPIRE_MINUTES', 15)) * 60,
            "user": {
                "id": user_id,
                "email": user_data['email'],
                "first_name": user_data['first_name'],
                "last_name": user_data['last_name'],
                "roles": role_names,
                "permissions": list(permissions)
            }
        }
    
    @staticmethod
    def refresh_token(refresh_token):
        """
        Refresh access token using a refresh token
        
        Args:
            refresh_token: Refresh token string
            
        Returns:
            tuple: (success, result_data)
        """
        # Validate refresh token
        is_valid, user_id = TokenModel.is_token_valid(
            token=refresh_token,
            token_type=TokenModel.TOKEN_TYPE_REFRESH
        )
        
        if not is_valid:
            return False, {"error": "Invalid or expired refresh token"}
        
        # Get user data
        user_data = UserModel.get_user_by_id(user_id)
        if not user_data:
            return False, {"error": "User not found"}
        
        # Generate new access token
        from .jwt_service import JWTService
        access_token = JWTService.generate_access_token(user_data)
        
        return True, {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": int(current_app.config.get('ACCESS_TOKEN_EXPIRE_MINUTES', 15)) * 60
        }
    
    @staticmethod
    def logout(refresh_token):
        """
        Logout a user by revoking their refresh token
        
        Args:
            refresh_token: Refresh token string
            
        Returns:
            tuple: (success, result_data)
        """
        # Validate refresh token
        is_valid, user_id = TokenModel.is_token_valid(
            token=refresh_token,
            token_type=TokenModel.TOKEN_TYPE_REFRESH
        )
        
        if not is_valid:
            return False, {"error": "Invalid or expired refresh token"}
        
        # Revoke token
        TokenModel.revoke_token(refresh_token)
        
        return True, {"message": "Successfully logged out"}
    
    @staticmethod
    def verify_email(verification_token):
        """
        Verify a user's email using a verification token
        
        Args:
            verification_token: Email verification token
            
        Returns:
            tuple: (success, result_data)
        """
        # Validate verification token
        is_valid, user_id = TokenModel.is_token_valid(
            token=verification_token,
            token_type=TokenModel.TOKEN_TYPE_VERIFY_EMAIL
        )
        
        if not is_valid:
            return False, {"error": "Invalid or expired verification token"}
        
        # Update user's email_verified status
        user_id_obj = ObjectId(user_id)
        UserModel.get_collection().update_one(
            {UserModel.FIELD_ID: user_id_obj},
            {"$set": {
                UserModel.FIELD_EMAIL_VERIFIED: True,
                UserModel.FIELD_UPDATED_AT: datetime.utcnow()
            }}
        )
        
        # Revoke the verification token
        TokenModel.revoke_token(verification_token)
        
        return True, {"message": "Email verified successfully"}
    
    @staticmethod
    def request_password_reset(email):
        """
        Request a password reset for a user
        
        Args:
            email: User's email
            
        Returns:
            tuple: (success, result_data)
        """
        # Find user by email
        user = UserModel.get_collection().find_one({UserModel.FIELD_EMAIL: email.lower()})
        
        if not user:
            # For security reasons, don't indicate if email exists
            return True, {"message": "If your email is registered, you will receive a password reset link"}
        
        # Generate password reset token
        user_id = str(user[UserModel.FIELD_ID])
        token, expires_at = TokenModel.create_token(
            user_id=user_id,
            token_type=TokenModel.TOKEN_TYPE_RESET_PASSWORD,
            expires_in_hours=1  # Short expiration for security
        )
        
        # In a real application, you would send an email with the reset link
        # For now, we'll just return the token in the response
        return True, {
            "message": "If your email is registered, you will receive a password reset link",
            "reset_token": token,  # Remove in production
            "token_expires_at": expires_at.isoformat()  # Remove in production
        }
    
    @staticmethod
    def reset_password(reset_token, new_password):
        """
        Reset a user's password using a reset token
        
        Args:
            reset_token: Password reset token
            new_password: New password
            
        Returns:
            tuple: (success, result_data)
        """
        # Validate reset token
        is_valid, user_id = TokenModel.is_token_valid(
            token=reset_token,
            token_type=TokenModel.TOKEN_TYPE_RESET_PASSWORD
        )
        
        if not is_valid:
            return False, {"error": "Invalid or expired reset token"}
        
        # Validate new password
        if not UserModel.validate_password(new_password):
            return False, {"error": "Password must be at least 8 characters and include uppercase, lowercase, number, and special character"}
        
        # Update user's password
        user_id_obj = ObjectId(user_id)
        password_hash = UserModel.hash_password(new_password)
        
        UserModel.get_collection().update_one(
            {UserModel.FIELD_ID: user_id_obj},
            {"$set": {
                UserModel.FIELD_PASSWORD: password_hash,
                UserModel.FIELD_UPDATED_AT: datetime.utcnow()
            }}
        )
        
        # Revoke all refresh tokens for this user
        TokenModel.revoke_all_user_tokens(user_id, TokenModel.TOKEN_TYPE_REFRESH)
        
        # Revoke the reset token
        TokenModel.revoke_token(reset_token)
        
        return True, {"message": "Password reset successfully"}
    
    @staticmethod
    def validate_token(token):
        """
        Validate an access token
        
        Args:
            token: JWT access token
            
        Returns:
            tuple: (success, result_data)
        """
        from .jwt_service import JWTService
        payload = JWTService.validate_access_token(token)
        
        if not payload:
            return False, {"error": "Invalid or expired token"}
        
        user_id = payload.get('sub')
        
        # Get user data
        user_data = UserModel.get_user_by_id(user_id)
        if not user_data:
            return False, {"error": "User not found"}
        
        # Get user roles information
        roles = RoleModel.get_roles_by_ids(user_data.get('role_ids', []))
        role_names = [role['name'] for role in roles]
        permissions = set()
        for role in roles:
            permissions.update(role.get('permissions', []))
        
        return True, {
            "user_id": user_id,
            "email": user_data['email'],
            "roles": role_names,
            "permissions": list(permissions),
            "exp": payload.get('exp')
        }