# app/services/user_service.py
from typing import Optional, List
from neo4j.exceptions import Neo4jError

from datetime import datetime
import logging

from passlib.context import CryptContext

from backend.db.database import db
from backend.schemas.user import UserIn, UserRoles, User
from backend.utilities.date_utils import neo4j_datetime_to_python_datetime
from backend.exceptions.database_exceptions import DatabaseConnectionError, UserNotFoundError, InvalidRoleAssignmentError

logger = logging.getLogger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_user_from_db(username: str) -> Optional[UserIn]:
    """
    Retrieve a user from the database by username.

    Args:
        username (str): The username of the user to retrieve.

    Returns:
        Optional[UserIn]: The user object if found, None otherwise.

    Raises:
        DatabaseConnectionError: If there's an error connecting to the database.
    """
    try:
        with db.get_session() as session:
            result = session.run(
                "MATCH (u:User {username: $username}) RETURN u",
                username=username
            )
            user_data = result.single()

            if user_data:
                user_node = user_data['u']
                date_created_str = str(user_node['datecreated'])
                date_created = neo4j_datetime_to_python_datetime(date_created_str)
                return UserIn(
                    username=user_node['username'],
                    password=user_node['password'],
                    uuid=user_node['uuid'],
                    email=user_node['email'],
                    name=user_node['name'],
                    disabled=user_node['disabled'],
                    datecreated=date_created
                )
            else:
                return None
    except Neo4jError as e:
        logger.error(f"Error fetching user '{username}': {e}")
        raise DatabaseConnectionError(detail=str(e))


def hash_password(password: str) -> str:
    """
    Hashes a plain password using bcrypt.
    """
    return pwd_context.hash(password)


def create_user_from_schema(user: UserIn) -> UserIn:
    return create_user(user.username, user.password, user.email, user.name, user.uuid)

def create_user(username: str, password: str, email: str, name: str, uuid: Optional[str] = None) -> UserIn:
    """
    Creates a user in the Neo4j database.
    """
    hashed_password = hash_password(password)
    try:
        with db.get_session() as session:
            result = session.run("""
                CREATE (u:User {
                    username: $username,
                    email: $email,
                    name: $name,
                    password: $password,
                    disabled: false,
                    uuid: CASE WHEN $uuid IS NULL THEN randomUUID() ELSE $uuid END,
                    datecreated: datetime()
                })
                RETURN u
            """, username=username, email=email, name=name, password=hashed_password, uuid=uuid)
            record = result.single()
            if record:
                user_node = record["u"]
                return UserIn(
                    uuid=user_node.get("uuid"),
                    username=user_node.get("username"),
                    email=user_node.get("email"),
                    name=user_node.get("name"),
                    disabled=user_node.get("disabled"),
                    password=user_node.get("password"),
                    datecreated=neo4j_datetime_to_python_datetime(str(user_node.get("datecreated")))
                )
    except Exception as e:
        logger.error(f"Error creating user '{username}': {e}")
        raise e


def add_roles_to_user(username: str, roles: List[str]) -> Optional[UserRoles]:
    """
    Add roles to a user in the database.

    Args:
        username (str): The username of the user to add roles to.
        roles (List[str]): A list of role names to add to the user.

    Returns:
        Optional[UserRoles]: The updated user roles if successful, None otherwise.

    Raises:
        InvalidRoleAssignmentError: If no roles are provided.
    """
    if not roles:
        logger.warning(f"No roles provided to add for user '{username}'.")
        raise InvalidRoleAssignmentError(detail="At least one role must be assigned")
    logger.info(f"Adding roles to user '{username}': {roles}")
    # log roles out to console
    logger.info(f"Roles: {roles}")
    try:
        with db.get_session() as session:
            result = session.run("""
                MATCH (u:User {username: $username})
                UNWIND $roles AS role
                MATCH (r:Role {name: role})
                MERGE (u)-[:HAS_ROLE]->(r)
                RETURN u.username AS username, COLLECT(r.name) AS roles
            """, username=username, roles=roles)
            
            record = result.single()
            if record:
                return UserRoles(username=record["username"], roles=record["roles"])
            else:
                logger.warning(f"User '{username}' not found when adding roles.")
                raise UserNotFoundError(detail=f"User '{username}' not found.")
    except Neo4jError as e:
        logger.error(f"Error adding roles to user '{username}': {e}")
        raise DatabaseConnectionError(detail=str(e))

def delete_user_by_uuid(uuid: str) -> bool:
    """
    Delete a user from the database by UUID.

    Args:
        uuid (str): The UUID of the user to delete.

    Returns:
        bool: True if the user was successfully deleted, False otherwise.
    """
    try:
        with db.get_session() as session:
            result = session.run("""
                MATCH (u:User {uuid: $uuid})
                DELETE u
                RETURN COUNT(u) AS deleted_count
            """, uuid=uuid)
            
            record = result.single()
            return record["deleted_count"] > 0
    except Neo4jError as e:
        logger.error(f"Error deleting user with UUID '{uuid}': {e}")
    return False

def delete_user(username: str) -> bool:
    """
    Deletes a user from the Neo4j database.
    """
    try:
        with db.get_session() as session:
            result = session.run("""
                MATCH (u:User {username: $username})
                DETACH DELETE u
                RETURN COUNT(u) AS deleted_count
            """, username=username)
            record = result.single()
            if record and record["deleted_count"] > 0:
                logger.info(f"User '{username}' deleted successfully.")
                return True
            else:
                logger.warning(f"User '{username}' not found for deletion.")
                return False
    except Exception as e:
        logger.error(f"Error deleting user '{username}': {e}")
        return False

def authenticate_user(username: str, password: str) -> Optional[User]:
    """
    Authenticate a user based on username and password.

    Args:
        username (str): The username of the user to authenticate.
        password (str): The password of the user to authenticate.

    Returns:
        Optional[User]: The authenticated user object if successful, None otherwise.
    """
    user = get_user_from_db(username)
    if user and verify_password(password, user.password):
        logger.info(f"User '{username}' authenticated successfully.")
        return User(
            uuid=user.uuid,
            username=user.username,
            email=user.email,
            name=user.name,
            disabled=user.disabled,
            datecreated=user.datecreated
        )
    logger.warning(f"Authentication failed for user '{username}'.")
    return None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password.

    Args:
        plain_password (str): The plain text password to verify.
        hashed_password (str): The hashed password to compare against.

    Returns:
        bool: True if the password is correct, False otherwise.
    """
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    return pwd_context.verify(plain_password, hashed_password)

