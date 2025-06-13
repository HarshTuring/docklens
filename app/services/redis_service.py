import hashlib
import json
import imagehash
from PIL import Image
import numpy as np
from flask import current_app
import datetime

class ImageCacheService:
    """Service for caching processed images using Redis"""
    
    # Key prefixes
    EXACT_HASH_PREFIX = "exact_hash:"
    PHASH_PREFIX = "phash:"
    METADATA_PREFIX = "img_meta:"
    
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
    def cache_processed_image(original_path, processed_path, operation):
        """
        Cache a processed image in Redis
        
        Args:
            original_path: Path to the original image
            processed_path: Path to the processed image
            operation: Type of processing operation (e.g., 'grayscale')
        
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
                "timestamp": datetime.datetime.utcnow().isoformat()
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
    def clear_cache():
        """Clear all image caching data from Redis"""
        try:
            redis_client = ImageCacheService.get_redis()
            # Find all keys matching our prefixes
            exact_keys = redis_client.keys(f"{ImageCacheService.EXACT_HASH_PREFIX}*")
            phash_keys = redis_client.keys(f"{ImageCacheService.PHASH_PREFIX}*")
            meta_keys = redis_client.keys(f"{ImageCacheService.METADATA_PREFIX}*")
            
            # Delete all keys
            all_keys = exact_keys + phash_keys + meta_keys
            if all_keys:
                redis_client.delete(*all_keys)
            
            return True
        except Exception as e:
            current_app.logger.error(f"Error clearing cache: {str(e)}")
            return False