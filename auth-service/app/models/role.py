from datetime import datetime
from pymongo import ASCENDING
from bson import ObjectId
from flask import current_app

class RoleModel:
    """
    Role model that represents the roles collection in MongoDB
    """
    
    # Collection fields
    COLLECTION_NAME = 'roles'
    FIELD_ID = '_id'
    FIELD_NAME = 'name'
    FIELD_DESCRIPTION = 'description'
    FIELD_PERMISSIONS = 'permissions'
    FIELD_CREATED_AT = 'created_at'
    FIELD_UPDATED_AT = 'updated_at'
    
    # Define standard roles
    ROLE_ADMIN = 'admin'
    ROLE_USER = 'user'
    
    # Define standard permissions
    PERMISSION_READ = 'read'
    PERMISSION_CREATE = 'create'
    PERMISSION_UPDATE = 'update'
    PERMISSION_DELETE = 'delete'
    
    @classmethod
    def get_collection(cls):
        """Get the MongoDB collection for roles"""
        from flask import current_app
        return current_app.db[cls.COLLECTION_NAME]
    
    @classmethod
    def create_indexes(cls):
        """Create necessary indexes for the collection"""
        collection = cls.get_collection()
        collection.create_index([(cls.FIELD_NAME, ASCENDING)], unique=True)
        current_app.logger.info(f"Indexes created for {cls.COLLECTION_NAME} collection")
    
    @classmethod
    def create_default_roles(cls):
        """Create default roles if they don't exist"""
        now = datetime.utcnow()
        
        # Admin role with all permissions
        admin_role = {
            cls.FIELD_NAME: cls.ROLE_ADMIN,
            cls.FIELD_DESCRIPTION: "Administrator with all permissions",
            cls.FIELD_PERMISSIONS: [
                cls.PERMISSION_READ,
                cls.PERMISSION_CREATE,
                cls.PERMISSION_UPDATE,
                cls.PERMISSION_DELETE
            ],
            cls.FIELD_CREATED_AT: now,
            cls.FIELD_UPDATED_AT: now
        }
        
        # Regular user with read and create permissions
        user_role = {
            cls.FIELD_NAME: cls.ROLE_USER,
            cls.FIELD_DESCRIPTION: "Regular user with limited permissions",
            cls.FIELD_PERMISSIONS: [
                cls.PERMISSION_READ,
                cls.PERMISSION_CREATE
            ],
            cls.FIELD_CREATED_AT: now,
            cls.FIELD_UPDATED_AT: now
        }
        
        # Insert roles if they don't exist
        for role in [admin_role, user_role]:
            cls.get_collection().update_one(
                {cls.FIELD_NAME: role[cls.FIELD_NAME]},
                {"$setOnInsert": role},
                upsert=True
            )
        
        current_app.logger.info("Default roles created")
    
    @classmethod
    def get_role_by_name(cls, role_name):
        """
        Get role by name
        
        Args:
            role_name: Name of the role
            
        Returns:
            dict: Role data or None
        """
        role = cls.get_collection().find_one({cls.FIELD_NAME: role_name})
        
        if role:
            # Transform ObjectId to string for serialization
            role[cls.FIELD_ID] = str(role[cls.FIELD_ID])
        
        return role
    
    @classmethod
    def get_roles_by_ids(cls, role_ids):
        """
        Get roles by list of IDs
        
        Args:
            role_ids: List of role IDs
            
        Returns:
            list: List of role data
        """
        role_ids_obj = []
        for role_id in role_ids:
            try:
                role_ids_obj.append(ObjectId(role_id))
            except:
                pass
                
        roles = list(cls.get_collection().find({cls.FIELD_ID: {"$in": role_ids_obj}}))
        
        # Transform ObjectId to string for serialization
        for role in roles:
            role[cls.FIELD_ID] = str(role[cls.FIELD_ID])
            
        return roles
    
    @classmethod
    def has_permission(cls, role_ids, permission):
        """
        Check if roles have a specific permission
        
        Args:
            role_ids: List of role IDs
            permission: Permission to check
            
        Returns:
            bool: True if roles have permission, False otherwise
        """
        roles = cls.get_roles_by_ids(role_ids)
        for role in roles:
            if permission in role.get(cls.FIELD_PERMISSIONS, []):
                return True
        return False