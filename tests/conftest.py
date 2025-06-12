import os
import sys
import json
import pytest
import tempfile
import shutil
from io import BytesIO
from PIL import Image

# Add the parent directory to sys.path to fix import issues
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app

@pytest.fixture
def app():
    """Create and configure a Flask app for testing."""
    # Set up test environment variables
    os.environ['FLASK_ENV'] = 'test'
    
    # Create temporary directories
    test_dir = tempfile.mkdtemp()
    upload_dir = os.path.join(test_dir, 'uploads')
    processed_dir = os.path.join(test_dir, 'static', 'processed_images')
    logs_dir = os.path.join(test_dir, 'logs')
    
    os.makedirs(upload_dir, exist_ok=True)
    os.makedirs(processed_dir, exist_ok=True)
    os.makedirs(logs_dir, exist_ok=True)
    
    # Create and configure app
    flask_app = create_app()
    
    # Override configurations for testing
    flask_app.config.update({
        'TESTING': True,
        'UPLOAD_FOLDER': upload_dir,
        'SERVER_NAME': 'localhost',
    })
    
    # Configure the app for the test context
    with flask_app.app_context():
        # Create initial log file
        log_file = os.path.join(logs_dir, 'image_operations.json')
        with open(log_file, 'w') as f:
            json.dump([], f)
    
    # Yield the app for testing
    yield flask_app
    
    # Clean up after the test
    shutil.rmtree(test_dir)

@pytest.fixture
def client(app):
    """Create a test client for the app."""
    return app.test_client()

@pytest.fixture
def test_image():
    """Create a simple test RGB image in memory."""
    # Create a 100x100 red image
    img = Image.new('RGB', (100, 100), color='red')
    img_io = BytesIO()
    img.save(img_io, 'JPEG')
    img_io.seek(0)
    return img_io

@pytest.fixture
def grayscale_image():
    """Create a grayscale test image in memory."""
    # Create a 100x100 gray image
    img = Image.new('L', (100, 100), color=128)
    img_io = BytesIO()
    img.save(img_io, 'JPEG')
    img_io.seek(0)
    return img_io

@pytest.fixture
def log_file(app):
    """Get the path to the log file for testing."""
    with app.app_context():
        log_dir = os.path.join(app.root_path, 'logs')
        return os.path.join(log_dir, 'image_operations.json')