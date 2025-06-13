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
from app.core.image_processor import convert_to_grayscale, apply_blur, resize_image, rotate_image, apply_transformations
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

def test_blur_processing():
    """Test image blur processing functionality."""
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
            # Test different blur radii
            for radius in [1.0, 2.0, 5.0]:
                # Process image
                output_path = apply_blur(temp_path, radius=radius)
                
                # Verify output exists
                assert os.path.exists(output_path)
                
                # Verify the image was actually blurred
                result_img = Image.open(output_path)
                assert result_img.mode == 'RGB'  # Should maintain RGB mode
                
                # Clean up processed image
                os.remove(output_path)
                
            # Test with negative radius - should still process but with warning
            output_path = apply_blur(temp_path, radius=-1)
            assert os.path.exists(output_path)
            result_img = Image.open(output_path)
            assert result_img.mode == 'RGB'
            os.remove(output_path)
                
    finally:
        # Clean up input file
        if os.path.exists(temp_path):
            os.remove(temp_path)

def test_resize_processing():
    """Test image resize processing functionality."""
    # Create a test RGB image
    rgb_img = Image.new('RGB', (100, 100), color='blue')
    
    # Save to a temporary file
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
        rgb_img.save(temp_file, 'JPEG')
        temp_path = temp_file.name
    
    try:
        # Create app context for testing
        from app import create_app
        app = create_app()
        
        with app.app_context():
            # Test different resize scenarios
            test_cases = [
                # (width, height, resize_type, expected_width, expected_height)
                (50, None, "maintain_aspect_ratio", 50, 50),  # Only width
                (None, 50, "maintain_aspect_ratio", 50, 50),  # Only height
                (50, 50, "maintain_aspect_ratio", 50, 50),    # Both dimensions
                (50, 50, "free", 50, 50),                     # Free resize
            ]
            
            for width, height, resize_type, exp_width, exp_height in test_cases:
                # Process image
                output_path = resize_image(
                    temp_path,
                    width=width,
                    height=height,
                    resize_type=resize_type
                )
                
                # Verify output exists
                assert os.path.exists(output_path)
                
                # Verify dimensions
                result_img = Image.open(output_path)
                assert result_img.size == (exp_width, exp_height)
                
                # Clean up processed image
                os.remove(output_path)
            
            # Test invalid inputs
            with pytest.raises(ValueError):
                resize_image(temp_path, width=-1)
            with pytest.raises(ValueError):
                resize_image(temp_path, height=-1)
            with pytest.raises(ValueError):
                resize_image(temp_path, width=None, height=None)
            with pytest.raises(ValueError):
                resize_image(temp_path, width=50, height=50, resize_type="invalid")
                
    finally:
        # Clean up input file
        if os.path.exists(temp_path):
            os.remove(temp_path)

def test_rotate_processing():
    """Test image rotation processing functionality."""
    # Create a test RGB image with a distinctive pattern
    rgb_img = Image.new('RGB', (100, 50), color='blue')
    # Add a red rectangle to make rotation obvious
    for x in range(25, 75):
        for y in range(10, 40):
            rgb_img.putpixel((x, y), (255, 0, 0))
    
    # Save to a temporary file
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
        rgb_img.save(temp_file, 'JPEG')
        temp_path = temp_file.name
    
    try:
        # Create app context for testing
        from app import create_app
        app = create_app()
        
        with app.app_context():
            # Test different rotation angles
            test_angles = [90, 180, 270, 360]
            
            for angle in test_angles:
                # Process image
                output_path = rotate_image(temp_path, angle=angle)
                
                # Verify output exists
                assert os.path.exists(output_path)
                
                # Verify the image was rotated
                result_img = Image.open(output_path)
                assert result_img.mode == 'RGB'  # Should maintain RGB mode
                
                # For 90 and 270 degrees, dimensions should be swapped
                # Note: PIL's rotate with expand=True may add padding to prevent cropping
                if angle in [90, 270]:
                    # Allow for small padding differences
                    assert abs(result_img.size[0] - 50) <= 2, f"Expected width close to 50, got {result_img.size[0]}"
                    assert abs(result_img.size[1] - 100) <= 2, f"Expected height close to 100, got {result_img.size[1]}"
                else:
                    # Allow for small padding differences
                    assert abs(result_img.size[0] - 100) <= 2, f"Expected width close to 100, got {result_img.size[0]}"
                    assert abs(result_img.size[1] - 50) <= 2, f"Expected height close to 50, got {result_img.size[1]}"
                
                # Clean up processed image
                os.remove(output_path)
                
            # Test with negative angle - should still process but with warning
            output_path = rotate_image(temp_path, angle=-1)
            assert os.path.exists(output_path)
            result_img = Image.open(output_path)
            assert result_img.mode == 'RGB'
            os.remove(output_path)
                
    finally:
        # Clean up input file
        if os.path.exists(temp_path):
            os.remove(temp_path)

def test_combined_transformations():
    """Test applying multiple transformations in sequence."""
    # Create a test RGB image
    rgb_img = Image.new('RGB', (100, 100), color='blue')
    
    # Save to a temporary file
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
        rgb_img.save(temp_file, 'JPEG')
        temp_path = temp_file.name
    
    try:
        # Create app context for testing
        from app import create_app
        app = create_app()
        
        with app.app_context():
            # Define transformations
            transformations = {
                'resize': {
                    'apply': True,
                    'width': 50,
                    'height': 50,
                    'type': 'maintain_aspect_ratio'
                },
                'rotate': {
                    'apply': True,
                    'angle': 90
                },
                'blur': {
                    'apply': True,
                    'radius': 2.0
                }
            }
            
            # Apply transformations
            output_path = apply_transformations(temp_path, transformations)
            
            # Verify output exists
            assert os.path.exists(output_path)
            
            # Verify the final image
            result_img = Image.open(output_path)
            assert result_img.mode == 'RGB'  # Should maintain RGB mode
            
            # Clean up processed image
            os.remove(output_path)
                
    finally:
        # Clean up input file
        if os.path.exists(temp_path):
            os.remove(temp_path)