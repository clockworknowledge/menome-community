import pytest
from fastapi.testclient import TestClient
from backend.services.user_service import create_user, delete_user_by_uuid, get_user_from_db
from backend.schemas.user import UserIn
from backend.db.database import db
from backend.main import app
from backend.config import CurrentConfig
import uuid
from datetime import datetime

# Setup the test configuration before creating the TestClient
CurrentConfig.NEO4J_URI = "bolt://localhost:7687"  # Use the appropriate test URI
CurrentConfig.initialize_environment_variables()
db.reinitialize()

client = TestClient(app)

@pytest.fixture(scope="module")
def service_user():
    user = UserIn(
        username="serviceuser",
        password="servicepassword",
        email="service@user.com",
        name="Service User",
        disabled=False,
        uuid="ba377768-889f-4653-aba9-16dc662648cf"
    )
    return user

@pytest.fixture(scope="module")
def created_service_user(service_user):
    user = create_user(
        username=service_user.username,
        password=service_user.password,
        email=service_user.email,
        name=service_user.name,
        uuid=service_user.uuid
    )
    # Get a valid token for the created service user
    token_response = client.post("/auth/token", data={
        "username": service_user.username,
        "password": service_user.password
    })
    assert token_response.status_code == 200
    token = token_response.json()["access_token"]
    
    yield user, token
    
    # Cleanup is now handled in the teardown_module fixture

@pytest.fixture(scope="module")
def auth_headers(created_service_user):
    _, token = created_service_user
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture(scope="module", autouse=True)
def setup_and_teardown(created_service_user):
    # Setup is already done
    yield
    # Teardown
    user, _ = created_service_user
    delete_user_by_uuid(user.uuid)
    db.close()

@pytest.fixture
def test_user():
    return UserIn(
        username="testuser",
        password="testpassword",
        email="test@example.com",
        name="Test User",
        disabled=False,
        uuid="3513170e-57fb-4200-b9d8-c4aa8df3fc7d"
    )

def test_create_user_valid(test_user, auth_headers):
    response = client.post("/users/create/", json=test_user.model_dump(), headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["username"] == test_user.username
    assert response.json()["email"] == test_user.email
    
    # Cleanup
    delete_user_by_uuid(response.json()["uuid"])
    
def test_create_user_invalid(auth_headers):
    invalid_user = {
        "username": "",
        "password": "Badpassword",
        "email": "invalid_email",
        "name": "",
        "disabled": False
    }
    response = client.post("/users/create/", json=invalid_user, headers=auth_headers)
    # Check if response is 422 which is unprocessable entityy
    assert response.status_code == 422
    assert "detail" in response.json()

def test_delete_user_by_uuid_valid(test_user, auth_headers):
    # Create a test user to delete
    created_user = create_user(

        username=test_user.username,
        password=test_user.password,
        email=test_user.email,
        name=test_user.name,
        uuid=test_user.uuid
    )
    
    response = client.delete(f"/users/user/{created_user.uuid}/", headers=auth_headers)
    assert response.status_code == 200
        
    # Verify user is actually deleted
    assert get_user_from_db(created_user.username) is None

def test_delete_user_by_uuid_invalid_format(auth_headers):
    invalid_uuid = "invalid-uuid"  # This UUID format is invalid
    response = client.delete(f"/users/user/{invalid_uuid}/", headers=auth_headers)
    
    # basic check for 400 - can add additional checks for message etc. 
    assert response.status_code == 400


def test_delete_user_by_nonexistent_uuid(auth_headers):
    nonexistent_uuid = str(uuid.uuid4())  # Generate a valid but nonexistent UUID
    response = client.delete(f"/users/user/{nonexistent_uuid}/", headers=auth_headers)

    assert response.status_code == 404
