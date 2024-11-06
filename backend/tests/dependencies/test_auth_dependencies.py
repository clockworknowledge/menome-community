# tests/dependencies/test_auth_dependency.py

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.testclient import TestClient
from jose import JWTError, jwt
from passlib.context import CryptContext

from backend.dependencies.auth import (
    verify_password,
    create_access_token,
    authenticate_user,
    get_current_user,
    get_optional_current_user,
    oauth2_scheme
)
from backend.schemas.user import User, UserIn
from backend.exceptions.database_exceptions import (
    DatabaseConnectionError,
    UserNotFoundError,
    InvalidRoleAssignmentError
)
from backend.config import CurrentConfig

# Initialize FastAPI TestClient for dependency testing
from fastapi import FastAPI

app = FastAPI()

# Dependency overrides for testing
@pytest.fixture
def client():
    return TestClient(app)

# Fixture for mocking get_user_from_db
@pytest.fixture
def mock_get_user_from_db():
    with patch('backend.dependencies.auth.get_user_from_db') as mock:
        yield mock

# Fixture for mocking jwt.encode and jwt.decode
@pytest.fixture
def mock_jwt():
    with patch('backend.dependencies.auth.jwt.encode') as mock_encode, \
         patch('backend.dependencies.auth.jwt.decode') as mock_decode:
        yield mock_encode, mock_decode

# Fixture for setting up CryptContext (if needed)
@pytest.fixture
def pwd_context():
    return CryptContext(schemes=["bcrypt"], deprecated="auto")

# Sample user data for testing
@pytest.fixture
def sample_user():
    return UserIn(
        username="testuser",
        email="testuser@example.com",
        name="Test User",
        password="$2b$12$KIXQ1m1qK1v7a9O8xG4XuORFZ3E0qA1QyK2eF8rYzZ1vJ1uYg6L5G",  # bcrypt hash for "securepassword"
        uuid="1234-5678",
        disabled=False,
        datecreated=datetime.utcnow().isoformat()
    )

# --------------------------- Tests for verify_password ---------------------------

def test_verify_password_correct(pwd_context):
    plain_password = "securepassword"
    hashed_password = pwd_context.hash(plain_password)
    assert verify_password(plain_password, hashed_password) is True

def test_verify_password_incorrect(pwd_context):
    plain_password = "securepassword"
    wrong_password = "wrongpassword"
    hashed_password = pwd_context.hash(plain_password)
    assert verify_password(wrong_password, hashed_password) is False

# --------------------------- Tests for create_access_token ---------------------------


def test_create_access_token_default_expiry(mock_jwt):
    data = {"sub": "testuser"}
    
    # Mock datetime to return a fixed current time
    fixed_now = datetime(2024, 10, 10, 22, 51, 43, 711830, tzinfo=timezone.utc)
    with patch('backend.dependencies.auth.datetime') as mock_datetime:
        mock_datetime.utcnow.return_value = fixed_now
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
        
        token = create_access_token(data)
    
    mock_jwt[0].assert_called_once()
    args, kwargs = mock_jwt[0].call_args
    
    # Expected payload
    expected_payload = {
        "sub": "testuser",
        "exp": fixed_now.timestamp() + 15 * 60  # 15 minutes default expiry
    }
    
    # Extract the actual payload passed to jwt.encode
    actual_payload = args[0]
    
    assert actual_payload["sub"] == expected_payload["sub"]
    assert actual_payload["exp"] == expected_payload["exp"]
    
def test_create_access_token_custom_expiry(mock_jwt):
    data = {"sub": "testuser"}
    expires_delta = timedelta(minutes=30)
    
    # Mock datetime to return a fixed current time
    fixed_now = datetime(2024, 10, 10, 23, 6, 43, 735646, tzinfo=timezone.utc)
    with patch('backend.dependencies.auth.datetime') as mock_datetime:
        mock_datetime.utcnow.return_value = fixed_now
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
        
        token = create_access_token(data, expires_delta=expires_delta)
    
    mock_jwt[0].assert_called_once()
    args, kwargs = mock_jwt[0].call_args
    
    # Expected payload
    expected_payload = {
        "sub": "testuser",
        "exp": fixed_now.timestamp() + 30 * 60  # 30 minutes custom expiry
    }
    
    # Extract the actual payload passed to jwt.encode
    actual_payload = args[0]
    
    assert actual_payload["sub"] == expected_payload["sub"]
    assert actual_payload["exp"] == expected_payload["exp"]

# --------------------------- Tests for authenticate_user ---------------------------

def test_authenticate_user_success(mock_get_user_from_db, pwd_context, sample_user):
    username = "testuser"
    password = "securepassword"
    hashed_password = pwd_context.hash(password)
    user = sample_user
    user.password = hashed_password  # Update the hashed password
    
    mock_get_user_from_db.return_value = user
    
    authenticated_user = authenticate_user(username, password)
    
    assert authenticated_user is not None
    assert authenticated_user.username == username

def test_authenticate_user_wrong_password(mock_get_user_from_db, pwd_context, sample_user):
    username = "testuser"
    password = "securepassword"
    wrong_password = "wrongpassword"
    hashed_password = pwd_context.hash(password)
    user = sample_user
    user.password = hashed_password  # Update the hashed password
    
    mock_get_user_from_db.return_value = user
    
    authenticated_user = authenticate_user(username, wrong_password)
    
    assert authenticated_user is None

def test_authenticate_user_user_not_found(mock_get_user_from_db):
    username = "nonexistent"
    password = "any_password"
    
    mock_get_user_from_db.return_value = None
    
    authenticated_user = authenticate_user(username, password)
    
    assert authenticated_user is None

# --------------------------- Tests for get_current_user ---------------------------

@pytest.mark.asyncio
async def test_get_current_user_success(mock_get_user_from_db, mock_jwt, sample_user):
    token = "validtoken"
    user = sample_user
    
    # Mock jwt.decode to return payload with 'sub'
    payload = {"sub": user.username, "exp": datetime.utcnow().timestamp() + 600}
    mock_jwt[1].return_value = payload
    
    # Mock get_user_from_db to return the user
    mock_get_user_from_db.return_value = user
    
    # Override the dependency
    async def override_get_current_user(token: str = Depends(oauth2_scheme)):
        return await get_current_user(token)
    
    app.dependency_overrides[get_current_user] = override_get_current_user
    
    with TestClient(app) as client:
        response = client.get("/protected-route", headers={"Authorization": f"Bearer {token}"})
        # Since there's no actual route defined, we'll directly call the dependency
        # Instead, we can test the dependency function directly
        current_user = await get_current_user(token)
        assert current_user is not None
        assert current_user.username == user.username

@pytest.mark.asyncio
async def test_get_current_user_invalid_token(mock_jwt):
    token = "invalidtoken"
    
    # Mock jwt.decode to raise JWTError
    mock_jwt[1].side_effect = JWTError("Invalid token")
    
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(token)
    
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc_info.value.detail == "Could not validate credentials."

@pytest.mark.asyncio
async def test_get_current_user_user_not_found(mock_get_user_from_db, mock_jwt):
    token = "validtoken"
    username = "nonexistent"
    
    # Mock jwt.decode to return payload with 'sub'
    payload = {"sub": username, "exp": datetime.utcnow().timestamp() + 600}
    with patch('backend.dependencies.auth.jwt.decode', return_value=payload):
        mock_get_user_from_db.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert exc_info.value.detail == "Could not validate credentials."

# --------------------------- Tests for get_optional_current_user ---------------------------

@pytest.mark.asyncio
async def test_get_optional_current_user_no_token():
    # Simulate no token provided
    with patch('backend.dependencies.auth.oauth2_scheme') as mock_oauth2_scheme:
        mock_oauth2_scheme.return_value = None
        
        user = await get_optional_current_user(token=None)
        
        assert user is None

@pytest.mark.asyncio
async def test_get_optional_current_user_valid_token(mock_get_user_from_db, mock_jwt, sample_user):
    token = "validtoken"
    user = sample_user
    
    # Mock jwt.decode to return payload with 'sub'
    payload = {"sub": user.username, "exp": datetime.utcnow().timestamp() + 600}
    mock_jwt[1].return_value = payload
    
    # Mock get_user_from_db to return the user
    mock_get_user_from_db.return_value = user
    
    user_result = await get_optional_current_user(token=token)
    
    assert user_result is not None
    assert user_result.username == user.username

@pytest.mark.asyncio
async def test_get_optional_current_user_invalid_token(mock_jwt):
    token = "invalidtoken"
    
    # Mock jwt.decode to raise JWTError
    mock_jwt[1].side_effect = JWTError("Invalid token")
    
    user_result = await get_optional_current_user(token=token)
    
    assert user_result is None

@pytest.mark.asyncio
async def test_get_optional_current_user_user_not_found(mock_get_user_from_db, mock_jwt):
    token = "validtoken"
    username = "nonexistent"
    
    # Mock jwt.decode to return payload with 'sub'
    payload = {"sub": username, "exp": datetime.utcnow().timestamp() + 600}
    mock_jwt[1].return_value = payload
    
    # Mock get_user_from_db to return None
    mock_get_user_from_db.return_value = None
    
    user_result = await get_optional_current_user(token=token)
    
    assert user_result is None

# --------------------------- Additional Notes ---------------------------

"""
- **Testing Asynchronous Functions**:
    - Functions like `get_current_user` and `get_optional_current_user` are asynchronous. Hence, we use `pytest.mark.asyncio` to handle these tests.
  
- **Mocking `jwt.encode` and `jwt.decode`**:
    - We mock `jwt.encode` and `jwt.decode` to control their behavior during tests, ensuring consistent and predictable outcomes.
  
- **Mocking Dependencies**:
    - `get_user_from_db` is a dependency that interacts with the database. We mock it to return predefined user objects or `None` based on the test scenario.
  
- **Testing `get_current_user` and `get_optional_current_user`**:
    - These functions rely on FastAPI's `Depends` and `OAuth2PasswordBearer`. We simulate token retrieval by directly passing the token to the functions.
    - For more integrated testing, you can define protected routes and use `TestClient` to make requests with appropriate headers. However, for unit testing dependencies in isolation, directly calling the functions with mocked dependencies is sufficient.
  
- **Password Hashing**:
    - Ensure that the `pwd_context` used in tests matches the one in your actual application to maintain consistency in password hashing and verification.
  
- **Error Handling**:
    - Tests assert that appropriate exceptions are raised with correct details when errors occur, ensuring that your application handles error scenarios gracefully.
"""



