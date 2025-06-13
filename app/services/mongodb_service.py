from flask import current_app
import datetime

class ImageMetadataService:
    """Service for handling image metadata in MongoDB"""
    
    @staticmethod
    def get_collection():
        """Get the images collection"""
        return current_app.db.images
    
    @staticmethod
    def save_upload_metadata(filename, file_path, original_filename, source_type="upload", source_url=None):
        """
        Save metadata for an uploaded image
        
        Args:
            filename: The stored filename (with unique ID)
            file_path: Path where the image is stored
            original_filename: Original filename from the upload
            source_type: 'upload' or 'url'
            source_url: Original URL if source_type is 'url'
            
        Returns:
            str: MongoDB document ID
        """
        now = datetime.datetime.utcnow()
        
        # Create document
        document = {
            "filename": filename,
            "file_path": file_path,
            "original_filename": original_filename,
            "source_type": source_type,
            "source_url": source_url,
            "upload_date": now,
            "processed_images": []
        }
        
        # Insert into database
        result = ImageMetadataService.get_collection().insert_one(document)
        return str(result.inserted_id)
    
    @staticmethod
    def save_processed_image(original_filename, original_path, processed_path, operation, source_type="upload"):
        """
        Save metadata for a processed image
        
        Args:
            original_filename: Original stored filename
            original_path: Path to the original image
            processed_path: Path to the processed image
            operation: Type of processing operation (e.g., 'grayscale')
            source_type: 'upload' or 'url'
            
        Returns:
            bool: Success status
        """
        now = datetime.datetime.utcnow()
        
        # Find the original image record
        original_image = ImageMetadataService.get_collection().find_one({"file_path": original_path})
        
        if original_image:
            # Update existing record with processed image info
            processed_info = {
                "operation": operation,
                "processed_path": processed_path,
                "processed_date": now
            }
            
            result = ImageMetadataService.get_collection().update_one(
                {"_id": original_image["_id"]},
                {"$push": {"processed_images": processed_info}}
            )
            
            return result.modified_count > 0
        else:
            # Create a new record if original not found
            document = {
                "filename": original_filename,
                "file_path": original_path,
                "source_type": source_type,
                "upload_date": now,
                "processed_images": [{
                    "operation": operation,
                    "processed_path": processed_path,
                    "processed_date": now
                }]
            }
            
            result = ImageMetadataService.get_collection().insert_one(document)
            return result.inserted_id is not None
    
    @staticmethod
    def get_processing_history(limit=10, operation=None, source_type=None):
        """
        Get history of processed images
        
        Args:
            limit: Maximum number of records to return
            operation: Filter by operation type
            source_type: Filter by source type ('upload' or 'url')
            
        Returns:
            list: List of processing records
        """
        # Build query
        query = {}
        if operation:
            query["processed_images.operation"] = operation
        if source_type:
            query["source_type"] = source_type
        
        # Execute query
        cursor = ImageMetadataService.get_collection().find(
            query, 
            {"_id": 0}  # Exclude MongoDB ID
        ).sort("upload_date", -1).limit(limit)
        
        return list(cursor)
    
    @staticmethod
    def is_url_processed(url, operation=None):
        """
        Check if an image from a URL has already been processed
        
        Args:
            url: The source URL
            operation: Optional operation type filter
            
        Returns:
            tuple: (bool, existing_record) or (False, None)
        """
        query = {"source_url": url}
        if operation:
            query["processed_images.operation"] = operation
        
        record = ImageMetadataService.get_collection().find_one(query)
        
        if record:
            return True, record
        return False, None