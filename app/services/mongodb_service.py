import datetime
import hashlib
import json
import os
from bson.objectid import ObjectId
from flask import current_app

class ImageMetadataService:
    def __init__(self, db):
        self.db = db
        self.images_collection = self.db.images
        self.versions_collection = self.db.image_versions
        
        # Create necessary indexes for better performance
        self._create_indexes()
    
    def _create_indexes(self):
        """Create indexes for efficient lookups."""
        # Indexes for original images
        self.images_collection.create_index("file_path", unique=True)
        self.images_collection.create_index("image_hash")
        self.images_collection.create_index("upload_date")
        self.images_collection.create_index("source_url")  # Add index for source_url
        self.images_collection.create_index("user_id")  # Add index for user lookups
        
        # Indexes for versions
        self.versions_collection.create_index("original_image_id")
        self.versions_collection.create_index([
            ("original_image_id", 1),
            ("operation_param_hash", 1)
        ], unique=True)
        self.versions_collection.create_index("created_date")
        self.versions_collection.create_index("version_number")
        self.versions_collection.create_index("user_id")  # Add index for user lookups
    
    # Original image methods
    
    def store_original_image(self, filename, file_path, original_filename, image_hash, 
                           source_type="upload", source_url=None, user_id=None):
        """
        Store metadata for an original uploaded image.
        
        Args:
            filename: Current filename in the storage
            file_path: Full path to the stored file
            original_filename: Original name of the uploaded file
            image_hash: Hash of the image content
            source_type: How the image was obtained ('upload' or 'url')
            source_url: Source URL if applicable
            user_id: ID of the user who uploaded the image
            
        Returns:
            str: MongoDB document ID
        """
        # Check if image already exists by file_path
        existing_image = self.images_collection.find_one({"file_path": file_path})
        if existing_image:
            return str(existing_image["_id"])
            
        # Create new image document
        image_data = {
            "filename": filename,
            "file_path": file_path,
            "original_filename": original_filename,
            "image_hash": image_hash,
            "source_type": source_type,
            "source_url": source_url,
            "upload_date": datetime.datetime.utcnow(),
            "version_count": 0,
            "user_id": user_id  # Store user ID in metadata
        }
        
        result = self.images_collection.insert_one(image_data)
        return str(result.inserted_id)
    
    def find_image_by_path(self, file_path):
        """Find an image by its file path."""
        return self.images_collection.find_one({"file_path": file_path})
    
    def find_image_by_hash(self, image_hash):
        """Find an image by its hash."""
        return self.images_collection.find_one({"image_hash": image_hash})
    
    def get_image_by_id(self, image_id):
        """Get an image by its ID."""
        try:
            return self.images_collection.find_one({"_id": ObjectId(image_id)})
        except Exception:
            return None
    
    def update_version_count(self, image_id, increment=1):
        """Update the version count for an original image."""
        try:
            self.images_collection.update_one(
                {"_id": ObjectId(image_id)},
                {"$inc": {"version_count": increment}}
            )
            return True
        except Exception:
            return False
    
    def get_recent_uploads(self, limit=10, user_id=None):
        """
        Get recent image uploads.
        
        Args:
            limit: Maximum number of records to return
            user_id: Optional user ID to filter results by user
            
        Returns:
            list: Recent upload records
        """
        query = {}
        if user_id:
            query["user_id"] = user_id
            
        return list(self.images_collection.find(query).sort("upload_date", -1).limit(limit))
    
    # Version methods
    
    def generate_operation_param_hash(self, operation_params):
        """Generate a hash for operation parameters."""
        params_str = json.dumps(operation_params, sort_keys=True)
        return hashlib.sha256(params_str.encode()).hexdigest()
    
    def get_next_version_number(self, image_id):
        """Get the next available version number for an image."""
        highest_version = self.versions_collection.find_one(
            {"original_image_id": image_id},
            sort=[("version_number", -1)]
        )
        
        if highest_version:
            return highest_version["version_number"] + 1
        return 1
    
    def create_image_version(self, original_image_id, processed_path, operation_params, image_hash, user_id=None):
        """
        Create a new version of an image.
        
        Args:
            original_image_id: ID of the original image
            processed_path: Path to the processed image
            operation_params: Parameters used for processing
            image_hash: Hash of the processed image content
            user_id: ID of the user who created this version
            
        Returns:
            tuple: (version_id, processed_path, is_cached)
        """
        # Generate operation parameter hash
        operation_param_hash = self.generate_operation_param_hash(operation_params)
        
        # Check if this version already exists
        existing_version = self.versions_collection.find_one({
            "original_image_id": original_image_id,
            "operation_param_hash": operation_param_hash
        })
        
        if existing_version:
            return str(existing_version["_id"]), existing_version["processed_path"], True
        
        # Get next version number
        version_number = self.get_next_version_number(original_image_id)
        
        # Create new version document
        version_data = {
            "original_image_id": original_image_id,
            "processed_path": processed_path,
            "created_date": datetime.datetime.utcnow(),
            "version_number": version_number,
            "image_hash": image_hash,
            "operation_param_hash": operation_param_hash,
            "operation_params": operation_params,  # Store the actual parameters for reference
            "user_id": user_id  # Store user ID with the version
        }
        
        result = self.versions_collection.insert_one(version_data)
        
        # Update the version count on the original image
        self.update_version_count(original_image_id)
        
        return str(result.inserted_id), processed_path, False  # False indicates new version
    
    def find_version_by_params(self, original_image_id, operation_params):
        """Find a version by original image ID and operation parameters."""
        operation_param_hash = self.generate_operation_param_hash(operation_params)
        
        return self.versions_collection.find_one({
            "original_image_id": original_image_id,
            "operation_param_hash": operation_param_hash
        })
    
    def get_image_versions(self, image_id, user_id=None):
        """
        Get all versions of an image.
        
        Args:
            image_id: ID of the original image
            user_id: Optional user ID to filter versions by user
            
        Returns:
            list: All matching versions of the image
        """
        try:
            query = {"original_image_id": image_id}
            if user_id:
                query["user_id"] = user_id
                
            versions = self.versions_collection.find(query).sort("version_number", 1)
            
            return list(versions)
        except Exception:
            return []
    
    def get_version_by_id(self, version_id):
        """Get a specific version by its ID."""
        try:
            return self.versions_collection.find_one({"_id": ObjectId(version_id)})
        except Exception:
            return None
    
    def get_version_by_number(self, image_id, version_number):
        """Get a specific version by its number."""
        return self.versions_collection.find_one({
            "original_image_id": image_id,
            "version_number": version_number
        })
    
    def delete_version(self, version_id):
        """Delete a version."""
        try:
            version = self.versions_collection.find_one_and_delete({"_id": ObjectId(version_id)})
            if version:
                # Decrement version count on original image
                self.update_version_count(version["original_image_id"], -1)
                return True
            return False
        except Exception:
            return False
    
    # Combined operations
    
    def get_or_create_version(self, original_image_id, operation_params, processed_path, image_hash, user_id=None):
        """
        Get an existing version or create a new one.
        
        Args:
            original_image_id: ID of the original image
            operation_params: Parameters used for processing
            processed_path: Path to the processed image
            image_hash: Hash of the processed image content
            user_id: ID of the user performing this operation
            
        Returns:
            tuple: (version_id, processed_path, is_cached)
        """
        # Check if version exists
        existing_version = self.find_version_by_params(original_image_id, operation_params)
        
        if existing_version:
            return str(existing_version["_id"]), existing_version["processed_path"], True
        
        # Create new version
        return self.create_image_version(
            original_image_id, 
            processed_path, 
            operation_params, 
            image_hash,
            user_id  # Pass the user ID to create_image_version
        )
    
    def get_version_stats(self, image_id):
        """Get statistics about versions of an image."""
        try:
            original_image = self.get_image_by_id(image_id)
            if not original_image:
                return None
                
            versions = self.get_image_versions(image_id)
            
            return {
                "original_filename": original_image["original_filename"],
                "upload_date": original_image["upload_date"],
                "source_type": original_image["source_type"],
                "user_id": original_image.get("user_id"),  # Include user who uploaded the original
                "total_versions": len(versions),
                "latest_version": max([v["version_number"] for v in versions]) if versions else 0,
                "latest_processing_date": max([v["created_date"] for v in versions]) if versions else None
            }
        except Exception:
            return None
    
    # User-specific operations
    
    def get_user_images(self, user_id, limit=10, skip=0):
        """
        Get images uploaded by a specific user.
        
        Args:
            user_id: ID of the user
            limit: Maximum number of records to return
            skip: Number of records to skip (for pagination)
            
        Returns:
            list: Images uploaded by the user
        """
        if not user_id:
            return []
            
        return list(self.images_collection.find(
            {"user_id": user_id}
        ).sort("upload_date", -1).skip(skip).limit(limit))
    
    def get_user_versions(self, user_id, limit=10, skip=0):
        """
        Get versions created by a specific user.
        
        Args:
            user_id: ID of the user
            limit: Maximum number of records to return
            skip: Number of records to skip (for pagination)
            
        Returns:
            list: Versions created by the user
        """
        if not user_id:
            return []
            
        return list(self.versions_collection.find(
            {"user_id": user_id}
        ).sort("created_date", -1).skip(skip).limit(limit))
    
    def get_user_stats(self, user_id):
        """
        Get statistics about a user's activity.
        
        Args:
            user_id: ID of the user
            
        Returns:
            dict: User activity statistics
        """
        if not user_id:
            return None
            
        # Count uploads
        upload_count = self.images_collection.count_documents({"user_id": user_id})
        
        # Count versions created
        version_count = self.versions_collection.count_documents({"user_id": user_id})
        
        # Get operation types breakdown
        pipeline = [
            {"$match": {"user_id": user_id}},
            {"$group": {
                "_id": {"$arrayElemAt": [{"$split": ["$operation_params.operation", "_"]}, 0]},
                "count": {"$sum": 1}
            }}
        ]
        operations = list(self.versions_collection.aggregate(pipeline))
        
        # Get recent activity
        recent_uploads = self.get_user_images(user_id, limit=5)
        recent_versions = self.get_user_versions(user_id, limit=5)
        
        # Compile statistics
        return {
            "user_id": user_id,
            "total_uploads": upload_count,
            "total_versions": version_count,
            "operations_by_type": {op["_id"]: op["count"] for op in operations},
            "recent_uploads": recent_uploads,
            "recent_versions": recent_versions
        }
    
    # Class methods for direct use without instantiation
    
    @classmethod
    def is_url_processed(cls, url):
        """
        Check if an image from a URL has already been processed.
        
        Args:
            url: The URL to check
            
        Returns:
            tuple: (bool, dict) - (True if processed, record if found)
        """
        try:
            # Get database instance from current app
            db = current_app.db
            # Find image with matching source_url
            record = db.images.find_one({"source_url": url})
            if record:
                return True, record
            return False, None
        except Exception as e:
            current_app.logger.error(f"Error checking URL processing status: {str(e)}")
            return False, None

    @classmethod
    def save_upload_metadata(cls, filename, file_path, original_filename, source_type="upload", source_url=None, user_id=None):
        """
        Save metadata for an uploaded image.
        
        Args:
            filename: The saved filename
            file_path: Path where the file is saved
            original_filename: Original filename from upload
            source_type: Type of upload (upload, url)
            source_url: URL if source_type is url
            user_id: ID of the user who uploaded the image
            
        Returns:
            str: ID of the saved record
        """
        try:
            db = current_app.db
            # Create metadata record
            metadata = {
                "filename": filename,
                "file_path": file_path,
                "original_filename": original_filename,
                "source_type": source_type,
                "source_url": source_url,
                "upload_date": datetime.datetime.utcnow(),
                "version_count": 0,
                "user_id": user_id  # Store user ID
            }
            
            # Insert record
            result = db.images.insert_one(metadata)
            return str(result.inserted_id)
        except Exception as e:
            current_app.logger.error(f"Error saving upload metadata: {str(e)}")
            return None

    @classmethod
    def get_original_image_by_path(cls, file_path):
        """
        Get an original image record by its file path.
        
        Args:
            file_path: Path to the image file
            
        Returns:
            dict: Image record if found, None otherwise
        """
        try:
            db = current_app.db
            return db.images.find_one({"file_path": file_path})
        except Exception as e:
            current_app.logger.error(f"Error getting original image by path: {str(e)}")
            return None

    @classmethod
    def save_original_image(cls, filename, file_path, original_filename, source_type="upload", source_url=None, user_id=None):
        """
        Save metadata for an original image.
        
        Args:
            filename: The saved filename
            file_path: Path where the file is saved
            original_filename: Original filename
            source_type: Type of upload (upload, url)
            source_url: URL if source_type is url
            user_id: ID of the user who uploaded the image
            
        Returns:
            str: ID of the saved record
        """
        try:
            db = current_app.db
            # Create metadata record
            metadata = {
                "filename": filename,
                "file_path": file_path,
                "original_filename": original_filename,
                "source_type": source_type,
                "source_url": source_url,
                "upload_date": datetime.datetime.utcnow(),
                "version_count": 0,
                "user_id": user_id  # Store user ID
            }
            
            # Insert record
            result = db.images.insert_one(metadata)
            return str(result.inserted_id)
        except Exception as e:
            current_app.logger.error(f"Error saving original image: {str(e)}")
            return None

    @classmethod
    def get_next_version_number(cls, original_image_id):
        """
        Get the next available version number for an image.
        
        Args:
            original_image_id: ID of the original image
            
        Returns:
            int: Next version number
        """
        try:
            db = current_app.db
            highest_version = db.image_versions.find_one(
                {"original_image_id": original_image_id},
                sort=[("version_number", -1)]
            )
            
            if highest_version:
                return highest_version["version_number"] + 1
            return 1
        except Exception as e:
            current_app.logger.error(f"Error getting next version number: {str(e)}")
            return 1

    @classmethod
    def create_image_version(cls, original_image_id, processed_path, operation_params, user_id=None):
        """
        Create a new version of an image.
        
        Args:
            original_image_id: ID of the original image
            processed_path: Path to the processed image
            operation_params: Parameters used for processing
            user_id: ID of the user who created this version
            
        Returns:
            str: ID of the created version
        """
        try:
            db = current_app.db
            # Generate operation parameter hash
            operation_param_hash = cls.generate_operation_param_hash(operation_params)
            
            # Get next version number
            version_number = cls.get_next_version_number(original_image_id)
            
            # Create new version document
            version_data = {
                "original_image_id": original_image_id,
                "processed_path": processed_path,
                "created_date": datetime.datetime.utcnow(),
                "version_number": version_number,
                "operation_param_hash": operation_param_hash,
                "operation_params": operation_params,
                "user_id": user_id  # Store user ID
            }
            
            result = db.image_versions.insert_one(version_data)
            
            # Update version count on original image
            db.images.update_one(
                {"_id": ObjectId(original_image_id)},
                {"$inc": {"version_count": 1}}
            )
            
            return str(result.inserted_id)
        except Exception as e:
            current_app.logger.error(f"Error creating image version: {str(e)}")
            return None

    @staticmethod
    def generate_operation_param_hash(operation_params):
        """
        Generate a hash for operation parameters.
        
        Args:
            operation_params: Dictionary of operation parameters
            
        Returns:
            str: Hash of the parameters
        """
        params_str = json.dumps(operation_params, sort_keys=True)
        return hashlib.sha256(params_str.encode()).hexdigest()
        
    @classmethod
    def get_user_statistics(cls, user_id):
        """
        Get comprehensive statistics about a user's activity.
        
        Args:
            user_id: ID of the user
            
        Returns:
            dict: User activity statistics
        """
        try:
            if not user_id:
                return None
                
            db = current_app.db
            
            # Count uploads
            upload_count = db.images.count_documents({"user_id": user_id})
            
            # Count versions created
            version_count = db.image_versions.count_documents({"user_id": user_id})
            
            # Get operation types breakdown
            pipeline = [
                {"$match": {"user_id": user_id}},
                {"$group": {
                    "_id": {"$arrayElemAt": [{"$split": [{"$ifNull": ["$operation_params.operation", "other"]}, "_"]}, 0]},
                    "count": {"$sum": 1}
                }}
            ]
            operations = list(db.image_versions.aggregate(pipeline))
            
            # Get recent uploads
            recent_uploads = list(db.images.find(
                {"user_id": user_id},
                {"_id": 1, "filename": 1, "original_filename": 1, "upload_date": 1}
            ).sort("upload_date", -1).limit(5))
            
            # Get recent operations
            recent_operations = list(db.image_versions.find(
                {"user_id": user_id},
                {"_id": 1, "original_image_id": 1, "operation_params": 1, "created_date": 1}
            ).sort("created_date", -1).limit(5))
            
            # Convert ObjectId to string for serialization
            for upload in recent_uploads:
                if "_id" in upload:
                    upload["_id"] = str(upload["_id"])
                    
            for op in recent_operations:
                if "_id" in op:
                    op["_id"] = str(op["_id"])
                if "original_image_id" in op:
                    op["original_image_id"] = str(op["original_image_id"])
            
            # Compile statistics
            return {
                "user_id": user_id,
                "total_uploads": upload_count,
                "total_versions": version_count,
                "operations_by_type": {op["_id"]: op["count"] for op in operations if op["_id"]},
                "recent_uploads": recent_uploads,
                "recent_operations": recent_operations
            }
        except Exception as e:
            current_app.logger.error(f"Error getting user statistics: {str(e)}")
            return None