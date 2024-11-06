# backend/routes/auth.py

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
import logging

from backend.schemas.token import Token
from backend.services.user_service import authenticate_user
from backend.dependencies.auth import create_access_token
from backend.config import CurrentConfig

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post(
    "/token",
    response_model=Token,
    description="Authenticate user and return an access token",
    summary="Obtain Access Token",
    tags=["Authentication"]
)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    Authenticate a user and return an access token.

    Args:
        form_data (OAuth2PasswordRequestForm): The form data containing username and password.

    Returns:
        Token: A dictionary containing the access token and token type.

    Raises:
        HTTPException: If authentication fails.
    """
    logger.info(f"Attempting to authenticate user: {form_data.username}")
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        logger.warning(f"Authentication failed for user: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=CurrentConfig.API_ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires
    )
    logger.info(f"Authentication successful for user: {form_data.username}")
    return {"access_token": access_token, "token_type": "bearer"}
