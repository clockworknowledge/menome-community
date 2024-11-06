# backend/dependencies/auth.py

"""
This module handles authentication-related dependencies for the API.

It includes functions for password hashing, token creation, user authentication,
and user retrieval. The module uses JWT for token-based authentication.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from backend.schemas.user import User
from backend.services.user_service import get_user_from_db
from backend.config import CurrentConfig

logger = logging.getLogger(__name__)

# Initialize with a placeholder, it will be replaced in main.py
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password.

    Args:
        plain_password (str): The plain text password to verify.
        hashed_password (str): The hashed password to compare against.

    Returns:
        bool: True if the password is correct, False otherwise.
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a new JWT access token.

    Args:
        data (dict): The data to encode in the token.
        expires_delta (timedelta, optional): The expiration time for the token.

    Returns:
        str: The encoded JWT token.
    """
    to_encode = data.copy()
    now = datetime.utcnow()
    
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=15)
    
    logger.info(f"Creating access token at {now.isoformat()} with expiration at {expire.isoformat()}")
    
    # Convert expire to Unix timestamp
    to_encode.update({"exp": expire.timestamp()})
    encoded_jwt = jwt.encode(to_encode, CurrentConfig.SECRET_KEY, algorithm=CurrentConfig.ALGORITHM)
    
    logger.debug(f"Encoded JWT: {encoded_jwt}")
    
    return encoded_jwt


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
        return user
    logger.warning(f"Authentication failed for user '{username}'.")
    return None


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """
    Get the current authenticated user based on the provided token.

    Args:
        token (str): The JWT token to validate.

    Returns:
        User: The current authenticated user.

    Raises:
        HTTPException: If the token is invalid or the user cannot be found.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        now = datetime.now(timezone.utc)
        payload = jwt.decode(token, CurrentConfig.SECRET_KEY, algorithms=[CurrentConfig.ALGORITHM])
        
        logger.info(f"Validating token at {now.isoformat()}")
        logger.debug(f"Token payload: {payload}")
        
        exp = payload.get("exp")
        if exp:
            expiration_time = datetime.fromtimestamp(exp, tz=timezone.utc)
            logger.info(f"Token expiration time: {expiration_time.isoformat()}")
        
        username: str = payload.get("sub")
        if username is None:
            logger.error("Token payload does not contain 'sub'.")
            raise credentials_exception
        
        user = get_user_from_db(username)
        if user is None:
            logger.error(f"User '{username}' not found.")
            raise credentials_exception
    except JWTError as e:
        logger.error(f"JWT decoding failed: {str(e)}")
        raise credentials_exception
    return user


async def get_optional_current_user(token: str = Depends(oauth2_scheme)) -> Optional[User]:
    """
    Get the current user if authenticated, or None if not.

    Args:
        token (str, optional): The JWT token to validate.

    Returns:
        Optional[User]: The current user if authenticated, None otherwise.
    """
    if not token:
        logger.info("No token provided. Returning None for optional user.")
        return None
    try:
        user = await get_current_user(token)
        return user
    except HTTPException:
        logger.warning("Invalid token provided for optional user.")
        return None
