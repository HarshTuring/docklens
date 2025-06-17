import os
import pytest
from bson import ObjectId
from PIL import Image
from io import BytesIO
from app.services.mongodb_service import ImageMetadataService
from app.services.redis_service import ImageCacheService
from app.core.image_processor import (
    convert_to_grayscale,
    apply_blur,
    rotate_image,
    resize_image,
    remove_background
)

@pytest.fixture
def sample_image():
    """Create a sample image for testing."""
    # Create a simple test image
    img = Image.new('RGB', (100, 100), color='red')
    img_byte_arr = BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    return img_byte_arr

@pytest.fixture(autouse=True)
def setup_database(app):
    """Setup and teardown database for each test."""
    with app.app_context():
        # Drop all collections and indexes
        app.db.images.drop()
        app.db.image_versions.drop()
        yield
        # Clean up after test
        app.db.images.drop()
        app.db.image_versions.drop()

@pytest.fixture
def image_metadata_service(app):
    """Create an instance of ImageMetadataService for testing."""
    with app.app_context():
        # Get the database instance from the app context
        db = app.db
        service = ImageMetadataService(db)
        # Create indexes
        service._create_indexes()
        yield service

@pytest.fixture
def image_cache_service(app):
    """Create an instance of ImageCacheService for testing."""
    with app.app_context():
        # ImageCacheService uses static methods and gets Redis from current_app
        yield ImageCacheService

def test_save_original_image(image_metadata_service, sample_image, app):
    """Test saving an original image."""
    with app.app_context():
        # Save the image
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'test_image.png')
        with open(file_path, 'wb') as f:
            f.write(sample_image.getvalue())
        
        # Calculate image hash
        image_hash = ImageCacheService.calculate_exact_hash(file_path)
        
        # Save metadata
        image_id = image_metadata_service.store_original_image(
            filename='test_image.png',
            file_path=file_path,
            original_filename='test_image.png',
            image_hash=image_hash,
            source_type='upload',
            source_url=None
        )
        
        # Verify the image was saved
        saved_image = image_metadata_service.images_collection.find_one({'_id': ObjectId(image_id)})
        assert saved_image is not None
        assert saved_image['filename'] == 'test_image.png'
        assert saved_image['file_path'] == file_path
        assert saved_image['source_type'] == 'upload'
        assert saved_image['version_count'] == 0

def test_create_image_version(image_metadata_service, sample_image, app):
    """Test creating an image version."""
    with app.app_context():
        # First save an original image
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'test_image.png')
        with open(file_path, 'wb') as f:
            f.write(sample_image.getvalue())
        
        image_hash = ImageCacheService.calculate_exact_hash(file_path)
        image_id = image_metadata_service.store_original_image(
            filename='test_image.png',
            file_path=file_path,
            original_filename='test_image.png',
            image_hash=image_hash,
            source_type='upload',
            source_url=None
        )
        
        # Create a version
        operation_params = {'grayscale': True}
        version_id = ImageMetadataService.create_image_version(
            original_image_id=image_id,
            processed_path=file_path,
            operation_params=operation_params
        )
        
        # Verify the version was created
        version = image_metadata_service.versions_collection.find_one({'_id': ObjectId(version_id)})
        assert version is not None
        assert version['original_image_id'] == image_id
        assert version['version_number'] == 1
        assert version['operation_params'] == operation_params
        
        # Verify version count was updated
        original = image_metadata_service.images_collection.find_one({'_id': ObjectId(image_id)})
        assert original['version_count'] == 1

def test_get_next_version_number(image_metadata_service, sample_image, app):
    """Test getting the next version number."""
    with app.app_context():
        # First save an original image
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'test_image.png')
        with open(file_path, 'wb') as f:
            f.write(sample_image.getvalue())
        
        image_hash = ImageCacheService.calculate_exact_hash(file_path)
        image_id = image_metadata_service.store_original_image(
            filename='test_image.png',
            file_path=file_path,
            original_filename='test_image.png',
            image_hash=image_hash,
            source_type='upload',
            source_url=None
        )
        
        # Create multiple versions
        for i in range(3):
            operation_params = {'grayscale': True, 'version': i}
            ImageMetadataService.create_image_version(
                original_image_id=image_id,
                processed_path=file_path,
                operation_params=operation_params
            )
        
        # Get next version number
        next_version = image_metadata_service.get_next_version_number(image_id)
        assert next_version == 4

def test_generate_operation_param_hash(image_metadata_service):
    """Test generating operation parameter hash."""
    # Test with different parameter combinations
    params1 = {'grayscale': True}
    params2 = {'grayscale': True, 'blur': {'radius': 5}}
    params3 = {'grayscale': True, 'blur': {'radius': 5}, 'rotate': {'angle': 90}}
    
    hash1 = image_metadata_service.generate_operation_param_hash(params1)
    hash2 = image_metadata_service.generate_operation_param_hash(params2)
    hash3 = image_metadata_service.generate_operation_param_hash(params3)
    
    # Verify hashes are different for different parameters
    assert hash1 != hash2 != hash3
    
    # Verify same parameters produce same hash
    hash1_again = image_metadata_service.generate_operation_param_hash(params1)
    assert hash1 == hash1_again

def test_cache_integration(image_metadata_service, image_cache_service, app, sample_image):
    """Test integration between metadata service and cache service."""
    with app.app_context():
        # Save original image
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'test_image.png')
        with open(file_path, 'wb') as f:
            f.write(sample_image.getvalue())
        
        image_hash = ImageCacheService.calculate_exact_hash(file_path)
        image_id = image_metadata_service.store_original_image(
            filename='test_image.png',
            file_path=file_path,
            original_filename='test_image.png',
            image_hash=image_hash,
            source_type='upload',
            source_url=None
        )
        
        # Create a version with caching
        operation_params = {'grayscale': True}
        version_id = ImageMetadataService.create_image_version(
            original_image_id=image_id,
            processed_path=file_path,
            operation_params=operation_params
        )
        
        # Cache the version
        image_cache_service.cache_image_version(
            original_image_id=str(image_id),
            version_number=1,
            original_path=file_path,
            processed_path=file_path,
            operation_params=operation_params,
            image_hash=image_hash
        )
        
        # Verify version is in cache
        cached_version = image_cache_service.get_version_by_id(str(image_id), 1)
        assert cached_version is not None
        assert cached_version['original_image_id'] == str(image_id)
        assert cached_version['version_number'] == 1

def test_transformation_versioning(image_metadata_service, app, sample_image):
    """Test creating versions with different transformations."""
    with app.app_context():
        # Save original image
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'test_image.png')
        with open(file_path, 'wb') as f:
            f.write(sample_image.getvalue())
        
        image_hash = ImageCacheService.calculate_exact_hash(file_path)
        image_id = image_metadata_service.store_original_image(
            filename='test_image.png',
            file_path=file_path,
            original_filename='test_image.png',
            image_hash=image_hash,
            source_type='upload',
            source_url=None
        )
        
        # Create versions with different transformations
        transformations = [
            {'grayscale': True},
            {'blur': {'apply': True, 'radius': 5}},
            {'rotate': {'apply': True, 'angle': 90}},
            {'resize': {'apply': True, 'width': 200, 'height': 200, 'type': 'maintain_aspect_ratio'}},
            {'remove_background': True}
        ]
        
        version_ids = []
        for params in transformations:
            version_id = ImageMetadataService.create_image_version(
                original_image_id=image_id,
                processed_path=file_path,
                operation_params=params
            )
            version_ids.append(version_id)
        
        # Verify all versions were created
        assert len(version_ids) == len(transformations)
        
        # Verify version numbers are sequential
        versions = list(image_metadata_service.versions_collection.find(
            {"original_image_id": image_id}
        ).sort("version_number", 1))
        
        for i, version in enumerate(versions, 1):
            assert version['version_number'] == i
            assert version['operation_params'] == transformations[i-1] 