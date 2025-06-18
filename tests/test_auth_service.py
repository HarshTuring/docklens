import json
import pytest
import requests
import time
from unittest.mock import patch, Mock

# Auth service base URL - this would be the service URL when running
AUTH_SERVICE_BASE_URL = "http://localhost:5002/auth"

def test_auth_service_health():
    """Test the auth service health check endpoint."""
    try:
        response = requests.get(f"{AUTH_SERVICE_BASE_URL}/health", timeout=5)
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'healthy'
        assert 'timestamp' in data
        assert data['service'] == 'auth'
    except requests.exceptions.ConnectionError:
        pytest.skip("Auth service is not running. Start it with docker-compose up auth-service")
    except requests.exceptions.Timeout:
        pytest.skip("Auth service health check timed out")

def test_auth_service_register():
    """Test the auth service register endpoint."""
    # Use unique email to avoid rate limiting
    unique_email = f"test_{int(time.time())}@example.com"
    register_data = {
        "email": unique_email,
        "password": "TestPass123!",
        "first_name": "Test",
        "last_name": "User"
    }
    
    try:
        response = requests.post(
            f"{AUTH_SERVICE_BASE_URL}/register",
            json=register_data,
            headers={'Content-Type': 'application/json'},
            timeout=5
        )
        
        # Should return 201 for successful registration
        assert response.status_code == 201, f"Expected 201, got {response.status_code}. Response: {response.text}"
        data = response.json()
        assert 'message' in data
        assert 'user_id' in data
        assert 'token_expires_at' in data
        assert 'verification_token' in data
        # Password should not be returned
        assert 'password' not in data
        
    except requests.exceptions.ConnectionError:
        pytest.skip("Auth service is not running. Start it with docker-compose up auth-service")
    except requests.exceptions.Timeout:
        pytest.skip("Auth service register request timed out")

def test_auth_service_register_duplicate_email():
    """Test the auth service register endpoint with duplicate email."""
    # Use unique email to avoid rate limiting
    unique_email = f"duplicate_{int(time.time())}@example.com"
    register_data = {
        "email": unique_email,
        "password": "TestPass123!",
        "first_name": "Test",
        "last_name": "User"
    }
    
    try:
        # First registration should succeed
        response1 = requests.post(
            f"{AUTH_SERVICE_BASE_URL}/register",
            json=register_data,
            headers={'Content-Type': 'application/json'},
            timeout=5
        )
        assert response1.status_code == 201, f"Expected 201, got {response1.status_code}. Response: {response1.text}"
        
        # Second registration with same email should fail
        response2 = requests.post(
            f"{AUTH_SERVICE_BASE_URL}/register",
            json=register_data,
            headers={'Content-Type': 'application/json'},
            timeout=5
        )
        assert response2.status_code == 400, f"Expected 400, got {response2.status_code}. Response: {response2.text}"
        data = response2.json()
        assert 'error' in data
        
    except requests.exceptions.ConnectionError:
        pytest.skip("Auth service is not running. Start it with docker-compose up auth-service")
    except requests.exceptions.Timeout:
        pytest.skip("Auth service register request timed out")

def test_auth_service_login():
    """Test the auth service login endpoint."""
    # Use unique email to avoid rate limiting
    unique_email = f"login_{int(time.time())}@example.com"
    register_data = {
        "email": unique_email,
        "password": "TestPass123!",
        "first_name": "Test",
        "last_name": "User"
    }
    
    try:
        # Register the user
        register_response = requests.post(
            f"{AUTH_SERVICE_BASE_URL}/register",
            json=register_data,
            headers={'Content-Type': 'application/json'},
            timeout=5
        )
        assert register_response.status_code == 201, f"Expected 201, got {register_response.status_code}. Response: {register_response.text}"
        
        # Now try to login
        login_data = {
            "email": unique_email,
            "password": "TestPass123!"
        }
        
        login_response = requests.post(
            f"{AUTH_SERVICE_BASE_URL}/login",
            json=login_data,
            headers={'Content-Type': 'application/json'},
            timeout=5
        )
        
        assert login_response.status_code == 200, f"Expected 200, got {login_response.status_code}. Response: {login_response.text}"
        data = login_response.json()
        assert 'access_token' in data
        assert 'refresh_token' in data
        assert 'user' in data
        assert data['user']['email'] == login_data['email']
        
    except requests.exceptions.ConnectionError:
        pytest.skip("Auth service is not running. Start it with docker-compose up auth-service")
    except requests.exceptions.Timeout:
        pytest.skip("Auth service login request timed out")

def test_auth_service_login_invalid_credentials():
    """Test the auth service login endpoint with invalid credentials."""
    login_data = {
        "email": "nonexistent@example.com",
        "password": "WrongPass123!"
    }
    
    try:
        response = requests.post(
            f"{AUTH_SERVICE_BASE_URL}/login",
            json=login_data,
            headers={'Content-Type': 'application/json'},
            timeout=5
        )
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}. Response: {response.text}"
        data = response.json()
        assert 'error' in data
        
    except requests.exceptions.ConnectionError:
        pytest.skip("Auth service is not running. Start it with docker-compose up auth-service")
    except requests.exceptions.Timeout:
        pytest.skip("Auth service login request timed out")

def test_auth_service_login_invalid_data():
    """Test the auth service login endpoint with invalid data."""
    invalid_data_cases = [
        # Missing email
        {
            "password": "TestPass123!"
        },
        # Missing password
        {
            "email": "test@example.com"
        },
        # Invalid email format
        {
            "email": "invalid-email",
            "password": "TestPass123!"
        },
        # Empty data
        {}
    ]
    
    try:
        for invalid_data in invalid_data_cases:
            response = requests.post(
                f"{AUTH_SERVICE_BASE_URL}/login",
                json=invalid_data,
                headers={'Content-Type': 'application/json'},
                timeout=5
            )
            assert response.status_code == 400, f"Expected 400, got {response.status_code}. Response: {response.text}"
            data = response.json()
            assert 'error' in data or 'errors' in data
            
    except requests.exceptions.ConnectionError:
        pytest.skip("Auth service is not running. Start it with docker-compose up auth-service")
    except requests.exceptions.Timeout:
        pytest.skip("Auth service login request timed out")
