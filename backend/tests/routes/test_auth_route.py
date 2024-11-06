# tests/routes/test_auth_route.py

import pytest
from fastapi.testclient import TestClient
from datetime import timedelta

from backend.main import app  # Ensure that your main FastAPI app is imported correctly
from backend.schemas.user import UserIn
from backend.services.user_service import create_user, delete_user
from backend.config import CurrentConfig

# Initialize the TestClient with the FastAPI app
client = TestClient(app)

@pytest.fixture(scope="module")
def test_user():
    """
    Fixture to create a test user before tests and delete it after tests.
    """
    username = "testuser"
    password = "securepassword"
    email = "testuser@example.com"
    name = "Test User"
    uuid = "test-uuid-1234"
    
    # Create the user
    user = create_user(username, password, email, name, uuid)
    
    yield user
    
    # Cleanup: delete the user after tests
    delete_user(username)

def test_login_for_access_token_success(test_user):
    """
    Test obtaining an access token with valid credentials.
    """
    response = client.post(
        "/auth/token",
        data={"username": "testuser", "password": "securepassword"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert response.status_code == 200, f"Unexpected status code: {response.status_code}"
    data = response.json()
    assert "access_token" in data, "Access token not found in response"
    assert data["token_type"] == "bearer", "Token type is not 'bearer'"

def test_login_for_access_token_invalid_username(test_user):
    """
    Test obtaining an access token with an invalid username.
    """
    response = client.post(
        "/auth/token",
        data={"username": "invaliduser", "password": "securepassword"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert response.status_code == 401, f"Unexpected status code: {response.status_code}"
    data = response.json()
    assert data["detail"] == "Incorrect username or password.", "Unexpected error message"

def test_login_for_access_token_invalid_password(test_user):
    """
    Test obtaining an access token with an invalid password.
    """
    response = client.post(
        "/auth/token",
        data={"username": "testuser", "password": "wrongpassword"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert response.status_code == 401, f"Unexpected status code: {response.status_code}"
    data = response.json()
    assert data["detail"] == "Incorrect username or password.", "Unexpected error message"

def test_login_for_access_token_missing_username(test_user):
    """
    Test obtaining an access token with missing username.
    """
    response = client.post(
        "/auth/token",
        data={"password": "securepassword"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert response.status_code == 422, f"Unexpected status code: {response.status_code}"
    data = response.json()
    assert data["detail"][0]["loc"] == ["body", "username"], "Missing username not detected"
    assert data["detail"][0]["msg"] == "Field required", "Unexpected error message for missing username"

def test_login_for_access_token_missing_password(test_user):
    """
    Test obtaining an access token with missing password.
    """
    response = client.post(
        "/auth/token",
        data={"username": "testuser"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert response.status_code == 422, f"Unexpected status code: {response.status_code}"
    data = response.json()
    assert data["detail"][0]["loc"] == ["body", "password"], "Missing password not detected"
    assert data["detail"][0]["msg"] == "Field required", "Unexpected error message for missing password"
