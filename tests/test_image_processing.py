# tests/test_image_processing.py
import os
import json
import pytest
import tempfile
from PIL import Image
from io import BytesIO
from unittest.mock import patch, Mock

# Import app components directly
from app.utils.helpers import allowed_file, save_uploaded_file, is_valid_image_url
from app.core.image_processor import convert_to_grayscale
from app.utils.logger import log_operation, get_operation_logs

def test_allowed_file_function():
    """Test the allowed_file helper function."""
    with tempfile.NamedTemporaryFile(suffix='.jpg') as valid_file, \
         tempfile.NamedTemporaryFile(suffix='.txt') as invalid_file:
        
        # Need to create an app context to access configuration
        from app import create_app
        app = create_app()
        
        with app.app_context():
            # Test valid file types
            assert allowed_file('test.jpg') is True
            assert allowed_file('test.png') is True
            assert allowed_file('test.jpeg') is True
            assert allowed_file('test.gif') is True
            
            # Test invalid file types
            assert allowed_file('test.txt') is False
            assert allowed_file('test.pdf') is False
            assert allowed_file('test') is False
            assert allowed_file('') is False

def test_grayscale_conversion():
    """Test image grayscale conversion functionality."""
    # Create a test RGB image
    rgb_img = Image.new('RGB', (50, 50), color='blue')
    
    # Save to a temporary file
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
        rgb_img.save(temp_file, 'JPEG')
        temp_path = temp_file.name
    
    try:
        # Create app context for testing
        from app import create_app
        app = create_app()
        
        with app.app_context():
            # Process image
            output_path = convert_to_grayscale(temp_path)
            
            # Verify output exists and is grayscale
            assert os.path.exists(output_path)
            result_img = Image.open(output_path)
            assert result_img.mode == 'L'  # L mode means grayscale
            
            # Clean up processed image
            os.remove(output_path)
    finally:
        # Clean up input file
        if os.path.exists(temp_path):
            os.remove(temp_path)

def test_url_validation():
    """Test URL validation function."""
    valid_url = 'https://example.com/image.jpg'
    invalid_url = 'https://example.com/page.html'

    with patch('requests.head') as mock_head:
        # Valid image URL
        mock_head.return_value = Mock(headers={'Content-Type': 'image/jpeg'})
        assert is_valid_image_url(valid_url) is True

        # Not an image
        mock_head.return_value = Mock(headers={'Content-Type': 'text/html'})
        assert is_valid_image_url(invalid_url) is False

        # Malformed/empty URLs (should not call requests.head)
        assert is_valid_image_url('not-a-url') is False
        assert is_valid_image_url('') is False

def test_logging_functionality(app, log_file):
    """Test logging functionality."""
    # Clear the log file before the test
    with open(log_file, 'w') as f:
        json.dump([], f)

    with app.app_context():
        # Log a test operation
        log_operation(
            image_name='test.jpg',
            operation='test_operation',
            source_type='test',
            details={'test_key': 'test_value'}
        )
        
        # Get logs and verify
        logs = get_operation_logs()
        assert len(logs) >= 1
        
        # Find our test log
        test_logs = [log for log in logs if log['operation'] == 'test_operation']
        assert len(test_logs) == 1
        
        log_entry = test_logs[0]
        assert log_entry['image_name'] == 'test.jpg'
        assert log_entry['source_type'] == 'test'
        assert log_entry['status'] == 'success'
        assert 'details' in log_entry
        assert log_entry['details']['test_key'] == 'test_value'