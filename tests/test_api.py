import os
import json
import io
import pytest
import responses
from PIL import Image
from io import BytesIO
from unittest.mock import patch, Mock

def test_health_endpoint(client):
    """Test the health check endpoint."""
    response = client.get('/api/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'OK'

def test_api_root_endpoint(client):
    """Test the API root endpoint."""
    response = client.get('/api/')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'name' in data
    assert 'version' in data
    assert 'endpoints' in data

def test_upload_endpoint_success(client, test_image):
    """Test successful image upload."""
    test_image.seek(0)  # Reset file pointer
    response = client.post(
        '/api/images/upload',
        data={'image': (test_image, 'test.jpg')},
        content_type='multipart/form-data'
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'message' in data
    assert 'filename' in data
    assert data['message'] == 'Image successfully uploaded'

def test_upload_endpoint_no_image(client):
    """Test upload endpoint with missing image."""
    response = client.post(
        '/api/images/upload',
        data={},
        content_type='multipart/form-data'
    )
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['error'] == 'No image part in the request'

def test_grayscale_endpoint_success(client, test_image):
    """Test successful grayscale conversion."""
    test_image.seek(0)  # Reset file pointer
    response = client.post(
        '/api/images/grayscale',
        data={'image': (test_image, 'test.jpg')},
        content_type='multipart/form-data'
    )
    assert response.status_code == 200
    assert response.content_type.startswith('image/')
    
    # Check that result is a grayscale image
    img = Image.open(io.BytesIO(response.data))
    assert img.mode == 'L'  # 'L' mode is grayscale

def test_grayscale_endpoint_no_image(client):
    """Test grayscale endpoint with missing image."""
    response = client.post(
        '/api/images/grayscale',
        data={},
        content_type='multipart/form-data'
    )
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['error'] == 'No image part in the request'

@patch('requests.get')
@patch('requests.head')
def test_grayscale_url_endpoint_success(mock_head, mock_get, client, test_image):
    """Test grayscale conversion from URL."""
    image_url = 'https://example.com/test.jpg'
    test_image.seek(0)
    image_content = test_image.read()

    # Mock HEAD request for URL validation
    mock_head.return_value = Mock(headers={'Content-Type': 'image/jpeg'})
    # Mock GET request for image download
    mock_get.return_value = Mock(
        headers={'Content-Type': 'image/jpeg'},
        content=image_content,
        raise_for_status=lambda: None
    )

    response = client.post(
        '/api/images/grayscale-url',
        json={'url': image_url},
        content_type='application/json'
    )

    assert response.status_code == 200
    assert response.content_type.startswith('image/')
    img = Image.open(io.BytesIO(response.data))
    assert img.mode == 'L'

def test_grayscale_url_endpoint_missing_url(client):
    """Test grayscale URL endpoint with missing URL."""
    response = client.post(
        '/api/images/grayscale-url',
        json={},  # Missing URL field
        content_type='application/json'
    )
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data

def test_logs_endpoint(client, test_image):
    """Test the logs endpoint."""
    # First create some logs by uploading an image
    test_image.seek(0)
    client.post(
        '/api/images/upload',
        data={'image': (test_image, 'test.jpg')},
        content_type='multipart/form-data'
    )
    
    # Now test the logs endpoint
    response = client.get('/api/images/logs')
    assert response.status_code == 200
    logs = json.loads(response.data)
    
    # Verify log structure
    assert isinstance(logs, list)
    assert len(logs) > 0
    log = logs[0]
    assert 'timestamp' in log
    assert 'image_name' in log
    assert 'operation' in log

def test_logs_endpoint_with_filters(client, test_image):
    """Test logs endpoint with query parameters."""
    from io import BytesIO
    # First create some logs by uploading and processing images
    test_image.seek(0)
    client.post(
        '/api/images/upload',
        data={'image': (BytesIO(test_image.getvalue()), 'test1.jpg')},
        content_type='multipart/form-data'
    )
    
    test_image.seek(0)
    client.post(
        '/api/images/grayscale',
        data={'image': (BytesIO(test_image.getvalue()), 'test2.jpg')},
        content_type='multipart/form-data'
    )
    
    # Test filtering by operation
    response = client.get('/api/images/logs?operation=upload')
    assert response.status_code == 200
    logs = json.loads(response.data)
    for log in logs:
        assert log['operation'] == 'upload' or log['operation'] == 'upload_for_grayscale'
    
    # Test limit parameter
    response = client.get('/api/images/logs?limit=1')
    assert response.status_code == 200
    logs = json.loads(response.data)
    assert len(logs) <= 1

def test_swagger_docs_endpoint(client):
    """Test the Swagger documentation endpoint."""
    response = client.get('/docs')
    assert response.status_code == 200
    assert b'swagger' in response.data