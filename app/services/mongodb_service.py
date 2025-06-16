import datetime
import hashlib
import json
import os
from bson.objectid import ObjectId

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
        
        # Indexes for versions
        self.versions_collection.create_index("original_image_id")
        self.versions_collection.create_index([
            ("original_image_id", 1),
            ("operation_param_hash", 1)
        ], unique=True)
        self.versions_collection.create_index("created_date")
        self.versions_collection.create_index("version_number")
    
    # Original image methods
    
    def store_original_image(self, filename, file_path, original_filename, image_hash, 
                            source_type="upload", source_url=None):
        """Store metadata for an original uploaded image."""
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
            "version_count": 0
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
    
    def get_recent_uploads(self, limit=10):
        """Get recent image uploads."""
        return list(self.images_collection.find().sort("upload_date", -1).limit(limit))
    
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
    
    def create_image_version(self, original_image_id, processed_path, operation_params, image_hash):
        """Create a new version of an image."""
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
            "operation_params": operation_params  # Store the actual parameters for reference
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
    
    def get_image_versions(self, image_id):
        """Get all versions of an image."""
        try:
            versions = self.versions_collection.find(
                {"original_image_id": image_id}
            ).sort("version_number", 1)
            
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
    
    def get_or_create_version(self, original_image_id, operation_params, processed_path, image_hash):
        """Get an existing version or create a new one."""
        # Check if version exists
        existing_version = self.find_version_by_params(original_image_id, operation_params)
        
        if existing_version:
            return str(existing_version["_id"]), existing_version["processed_path"], True
        
        # Create new version
        return self.create_image_version(
            original_image_id, 
            processed_path, 
            operation_params, 
            image_hash
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
                "total_versions": len(versions),
                "latest_version": max([v["version_number"] for v in versions]) if versions else 0,
                "latest_processing_date": max([v["created_date"] for v in versions]) if versions else None
            }
        except Exception:
            return None