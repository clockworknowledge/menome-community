# backend/routes/user.py

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import JSONResponse
import re
import logging

from backend.dependencies.auth import get_current_user
from backend.schemas.user import User, UserIn, UserRoles
from backend.services.user_service import (
    get_user_from_db,
    create_user,
    add_roles_to_user,
    delete_user_by_uuid,
    delete_user
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Regular expression to validate UUID format
UUID_REGEX = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$"
)

@router.get(
    "/me",
    response_model=User,
    description="Returns the current authenticated user",
    summary="Get Current User",
    tags=["Users"]
)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """
    Retrieve the details of the currently authenticated user.

    Args:
        current_user (User): The authenticated user, injected via dependency.

    Returns:
        User: The current authenticated user's details.
    """
    logger.debug(f"Fetching current user: {current_user.username}")
    return current_user

@router.post(
    "/add-roles",
    response_model=UserRoles,
    description="Assign roles to a specific user",
    summary="Add Roles to User",
    tags=["Users"]
)
async def add_roles(
    user_roles: UserRoles,
    current_user: User = Depends(get_current_user)
):
    """
    Assign specified roles to a user.

    Args:
        user_roles (UserRoles): The username and list of roles to assign.
        current_user (User): The authenticated user performing the operation.

    Returns:
        UserRoles: The updated roles of the user.

    Raises:
        HTTPException: If username or roles are missing, or if the user is not found.
    """
    logger.info(f"Adding roles to user: {user_roles.username}")
    
    # Validate input
    if not user_roles.username or not user_roles.roles:
        logger.warning("Username and roles are required fields.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username and roles are required fields."
        )
    
    # Add roles via service layer
    updated_roles = add_roles_to_user(user_roles.username, user_roles.roles)
    if not updated_roles:
        logger.error(f"User '{user_roles.username}' not found or roles could not be added.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found or roles could not be added."
        )
    
    logger.info(f"Roles added to user '{user_roles.username}': {updated_roles.roles}")
    return updated_roles

@router.post(
    "/create",
    response_model=User,
    description="Create a new user in the database",
    summary="Create User",
    tags=["Users"]
)
async def create_user_endpoint(
    user: UserIn,
    current_user: User = Depends(get_current_user)
):
    """
    Create a new user with the provided details.

    Args:
        user (UserIn): The user information for creation.
        current_user (User): The authenticated user performing the operation.

    Returns:
        User: The created user's details.

    Raises:
        HTTPException: If required fields are missing or user creation fails.
    """
    logger.info(f"Creating user: {user.username}")
    
    # Validate required fields
    if not user.username or not user.email or not user.name:
        logger.warning("Username, Email, and Name are required fields.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username, Email, and Name are required fields."
        )
    
    # Create user via service layer
    created_user = create_user(
        username=user.username,
        password=user.password,
        email=user.email,
        name=user.name,
        uuid=user.uuid
    )
    if not created_user:
        logger.error(f"User creation failed for '{user.username}'.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User creation failed."
        )
    
    logger.info(f"User '{created_user.username}' created successfully.")
    return created_user

@router.delete(
    "/user/{uuid}",
    description="Delete a user by their UUID",
    summary="Delete User by UUID",
    tags=["Users"]
)
async def delete_user_by_uuid_endpoint(
    uuid: str,
    current_user: User = Depends(get_current_user)
):
    """
    Delete a user from the database using their UUID.

    Args:
        uuid (str): The UUID of the user to delete.
        current_user (User): The authenticated user performing the operation.

    Returns:
        JSONResponse: Confirmation of successful deletion.

    Raises:
        HTTPException: If the UUID format is invalid or the user is not found.
    """
    logger.info(f"Deleting user with UUID: {uuid}")
    
    # Validate UUID format
    if not UUID_REGEX.match(uuid):
        logger.warning(f"Invalid UUID format: {uuid}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid UUID format."
        )
    
    # Delete user via service layer
    success = delete_user_by_uuid(uuid)
    if not success:
        logger.error(f"User with UUID '{uuid}' not found or could not be deleted.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found or could not be deleted."
        )
    
    logger.info(f"User with UUID '{uuid}' deleted successfully.")
    return JSONResponse(content={"status": "User deleted successfully"}, status_code=200)

@router.delete(
    "/user/{username}",
    description="Delete a user by their username",
    summary="Delete User by Username",
    tags=["Users"]
)
async def delete_user_by_username_endpoint(
    username: str,
    current_user: User = Depends(get_current_user)
):
    """
    Delete a user from the database using their username.

    Args:
        username (str): The username of the user to delete.
        current_user (User): The authenticated user performing the operation.

    Returns:
        dict: Confirmation of successful deletion.

    Raises:
        HTTPException: If the user is not found.
    """
    logger.info(f"Deleting user with username: {username}")
    
    # Delete user via service layer
    success = delete_user(username)
    if not success:
        logger.error(f"User '{username}' not found or could not be deleted.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found or could not be deleted."
        )
    
    logger.info(f"User '{username}' deleted successfully.")
    return {"status": "User deleted successfully"}
