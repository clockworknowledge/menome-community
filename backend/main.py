# backend/main.py

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from typing import Optional

from backend.schemas.user import User
from backend.routes import api_router  # Centralized router
from backend.dependencies.auth import get_optional_current_user, oauth2_scheme

import os
from fastapi.openapi.utils import get_openapi

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Determine environment mode
env_mode = os.getenv("ENV_MODE", "development")

# Conditional root_path setting
root_path = "/api" if env_mode == "production" else ""
logger.info(f"Environment mode: {env_mode}")
logger.info(f"Root path set to: '{root_path}'")

# Initialize FastAPI with conditional root_path
app = FastAPI(root_path=root_path)
logger.info(f"FastAPI initialized with root_path: '{root_path}'")

# Read environment variables for CORS
FRONTEND_ORIGIN_DEV = os.getenv('FRONTEND_ORIGIN_DEV', default='http://localhost:3000')
FRONTEND_ORIGIN_PROD = os.getenv('FRONTEND_ORIGIN_PROD', default='https://thelink.menome.com')

# Define allowed origins
origins = [
    FRONTEND_ORIGIN_DEV,
    FRONTEND_ORIGIN_PROD,
    "https://chat.openai.com/"
]
logger.info(f"CORS origins set: {origins}")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
logger.info("CORS middleware added to the application")

# Create a new OAuth2PasswordBearer with the correct tokenUrl
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{root_path}/auth/token")
logger.info(f"OAuth2PasswordBearer initialized with tokenUrl: '{root_path}/auth/token'")

# Update the auth dependency to use the new oauth2_scheme
from backend.dependencies import auth
auth.oauth2_scheme = oauth2_scheme
logger.info("Auth dependency updated with new OAuth2PasswordBearer")

# Include the centralized API router
app.include_router(api_router)
logger.info("Centralized API router included in the application")

@app.get("/")
def read_root():
    return {
        "message": """Greetings and welcome to the Menome Personal Knowledge API! 
        The objective is to provide a flexible and extensible system that leverages AI to capture, curate, and manage personal knowledge.
        Documentation is available at https://github.com/clockworknowledge/menome-community
        """,
    }

# Custom OpenAPI schema to ensure correct `tokenUrl` and `servers`
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="clockworKnowledge Menome API",
        version="1.0.0",
        description="",
        routes=app.routes,
    )

    # Add server details
    openapi_schema["servers"] = [{"url": root_path}]

    # Add OAuth2 security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "OAuth2PasswordBearer": {
            "type": "oauth2",
            "flows": {
                "password": {
                    "tokenUrl": f"{root_path}/auth/token",
                    "scopes": {}
                }
            }
        }
    }

    # Apply the security scheme globally
    openapi_schema["security"] = [{"OAuth2PasswordBearer": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi


