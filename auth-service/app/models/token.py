from datetime import datetime, timedelta
from pymongo import ASCENDING, DESCENDING
from bson import ObjectId
from flask import current_app
import uuid

class TokenModel:
    """
    Token model that represents the tokens collection in MongoDB
    """
    
    # Collection fields
    COLLECTION_NAME = 'tokens'
    FIELD_ID = '_id'
    FIELD_USER_ID = 'user_id'
    FIELD_TOKEN = 'token'
    FIELD_TYPE = 'type'
    FIELD_EXPIRES_AT = 'expires_at'
    FIELD_CREATED_AT = 'created_at'
    FIELD_REVOKED = 'revoked'
    FIELD_REVOKED_AT = 'revoked_at'
    
    # Token types
    TOKEN_TYPE_REFRESH = 'refresh'
    TOKEN_TYPE_RESET_PASSWORD = 'reset_password'
    TOKEN_TYPE_VERIFY_EMAIL = 'verify_email'
    
    @classmethod
    def get_collection(cls):
        """Get the MongoDB collection for tokens"""
        from flask import current_app
        return current_app.mongo.db[cls.COLLECTION_NAME]
    
    @classmethod
    def create_indexes(cls):
        """Create necessary indexes for the collection"""
        collection = cls.get_collection()
        collection.create_index([(cls.FIELD_TOKEN, ASCENDING)], unique=True)
        collection.create_index([(cls.FIELD_USER_ID, ASCENDING), (cls.FIELD_TYPE, ASCENDING)])
        collection.create_index([(cls.FIELD_EXPIRES_AT, ASCENDING)], expireAfterSeconds=0)
        current_app.logger.info(f"Indexes created for {cls.COLLECTION_NAME} collection")
    
    @classmethod
    def create_token(cls, user_id, token_type, expires_in_hours=24):
        """
        Create a new token
        
        Args:
            user_id: User ID
            token_type: Type of token
            expires_in_hours: Token expiration in hours
            
        Returns:
            tuple: (token, expires_at)
        """
        # Generate a secure token
        token = str(uuid.uuid4())
        
        now = datetime.utcnow()
        expires_at = now + timedelta(hours=expires_in_hours)
        
        # Store token in database
        token_data = {
            cls.FIELD_USER_ID: ObjectId(user_id) if not isinstance(user_id, ObjectId) else user_id,
            cls.FIELD_TOKEN: token,
            cls.FIELD_TYPE: token_type,
            cls.FIELD_EXPIRES_AT: expires_at,
            cls.FIELD_CREATED_AT: now,
            cls.FIELD_REVOKED: False,
            cls.FIELD_REVOKED_AT: None
        }
        
        cls.get_collection().insert_one(token_data)
        
        return token, expires_at
    
    @classmethod
    def get_token(cls, token, token_type=None):
        """
        Get token data
        
        Args:
            token: Token string
            token_type: Optional token type filter
            
        Returns:
            dict: Token data or None
        """
        query = {cls.FIELD_TOKEN: token}
        if token_type:
            query[cls.FIELD_TYPE] = token_type
        
        token_data = cls.get_collection().find_one(query)
        
        if token_data:
            # Transform ObjectId to string for serialization
            token_data[cls.FIELD_ID] = str(token_data[cls.FIELD_ID])
            token_data[cls.FIELD_USER_ID] = str(token_data[cls.FIELD_USER_ID])
        
        return token_data
    
    @classmethod
    def is_token_valid(cls, token, token_type=None):
        """
        Check if token is valid
        
        Args:
            token: Token string
            token_type: Optional token type filter
            
        Returns:
            tuple: (is_valid, user_id or None)
        """
        token_data = cls.get_token(token, token_type)
        
        if not token_data:
            return False, None
        
        # Check if token is expired
        now = datetime.utcnow()
        if token_data[cls.FIELD_EXPIRES_AT] < now:
            return False, None
        
        # Check if token is revoked
        if token_data[cls.FIELD_REVOKED]:
            return False, None
        
        return True, token_data[cls.FIELD_USER_ID]
    
    @classmethod
    def revoke_token(cls, token):
        """
        Revoke a token
        
        Args:
            token: Token string
            
        Returns:
            bool: Success status
        """
        result = cls.get_collection().update_one(
            {cls.FIELD_TOKEN: token},
            {"$set": {
                cls.FIELD_REVOKED: True,
                cls.FIELD_REVOKED_AT: datetime.utcnow()
            }}
        )
        
        return result.modified_count > 0
    
    @classmethod
    def revoke_all_user_tokens(cls, user_id, token_type=None):
        """
        Revoke all tokens for a user
        
        Args:
            user_id: User ID
            token_type: Optional token type filter
            
        Returns:
            int: Number of tokens revoked
        """
        query = {
            cls.FIELD_USER_ID: ObjectId(user_id) if not isinstance(user_id, ObjectId) else user_id,
            cls.FIELD_REVOKED: False
        }
        
        if token_type:
            query[cls.FIELD_TYPE] = token_type
        
        result = cls.get_collection().update_many(
            query,
            {"$set": {
                cls.FIELD_REVOKED: True,
                cls.FIELD_REVOKED_AT: datetime.utcnow()
            }}
        )
        
        return result.modified_count
    
    @classmethod
    def cleanup_expired_tokens(cls):
        """
        Delete expired tokens
        The MongoDB TTL index should handle this automatically,
        but this method can be used for manual cleanup
        
        Returns:
            int: Number of tokens deleted
        """
        now = datetime.utcnow()
        result = cls.get_collection().delete_many({
            cls.FIELD_EXPIRES_AT: {"$lt": now}
        })
        
        return result.deleted_count