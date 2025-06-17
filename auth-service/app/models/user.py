from datetime import datetime
from pymongo import MongoEngine, ASCENDING
from bson import ObjectId
from flask import current_app
import bcrypt
import re

class UserModel:
    """
    User model that represents the users collection in MongoDB
    """
    
    # Collection fields
    COLLECTION_NAME = 'users'
    FIELD_ID = '_id'
    FIELD_EMAIL = 'email'
    FIELD_PASSWORD = 'password_hash'
    FIELD_FIRST_NAME = 'first_name'
    FIELD_LAST_NAME = 'last_name'
    FIELD_ROLE_IDS = 'role_ids'
    FIELD_ACTIVE = 'active'
    FIELD_EMAIL_VERIFIED = 'email_verified'
    FIELD_CREATED_AT = 'created_at'
    FIELD_UPDATED_AT = 'updated_at'
    FIELD_LAST_LOGIN = 'last_login'
    
    @classmethod
    def get_collection(cls):
        """Get the MongoDB collection for users"""
        from flask import current_app
        return current_app.mongo.db[cls.COLLECTION_NAME]
    
    @classmethod
    def create_indexes(cls):
        """Create necessary indexes for the collection"""
        collection = cls.get_collection()
        collection.create_index([(cls.FIELD_EMAIL, ASCENDING)], unique=True)
        current_app.logger.info(f"Indexes created for {cls.COLLECTION_NAME} collection")
    
    @classmethod
    def validate_email(cls, email):
        """Validate email format"""
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(email_regex, email) is not None
    
    @classmethod
    def validate_password(cls, password):
        """
        Validate password strength
        Password must be at least 8 characters and include uppercase, 
        lowercase, number, and special character
        """
        if len(password) < 8:
            return False
            
        checks = [
            re.search(r'[A-Z]', password),  # uppercase
            re.search(r'[a-z]', password),  # lowercase
            re.search(r'[0-9]', password),  # number
            re.search(r'[!@#$%^&*(),.?":{}|<>]', password)  # special char
        ]
        
        return all(checks)
    
    @classmethod
    def hash_password(cls, password):
        """Hash a password using bcrypt"""
        if isinstance(password, str):
            password = password.encode('utf-8')
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password, salt).decode('utf-8')
    
    @classmethod
    def verify_password(cls, stored_hash, password):
        """Verify a password against a stored hash"""
        if isinstance(password, str):
            password = password.encode('utf-8')
        if isinstance(stored_hash, str):
            stored_hash = stored_hash.encode('utf-8')
        try:
            return bcrypt.checkpw(password, stored_hash)
        except Exception as e:
            current_app.logger.error(f"Password verification error: {str(e)}")
            return False
    
    @classmethod
    def create_user(cls, email, password, first_name, last_name, roles=None, email_verified=False):
        """
        Create a new user
        
        Args:
            email: User email
            password: User password
            first_name: User first name
            last_name: User last name
            roles: List of role IDs
            email_verified: Whether email is verified
            
        Returns:
            tuple: (success, user_id or error_message)
        """
        # Validate email
        if not cls.validate_email(email):
            return False, "Invalid email format"
            
        # Validate password
        if not cls.validate_password(password):
            return False, "Password must be at least 8 characters and include uppercase, lowercase, number, and special character"
        
        # Check if email exists
        if cls.get_collection().find_one({cls.FIELD_EMAIL: email}):
            return False, "Email already exists"
            
        # Hash password
        password_hash = cls.hash_password(password)
        
        # Get default role if roles not specified
        if not roles:
            default_role = current_app.mongo.db['roles'].find_one({"name": "user"})
            role_ids = [default_role["_id"]] if default_role else []
        else:
            role_ids = [role if isinstance(role, ObjectId) else ObjectId(role) for role in roles]
            
        # Create user
        now = datetime.utcnow()
        user = {
            cls.FIELD_EMAIL: email.lower(),
            cls.FIELD_PASSWORD: password_hash,
            cls.FIELD_FIRST_NAME: first_name,
            cls.FIELD_LAST_NAME: last_name,
            cls.FIELD_ROLE_IDS: role_ids,
            cls.FIELD_ACTIVE: True,
            cls.FIELD_EMAIL_VERIFIED: email_verified,
            cls.FIELD_CREATED_AT: now,
            cls.FIELD_UPDATED_AT: now,
            cls.FIELD_LAST_LOGIN: None
        }
        
        try:
            result = cls.get_collection().insert_one(user)
            return True, str(result.inserted_id)
        except Exception as e:
            current_app.logger.error(f"Error creating user: {str(e)}")
            return False, str(e)
    
    @classmethod
    def authenticate_user(cls, email, password):
        """
        Authenticate a user with email and password
        
        Args:
            email: User email
            password: User password
            
        Returns:
            tuple: (success, user_data or error_message)
        """
        user = cls.get_collection().find_one({cls.FIELD_EMAIL: email.lower()})
        if not user:
            return False, "Invalid email or password"
            
        if not user[cls.FIELD_ACTIVE]:
            return False, "Account is deactivated"
            
        if not cls.verify_password(user[cls.FIELD_PASSWORD], password):
            return False, "Invalid email or password"
            
        # Update last login
        cls.get_collection().update_one(
            {cls.FIELD_ID: user[cls.FIELD_ID]},
            {"$set": {cls.FIELD_LAST_LOGIN: datetime.utcnow()}}
        )
        
        # Transform ObjectId to string for serialization
        user[cls.FIELD_ID] = str(user[cls.FIELD_ID])
        user[cls.FIELD_ROLE_IDS] = [str(role_id) for role_id in user[cls.FIELD_ROLE_IDS]]
        
        # Remove password hash from response
        del user[cls.FIELD_PASSWORD]
        
        return True, user
    
    @classmethod
    def get_user_by_id(cls, user_id):
        """
        Get user by ID
        
        Args:
            user_id: User ID
            
        Returns:
            dict: User data or None
        """
        try:
            user_id_obj = ObjectId(user_id)
        except:
            return None
            
        user = cls.get_collection().find_one({cls.FIELD_ID: user_id_obj})
        if not user:
            return None
            
        # Transform ObjectId to string for serialization
        user[cls.FIELD_ID] = str(user[cls.FIELD_ID])
        user[cls.FIELD_ROLE_IDS] = [str(role_id) for role_id in user[cls.FIELD_ROLE_IDS]]
        
        # Remove password hash from response
        del user[cls.FIELD_PASSWORD]
        
        return user