from datetime import datetime
from bson import ObjectId
from flask import current_app
from ..models.user import UserModel
from ..models.role import RoleModel
from ..models.token import TokenModel

class UserService:
    """
    Service for user management operations
    """
    
    @staticmethod
    def get_user(user_id):
        """
        Get user by ID
        
        Args:
            user_id: User ID
            
        Returns:
            tuple: (success, user_data or error_message)
        """
        user_data = UserModel.get_user_by_id(user_id)
        
        if not user_data:
            return False, {"error": "User not found"}
        
        # Get user roles information
        roles = RoleModel.get_roles_by_ids(user_data.get('role_ids', []))
        role_names = [role['name'] for role in roles]
        permissions = set()
        for role in roles:
            permissions.update(role.get('permissions', []))
        
        # Add role information to user data
        user_data['roles'] = role_names
        user_data['permissions'] = list(permissions)
        
        return True, user_data
    
    @staticmethod
    def update_user(user_id, update_data, current_user_id=None):
        """
        Update user profile
        
        Args:
            user_id: ID of the user to update
            update_data: Dictionary of fields to update
            current_user_id: ID of the user making the request (for authorization)
            
        Returns:
            tuple: (success, result_data)
        """
        try:
            user_id_obj = ObjectId(user_id)
        except:
            return False, {"error": "Invalid user ID"}
        
        # Check if user exists
        user = UserModel.get_collection().find_one({UserModel.FIELD_ID: user_id_obj})
        if not user:
            return False, {"error": "User not found"}
        
        # Authorization check: only allow users to update their own profile
        # unless they have admin role
        if current_user_id != user_id:
            # Check if current user is admin
            current_user = UserModel.get_user_by_id(current_user_id)
            if current_user:
                role_ids = current_user.get('role_ids', [])
                is_admin = RoleModel.has_permission(role_ids, RoleModel.PERMISSION_UPDATE)
                if not is_admin:
                    return False, {"error": "Not authorized to update this user"}
            else:
                return False, {"error": "Not authorized to update this user"}
        
        # Fields that can be updated
        allowed_fields = {
            'first_name': UserModel.FIELD_FIRST_NAME,
            'last_name': UserModel.FIELD_LAST_NAME,
            'active': UserModel.FIELD_ACTIVE
        }
        
        # Prepare update data
        update_dict = {}
        for key, value in update_data.items():
            if key in allowed_fields:
                update_dict[allowed_fields[key]] = value
        
        # Add updated timestamp
        update_dict[UserModel.FIELD_UPDATED_AT] = datetime.utcnow()
        
        if not update_dict:
            return False, {"error": "No valid fields to update"}
        
        # Update user
        result = UserModel.get_collection().update_one(
            {UserModel.FIELD_ID: user_id_obj},
            {"$set": update_dict}
        )
        
        if result.modified_count > 0:
            return True, {"message": "User updated successfully"}
        else:
            return False, {"error": "User not updated"}
    
    @staticmethod
    def change_password(user_id, current_password, new_password, current_user_id=None):
        """
        Change a user's password
        
        Args:
            user_id: User ID
            current_password: Current password
            new_password: New password
            current_user_id: ID of the user making the request (for authorization)
            
        Returns:
            tuple: (success, result_data)
        """
        try:
            user_id_obj = ObjectId(user_id)
        except:
            return False, {"error": "Invalid user ID"}
        
        # Check if user exists
        user = UserModel.get_collection().find_one({UserModel.FIELD_ID: user_id_obj})
        if not user:
            return False, {"error": "User not found"}
        
        # Authorization check: only allow users to change their own password
        # unless they have admin role
        if current_user_id != user_id:
            # Check if current user is admin
            current_user = UserModel.get_user_by_id(current_user_id)
            if current_user:
                role_ids = current_user.get('role_ids', [])
                is_admin = RoleModel.has_permission(role_ids, RoleModel.PERMISSION_UPDATE)
                if not is_admin:
                    return False, {"error": "Not authorized to change password for this user"}
            else:
                return False, {"error": "Not authorized to change password for this user"}
        
        # Verify current password (not required for admins)
        if current_user_id == user_id:
            if not UserModel.verify_password(user[UserModel.FIELD_PASSWORD], current_password):
                return False, {"error": "Current password is incorrect"}
        
        # Validate new password
        if not UserModel.validate_password(new_password):
            return False, {"error": "Password must be at least 8 characters and include uppercase, lowercase, number, and special character"}
        
        # Update password
        password_hash = UserModel.hash_password(new_password)
        
        result = UserModel.get_collection().update_one(
            {UserModel.FIELD_ID: user_id_obj},
            {"$set": {
                UserModel.FIELD_PASSWORD: password_hash,
                UserModel.FIELD_UPDATED_AT: datetime.utcnow()
            }}
        )
        
        if result.modified_count > 0:
            # Revoke all refresh tokens for this user
            TokenModel.revoke_all_user_tokens(user_id, TokenModel.TOKEN_TYPE_REFRESH)
            return True, {"message": "Password changed successfully"}
        else:
            return False, {"error": "Password not updated"}
    
    @staticmethod
    def list_users(page=1, per_page=10, search=None, active_only=False):
        """
        Get a paginated list of users
        
        Args:
            page: Page number (starting from 1)
            per_page: Number of users per page
            search: Optional search term for email, first_name, or last_name
            active_only: Whether to return only active users
            
        Returns:
            tuple: (success, result_data)
        """
        # Build query
        query = {}
        if active_only:
            query[UserModel.FIELD_ACTIVE] = True
        
        if search:
            search_regex = {"$regex": search, "$options": "i"}
            query["$or"] = [
                {UserModel.FIELD_EMAIL: search_regex},
                {UserModel.FIELD_FIRST_NAME: search_regex},
                {UserModel.FIELD_LAST_NAME: search_regex}
            ]
        
        # Execute query with pagination
        skip = (page - 1) * per_page
        cursor = UserModel.get_collection().find(
            query,
            {UserModel.FIELD_PASSWORD: 0}  # Exclude password
        ).sort([(UserModel.FIELD_CREATED_AT, -1)]).skip(skip).limit(per_page)
        
        # Get total count for pagination
        total_count = UserModel.get_collection().count_documents(query)
        
        # Process results
        users = []
        for user in cursor:
            # Transform ObjectId to string
            user[UserModel.FIELD_ID] = str(user[UserModel.FIELD_ID])
            user['role_ids'] = [str(role_id) for role_id in user.get('role_ids', [])]
            users.append(user)
        
        return True, {
            "users": users,
            "pagination": {
                "total": total_count,
                "page": page,
                "per_page": per_page,
                "pages": (total_count + per_page - 1) // per_page
            }
        }