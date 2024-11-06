# tests/services/test_user_service.py

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from neo4j.exceptions import Neo4jError

from backend.services.user_service import (
    get_user_from_db,
    create_user,
    add_roles_to_user,
    delete_user_by_uuid,
    delete_user,
    authenticate_user,
    hash_password,
    verify_password
)
from backend.schemas.user import UserIn, UserRoles, User
from backend.exceptions.database_exceptions import DatabaseConnectionError, UserNotFoundError, InvalidRoleAssignmentError

# Fixture to mock the db.get_session without using pytest-mock
@pytest.fixture
def mock_db_session():
    with patch('backend.services.user_service.db.get_session') as mock_get_session:
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        yield mock_session

# Helper function to create a mock result with a single record
def mock_single_record(return_value):
    mock_record = MagicMock()
    mock_record.__getitem__.side_effect = lambda key: return_value.get(key)
    mock_record.get.side_effect = lambda key: return_value.get(key)
    return mock_record

# Tests for get_user_from_db
def test_get_user_from_db_user_exists(mock_db_session):
    username = "testuser"
    mock_record_data = {
        'username': username,
        'password': 'hashedpassword',
        'uuid': '1234-5678',
        'email': 'test@example.com',
        'name': 'Test User',
        'disabled': False,
        'datecreated': '2023-01-01T00:00:00'
    }
    mock_record = mock_single_record({'u': mock_record_data})
    mock_result = MagicMock()
    mock_result.single.return_value = mock_record
    mock_db_session.run.return_value = mock_result

    user = get_user_from_db(username)

    assert user is not None
    assert isinstance(user, UserIn)
    assert user.username == username
    assert user.email == 'test@example.com'

def test_get_user_from_db_user_not_exists(mock_db_session):
    username = "nonexistent"
    mock_result = MagicMock()
    mock_result.single.return_value = None
    mock_db_session.run.return_value = mock_result

    user = get_user_from_db(username)

    assert user is None

def test_get_user_from_db_database_error(mock_db_session):
    username = "testuser"
    mock_db_session.run.side_effect = Neo4jError("Connection failed")

    with pytest.raises(DatabaseConnectionError) as exc_info:
        get_user_from_db(username)

    assert exc_info.value.detail == "Connection failed"

# Tests for hash_password
def test_hash_password():
    password = "securepassword"
    hashed = hash_password(password)
    assert hashed != password
    assert hashed.startswith("$2b$")  # bcrypt hash prefix

# Tests for verify_password
def test_verify_password_correct():
    password = "securepassword"
    hashed = hash_password(password)
    assert verify_password(password, hashed) is True

def test_verify_password_incorrect():
    password = "securepassword"
    hashed = hash_password(password)
    assert verify_password("wrongpassword", hashed) is False

# Tests for create_user
def test_create_user_success_with_uuid(mock_db_session):
    username = "newuser"
    password = "newpassword"
    email = "new@example.com"
    name = "New User"
    uuid = "unique-uuid-1234"
    date_created = datetime.utcnow().isoformat()

    mock_user_node = {
        'username': username,
        'email': email,
        'name': name,
        'password': 'hashedpassword',
        'disabled': False,
        'uuid': uuid,
        'datecreated': date_created
    }
    mock_record = mock_single_record({'u': mock_user_node})
    mock_result = MagicMock()
    mock_result.single.return_value = mock_record
    mock_db_session.run.return_value = mock_result

    user = create_user(username, password, email, name, uuid)

    assert user is not None
    assert isinstance(user, UserIn)
    assert user.username == username
    assert user.uuid == uuid
    assert user.email == email

def test_create_user_success_without_uuid(mock_db_session):
    username = "newuser"
    password = "newpassword"
    email = "new@example.com"
    name = "New User"

    mock_user_node = {
        'username': username,
        'email': email,
        'name': name,
        'password': 'hashedpassword',
        'disabled': False,
        'uuid': 'generated-uuid-5678',
        'datecreated': '2023-01-01T00:00:00'
    }
    mock_record = mock_single_record({'u': mock_user_node})
    mock_result = MagicMock()
    mock_result.single.return_value = mock_record
    mock_db_session.run.return_value = mock_result

    user = create_user(username, password, email, name)

    assert user is not None
    assert isinstance(user, UserIn)
    assert user.username == username
    assert user.uuid == 'generated-uuid-5678'
    assert user.email == email

def test_create_user_database_error(mock_db_session):
    username = "newuser"
    password = "newpassword"
    email = "new@example.com"
    name = "New User"

    mock_db_session.run.side_effect = Neo4jError("Creation failed")

    with pytest.raises(Neo4jError) as exc_info:
        create_user(username, password, email, name)
    
    assert "Creation failed" in str(exc_info.value)

# Tests for add_roles_to_user
def test_add_roles_to_user_success(mock_db_session):
    username = "testuser"
    roles = ["Admin", "Editor"]
    mock_record_data = {
        "username": username,
        "roles": roles
    }
    mock_record = mock_single_record(mock_record_data)
    mock_result = MagicMock()
    mock_result.single.return_value = mock_record
    mock_db_session.run.return_value = mock_result

    user_roles = add_roles_to_user(username, roles)

    assert user_roles is not None
    assert isinstance(user_roles, UserRoles)
    assert user_roles.username == username
    assert set(user_roles.roles) == set(roles)

def test_add_roles_to_user_no_roles(mock_db_session):
    username = "testuser"
    roles = []

    with pytest.raises(InvalidRoleAssignmentError) as exc_info:
        add_roles_to_user(username, roles)
    
    assert exc_info.value.detail == "At least one role must be assigned"

def test_add_roles_to_user_user_not_found(mock_db_session):
    username = "nonexistent"
    roles = ["admin"]
    mock_result = MagicMock()
    mock_result.single.return_value = None
    mock_db_session.run.return_value = mock_result

    with pytest.raises(UserNotFoundError) as exc_info:
        add_roles_to_user(username, roles)

    assert exc_info.value.detail == f"User '{username}' not found."


def test_add_roles_to_user_database_error(mock_db_session):
    username = "testuser"
    roles = ["admin"]
    mock_db_session.run.side_effect = Neo4jError("Add roles failed")

    with pytest.raises(DatabaseConnectionError) as exc_info:
        add_roles_to_user(username, roles)

    assert exc_info.value.detail == "Add roles failed"

# Tests for delete_user_by_uuid
def test_delete_user_by_uuid_success(mock_db_session):
    uuid = "unique-uuid-1234"
    mock_record = mock_single_record({"deleted_count": 1})
    mock_result = MagicMock()
    mock_result.single.return_value = mock_record
    mock_db_session.run.return_value = mock_result

    result = delete_user_by_uuid(uuid)

    assert result is True

def test_delete_user_by_uuid_not_found(mock_db_session):
    uuid = "nonexistent-uuid"
    mock_record = mock_single_record({"deleted_count": 0})
    mock_result = MagicMock()
    mock_result.single.return_value = mock_record
    mock_db_session.run.return_value = mock_result

    result = delete_user_by_uuid(uuid)

    assert result is False

def test_delete_user_by_uuid_database_error(mock_db_session):
    uuid = "unique-uuid-1234"
    mock_db_session.run.side_effect = Neo4jError("Deletion failed")

    result = delete_user_by_uuid(uuid)

    assert result is False

# Tests for delete_user
def test_delete_user_success(mock_db_session):
    username = "testuser"
    mock_record = mock_single_record({"deleted_count": 1})
    mock_result = MagicMock()
    mock_result.single.return_value = mock_record
    mock_db_session.run.return_value = mock_result

    result = delete_user(username)

    assert result is True

def test_delete_user_not_found(mock_db_session):
    username = "nonexistent"
    mock_record = mock_single_record({"deleted_count": 0})
    mock_result = MagicMock()
    mock_result.single.return_value = mock_record
    mock_db_session.run.return_value = mock_result

    result = delete_user(username)

    assert result is False

def test_delete_user_database_error(mock_db_session):
    username = "testuser"
    mock_db_session.run.side_effect = Neo4jError("Deletion failed")

    result = delete_user(username)

    assert result is False

# Tests for authenticate_user
def test_authenticate_user_success(mock_db_session):
    username = "testuser"
    password = "securepassword"
    hashed_password = hash_password(password)
    mock_record_data = {
        'username': username,
        'password': hashed_password,
        'uuid': '1234-5678',
        'email': 'test@example.com',
        'name': 'Test User',
        'disabled': False,
        'datecreated': '2023-01-01T00:00:00'
    }
    mock_record = mock_single_record({'u': mock_record_data})
    mock_result = MagicMock()
    mock_result.single.return_value = mock_record
    mock_db_session.run.return_value = mock_result

    user = authenticate_user(username, password)

    assert user is not None
    assert isinstance(user, User)
    assert user.username == username

def test_authenticate_user_incorrect_password(mock_db_session):
    username = "testuser"
    password = "securepassword"
    wrong_password = "wrongpassword"
    hashed_password = hash_password(password)
    mock_record_data = {
        'username': username,
        'password': hashed_password,
        'uuid': '1234-5678',
        'email': 'test@example.com',
        'name': 'Test User',
        'disabled': False,
        'datecreated': '2023-01-01T00:00:00'
    }
    mock_record = mock_single_record({'u': mock_record_data})
    mock_result = MagicMock()
    mock_result.single.return_value = mock_record
    mock_db_session.run.return_value = mock_result

    user = authenticate_user(username, wrong_password)

    assert user is None

def test_authenticate_user_user_not_found(mock_db_session):
    username = "nonexistent"
    password = "any_password"
    mock_result = MagicMock()
    mock_result.single.return_value = None
    mock_db_session.run.return_value = mock_result

    user = authenticate_user(username, password)

    assert user is None

def test_authenticate_user_database_error(mock_db_session):
    username = "testuser"
    password = "securepassword"
    mock_db_session.run.side_effect = Neo4jError("Connection failed")

    with pytest.raises(DatabaseConnectionError):
        authenticate_user(username, password)
