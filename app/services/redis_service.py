import hashlib
import json
import imagehash
from PIL import Image
import numpy as np
from flask import current_app
import datetime
from bson.objectid import ObjectId

class ImageCacheService:
    """Service for caching processed images using Redis"""
    
    # Key prefixes
    EXACT_HASH_PREFIX = "exact_hash:"
    PHASH_PREFIX = "phash:"
    METADATA_PREFIX = "img_meta:"
    VERSION_PREFIX = "version:"  # New prefix for versioning
    VERSION_PARAMS_PREFIX = "version_params:"  # New prefix for version parameter lookup
    
    @staticmethod
    def get_redis():
        """Get the Redis client"""
        return current_app.redis
    
    @staticmethod
    def calculate_exact_hash(image_path):
        """Calculate exact (cryptographic) hash of image file"""
        try:
            with open(image_path, 'rb') as f:
                file_content = f.read()
                return hashlib.sha256(file_content).hexdigest()
        except Exception as e:
            current_app.logger.error(f"Error calculating exact hash: {str(e)}")
            return None
    
    @staticmethod
    def calculate_perceptual_hash(image_path):
        """Calculate perceptual hash of image"""
        try:
            image = Image.open(image_path)
            # Using pHash algorithm from imagehash
            phash = imagehash.phash(image)
            return str(phash)
        except Exception as e:
            current_app.logger.error(f"Error calculating perceptual hash: {str(e)}")
            return None
    
    @staticmethod
    def phash_similarity(hash1, hash2):
        """
        Calculate similarity between two perceptual hashes
        Returns a value between 0 and 1 (1 being identical)
        """
        try:
            # Convert hash strings to imagehash objects
            if isinstance(hash1, str):
                hash1 = imagehash.hex_to_hash(hash1)
            if isinstance(hash2, str):
                hash2 = imagehash.hex_to_hash(hash2)
                
            # Calculate normalized similarity
            hash_size = len(hash1.hash) * len(hash1.hash[0])  # Total bits in hash
            hamming_dist = hash1 - hash2  # Hamming distance
            
            # Convert to similarity percentage
            similarity = 1 - (hamming_dist / hash_size)
            return similarity
        except Exception as e:
            current_app.logger.error(f"Error calculating hash similarity: {str(e)}")
            return 0
    
    @staticmethod
    def generate_operation_param_hash(operation_params):
        """Generate a hash for operation parameters."""
        try:
            params_str = json.dumps(operation_params, sort_keys=True)
            return hashlib.sha256(params_str.encode()).hexdigest()
        except Exception as e:
            current_app.logger.error(f"Error generating param hash: {str(e)}")
            return None
            
    @staticmethod
    def cache_processed_image(original_path, processed_path, operation, user_id=None):
        """
        Cache a processed image in Redis
        
        Args:
            original_path: Path to the original image
            processed_path: Path to the processed image
            operation: Type of processing operation (e.g., 'grayscale')
            user_id: ID of the user who processed the image (optional)
        
        Returns:
            bool: Success status
        """
        try:
            redis_client = ImageCacheService.get_redis()
            
            # Calculate hashes for the original image
            exact_hash = ImageCacheService.calculate_exact_hash(original_path)
            phash = ImageCacheService.calculate_perceptual_hash(original_path)
            
            if not exact_hash or not phash:
                return False
                
            # Create metadata record
            metadata = {
                "original_path": original_path,
                "processed_path": processed_path,
                "operation": operation,
                "exact_hash": exact_hash,
                "phash": phash,
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "user_id": user_id  # Store user ID in metadata
            }
            
            # Store by exact hash
            exact_key = f"{ImageCacheService.EXACT_HASH_PREFIX}{operation}:{exact_hash}"
            redis_client.set(exact_key, processed_path)
            
            # Store phash in a sorted set - use the hash itself as score for easy retrieval
            phash_key = f"{ImageCacheService.PHASH_PREFIX}{operation}"
            # Convert hexadecimal phash to numeric value for Redis sorted set
            phash_int = int(phash, 16)
            redis_client.zadd(phash_key, {original_path: phash_int})
            
            # Store full metadata
            meta_key = f"{ImageCacheService.METADATA_PREFIX}{original_path}"
            redis_client.set(meta_key, json.dumps(metadata))
            
            return True
        except Exception as e:
            current_app.logger.error(f"Error caching processed image: {str(e)}")
            return False
    
    @staticmethod
    def cache_image_version(original_image_id, version_number, original_path, processed_path, 
                           operation_params, image_hash, expiry=604800, user_id=None):  # Default 1 week
        """
        Cache a specific image version
        
        Args:
            original_image_id: MongoDB ID of the original image
            version_number: Version number
            original_path: Path to the original image
            processed_path: Path to the processed version
            operation_params: Dictionary of transformation parameters
            image_hash: Hash of the processed image
            expiry: Cache expiry time in seconds
            user_id: ID of the user who created this version (optional)
        
        Returns:
            bool: Success status
        """
        try:
            redis_client = ImageCacheService.get_redis()
            
            # Generate param hash for lookup
            param_hash = ImageCacheService.generate_operation_param_hash(operation_params)
            if not param_hash:
                return False
            
            # Convert ObjectId to string if needed
            if isinstance(original_image_id, ObjectId):
                original_image_id = str(original_image_id)
            
            # Store version metadata
            version_metadata = {
                "original_image_id": original_image_id,
                "version_number": version_number,
                "original_path": original_path,
                "processed_path": processed_path,
                "operation_params": operation_params,
                "param_hash": param_hash,
                "image_hash": image_hash,
                "cached_at": datetime.datetime.utcnow().isoformat(),
                "user_id": user_id  # Store user ID in version metadata
            }
            
            # Create version key (by ID and version number)
            version_key = f"{ImageCacheService.VERSION_PREFIX}{original_image_id}:{version_number}"
            redis_client.setex(version_key, expiry, json.dumps(version_metadata))
            
            # Create parameter-based lookup key
            param_key = f"{ImageCacheService.VERSION_PARAMS_PREFIX}{original_image_id}:{param_hash}"
            redis_client.setex(param_key, expiry, json.dumps(version_metadata))
            
            # Track version in stats
            redis_client.hincrby("cache:stats:version", "stored", 1)
            
            return True
        except Exception as e:
            current_app.logger.error(f"Error caching image version: {str(e)}")
            return False
    
    @staticmethod
    def get_version_by_id(original_image_id, version_number):
        """
        Get a specific image version by its ID and version number
        
        Args:
            original_image_id: MongoDB ID of the original image
            version_number: Version number
            
        Returns:
            dict: Version metadata if found, None otherwise
        """
        try:
            redis_client = ImageCacheService.get_redis()
            
            # Create version key
            version_key = f"{ImageCacheService.VERSION_PREFIX}{original_image_id}:{version_number}"
            cached_version = redis_client.get(version_key)
            
            if cached_version:
                # Record hit
                redis_client.hincrby("cache:stats:version", "hits", 1)
                return json.loads(cached_version)
            
            # Record miss
            redis_client.hincrby("cache:stats:version", "misses", 1)
            return None
        except Exception as e:
            current_app.logger.error(f"Error retrieving version: {str(e)}")
            return None
    
    @staticmethod
    def find_version_by_params(original_image_id, operation_params):
        """
        Find a cached version by original image ID and operation parameters
        
        Args:
            original_image_id: MongoDB ID of the original image
            operation_params: Dictionary of transformation parameters
            
        Returns:
            dict: Version metadata if found, None otherwise
        """
        try:
            redis_client = ImageCacheService.get_redis()
            
            # Generate param hash
            param_hash = ImageCacheService.generate_operation_param_hash(operation_params)
            if not param_hash:
                return None
            
            # Create parameter lookup key
            param_key = f"{ImageCacheService.VERSION_PARAMS_PREFIX}{original_image_id}:{param_hash}"
            cached_version = redis_client.get(param_key)
            
            if cached_version:
                # Record hit
                redis_client.hincrby("cache:stats:version", "hits", 1)
                return json.loads(cached_version)
            
            # Record miss
            redis_client.hincrby("cache:stats:version", "misses", 1)
            return None
        except Exception as e:
            current_app.logger.error(f"Error finding version by params: {str(e)}")
            return None
    
    @staticmethod
    def find_processed_image(image_path, operation, similarity_threshold=0.97):
        """
        Find a cached processed image for the given original image
        
        Args:
            image_path: Path to the original image
            operation: Type of processing operation (e.g., 'grayscale')
            similarity_threshold: Minimum similarity for perceptual hash match (0-1)
            
        Returns:
            str: Path to processed image if found, None otherwise
        """
        try:
            redis_client = ImageCacheService.get_redis()
            
            # First try exact hash match (fast path)
            exact_hash = ImageCacheService.calculate_exact_hash(image_path)
            if exact_hash:
                exact_key = f"{ImageCacheService.EXACT_HASH_PREFIX}{operation}:{exact_hash}"
                exact_match = redis_client.get(exact_key)
                if exact_match:
                    # Log cache hit - exact match
                    current_app.logger.info(f"Exact hash cache hit for {image_path}")
                    return exact_match.decode('utf-8')  # Convert bytes to string
            
            # If no exact match, try perceptual hash
            phash = ImageCacheService.calculate_perceptual_hash(image_path)
            if not phash:
                return None
                
            # Get all phashes from Redis
            phash_key = f"{ImageCacheService.PHASH_PREFIX}{operation}"
            all_items = redis_client.zrange(phash_key, 0, -1, withscores=True)
            
            # Convert the target phash to an imagehash object once
            target_phash_obj = imagehash.hex_to_hash(phash)
            
            # Check each stored hash for similarity
            for path_bytes, stored_phash_int in all_items:
                # Convert stored path from bytes to string
                stored_path = path_bytes.decode('utf-8')
                
                # Get metadata to retrieve the full hash string
                meta_key = f"{ImageCacheService.METADATA_PREFIX}{stored_path}"
                metadata_json = redis_client.get(meta_key)
                
                if metadata_json:
                    metadata = json.loads(metadata_json)
                    stored_phash = metadata.get('phash')
                    
                    if stored_phash:
                        # Calculate similarity between hashes
                        similarity = ImageCacheService.phash_similarity(phash, stored_phash)
                        
                        if similarity >= similarity_threshold:
                            # Log cache hit - perceptual match
                            current_app.logger.info(
                                f"Perceptual hash match for {image_path} - "
                                f"similarity: {similarity:.2%}"
                            )
                            return metadata.get('processed_path')
            
            # No match found
            return None
            
        except Exception as e:
            current_app.logger.error(f"Error finding cached image: {str(e)}")
            return None
    
    @staticmethod
    def get_version_stats():
        """Get statistics about version caching"""
        try:
            redis_client = ImageCacheService.get_redis()
            
            # Get basic hit/miss stats
            stats = redis_client.hgetall("cache:stats:version")
            
            # Convert bytes to string and numbers
            result = {}
            for key, value in stats.items():
                key_str = key.decode('utf-8') if isinstance(key, bytes) else key
                result[key_str] = int(value)
            
            # Calculate hit ratio
            hits = result.get('hits', 0)
            misses = result.get('misses', 0)
            total = hits + misses
            
            if total > 0:
                result['hit_ratio'] = round((hits / total) * 100, 2)
            else:
                result['hit_ratio'] = 0
                
            # Count active version keys
            version_keys = redis_client.keys(f"{ImageCacheService.VERSION_PREFIX}*")
            result['active_version_keys'] = len(version_keys)
            
            param_keys = redis_client.keys(f"{ImageCacheService.VERSION_PARAMS_PREFIX}*")
            result['active_param_keys'] = len(param_keys)
            
            return result
        except Exception as e:
            current_app.logger.error(f"Error getting version stats: {str(e)}")
            return {"error": str(e)}
    
    @staticmethod
    def clear_cache():
        """Clear all image caching data from Redis"""
        try:
            redis_client = ImageCacheService.get_redis()
            # Find all keys matching our prefixes
            exact_keys = redis_client.keys(f"{ImageCacheService.EXACT_HASH_PREFIX}*")
            phash_keys = redis_client.keys(f"{ImageCacheService.PHASH_PREFIX}*")
            meta_keys = redis_client.keys(f"{ImageCacheService.METADATA_PREFIX}*")
            version_keys = redis_client.keys(f"{ImageCacheService.VERSION_PREFIX}*")
            param_keys = redis_client.keys(f"{ImageCacheService.VERSION_PARAMS_PREFIX}*")
            
            # Delete all keys
            all_keys = exact_keys + phash_keys + meta_keys + version_keys + param_keys
            if all_keys:
                redis_client.delete(*all_keys)
            
            # Reset stats
            redis_client.delete("cache:stats:version")
            
            return True
        except Exception as e:
            current_app.logger.error(f"Error clearing cache: {str(e)}")
            return False
            
    @staticmethod
    def clear_version_cache(original_image_id=None):
        """
        Clear version cache entries
        
        Args:
            original_image_id: If provided, only clear versions for this image
            
        Returns:
            int: Number of cleared entries
        """
        try:
            redis_client = ImageCacheService.get_redis()
            
            if original_image_id:
                # Clear only specific image versions
                version_keys = redis_client.keys(f"{ImageCacheService.VERSION_PREFIX}{original_image_id}:*")
                param_keys = redis_client.keys(f"{ImageCacheService.VERSION_PARAMS_PREFIX}{original_image_id}:*")
            else:
                # Clear all versions
                version_keys = redis_client.keys(f"{ImageCacheService.VERSION_PREFIX}*")
                param_keys = redis_client.keys(f"{ImageCacheService.VERSION_PARAMS_PREFIX}*")
                
            all_keys = version_keys + param_keys
            
            if all_keys:
                return redis_client.delete(*all_keys)
            return 0
        except Exception as e:
            current_app.logger.error(f"Error clearing version cache: {str(e)}")
            return 0
    
    @staticmethod
    def get_user_cached_versions(user_id):
        """
        Get all cached image versions for a specific user.
        Args:
            user_id: ID of the user
        Returns:
            list: List of version metadata dicts
        """
        try:
            redis_client = ImageCacheService.get_redis()
            version_keys = redis_client.keys(f"{ImageCacheService.VERSION_PREFIX}*")
            user_versions = []
            for key in version_keys:
                data = redis_client.get(key)
                if data:
                    meta = json.loads(data)
                    if meta.get("user_id") == user_id:
                        user_versions.append(meta)
            return user_versions
        except Exception as e:
            current_app.logger.error(f"Error getting user cached versions: {str(e)}")
            return []
    
    @staticmethod
    def get_user_cache_stats(user_id):
        """
        Get cache statistics for a specific user.
        Args:
            user_id: ID of the user
        Returns:
            dict: User cache statistics
        """
        try:
            user_versions = ImageCacheService.get_user_cached_versions(user_id)
            total_versions = len(user_versions)
            operations = {}
            for v in user_versions:
                op = v.get("operation_params", {}).get("operation", "other")
                operations[op] = operations.get(op, 0) + 1
            return {
                "user_id": user_id,
                "total_versions": total_versions,
                "operations_by_type": operations,
                "recent_versions": sorted(user_versions, key=lambda x: x.get("cached_at", ""), reverse=True)[:5]
            }
        except Exception as e:
            current_app.logger.error(f"Error getting user cache stats: {str(e)}")
            return {"error": str(e)}