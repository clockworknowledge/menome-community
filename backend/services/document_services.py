"""
Document Services Module

This module provides functionality for managing document sharing and access control through tokens.
It handles the creation, validation, and management of shareable links and their associated tokens
in a Neo4j database.

Functions:
    get_existing_shareable_link: Retrieves existing valid shareable link for a document
    save_token_metadata: Saves token metadata to Neo4j database
    get_token_metadata: Retrieves token metadata from Neo4j database
    invalidate_token: Removes a token from the database
    get_document_by_uuid: Retrieves a document by its UUID
    generate_shareable_link: Creates a new shareable link for a document
    validate_share_token: Validates a share token for document access
"""

import io
import datetime
import secrets, os
from datetime import datetime, timedelta
from fastapi import HTTPException, status
import logging


from backend.services.similarity_services import is_blocker_signal
from backend.config import CurrentConfig
from datetime import timezone
logger = logging.getLogger(__name__)


def get_existing_shareable_link(document_uuid: str, current_user_uuid: str, driver) -> str:
    """
    Retrieves an existing valid shareable link for a document.

    Args:
        document_uuid (str): UUID of the document
        current_user_uuid (str): UUID of the current user
        driver: Neo4j driver instance

    Returns:
        str: Existing shareable link if found, None otherwise
    """
    query = """
    MATCH (token:ShareToken {document_uuid: $document_uuid, user_uuid: $user_uuid})
    WHERE token.expiry > datetime()
    RETURN token
    """
    with driver.session() as session:
        result = session.run(query, {
            "document_uuid": document_uuid,
            "user_uuid": current_user_uuid
        })
        token_record = result.single()
        if token_record:
            token_data = token_record["token"]
            format_type = token_data.get('format_type', 'markdown')  
            existing_link = f"{CurrentConfig.SITE_URL}{CurrentConfig.ROOT_PATH}/documents/{document_uuid}?token={token_data['token']}&format_type={format_type}"
            logger.debug(f"Existing shareable link found: {existing_link}")
            return existing_link
        logger.debug("No existing shareable link found.")
        return None



def save_token_metadata(token: str, document_uuid: str, expiry: datetime, user_uuid: str, neo4j_driver, format_type: str = "markdown"):
    """
    Saves token metadata to the Neo4j database.

    Args:
        token (str): The token string.
        document_uuid (str): UUID of the associated document.
        expiry (datetime): Expiry datetime (timezone-aware).
        user_uuid (str): UUID of the user.
        neo4j_driver: The Neo4j driver instance.
        format_type (str): The format type for the shareable link.
    """
    create_query = """
        MERGE (d:Document {uuid: $document_uuid})
        CREATE (t:ShareToken {
            token: $token,
            expiry: $expiry,
            document_uuid: $document_uuid,
            user_uuid: $user_uuid,
            format_type: $format_type
        })
        MERGE (u:User {uuid: $user_uuid})
        MERGE (u)-[:GENERATED]->(t)
        MERGE (t)-[:ACCESS_TO]->(d)
        """
    try:
        with neo4j_driver.session() as session:
            session.run(create_query, token=token, document_uuid=document_uuid, user_uuid=user_uuid, expiry=expiry, format_type=format_type)
        logger.debug(f"ShareToken created: {token} for Document: {document_uuid}, User: {user_uuid}, Expiry: {expiry}, Format Type: {format_type}")
    except Exception as e:
        logger.error(f"Error creating ShareToken: {e}")
        raise

def get_token_metadata(token: str, driver):
    """
    Retrieves token metadata from the Neo4j database.

    Args:
        token (str): The token string
        driver: Neo4j driver instance

    Returns:
        dict: Token metadata including expiry and document info, or None if not found
    """
    query = """
    MATCH (t:ShareToken {token: $token})-[:ACCESS_TO]->(d:Document)
    RETURN t.token as token, t.expiry as expiry, t.document_uuid as document_uuid, t.user_uuid as user_uuid
    """
    with driver.session() as session:
        result = session.run(query, {"token": token}).single()
        if result:
            expiry = result["expiry"]
            # Check if expiry is already a datetime object
            if isinstance(expiry, datetime):
                expiry_datetime = expiry
            else:
                # If it's a string, parse it
                expiry_datetime = datetime.fromisoformat(str(expiry))
            return {
                "token": result["token"],
                "expiry": expiry_datetime,
                "document_uuid": result["document_uuid"],
                "user_uuid": result["user_uuid"]
            }
        return None

def invalidate_token(token: str, driver):
    """
    Removes a token from the database.

    Args:
        token (str): The token to invalidate
        driver: Neo4j driver instance
    """
    query = """
    MATCH (t:ShareToken {token: $token})
    DETACH DELETE t
    """
    with driver.session() as session:
        session.run(query, {"token": token})
    


def get_document_by_uuid(uuid: str, driver):
    """
    Retrieves a document by its UUID from the database.

    Args:
        uuid (str): UUID of the document
        driver: Neo4j driver instance

    Returns:
        dict: Document data if found, None otherwise
    """
    with driver.session() as session:
        result = session.run("MATCH (d:Document {uuid: $uuid}) RETURN d", uuid=uuid)
        record = result.single()
        return record['d'] if record else None
    

def generate_shareable_link(document_uuid: str, format_type: str, current_user_uuid: str, driver) -> str:
    """
    Creates a new shareable link for a document.

    Args:
        document_uuid (str): UUID of the document
        format_type (str): Format type for the shared document
        current_user_uuid (str): UUID of the current user
        driver: Neo4j driver instance

    Returns:
        str: Generated shareable link

    Raises:
        HTTPException: If token metadata cannot be saved
    """
    # Check for existing valid shareable link
    existing_link = get_existing_shareable_link(document_uuid, current_user_uuid, driver)
    if existing_link:
        return existing_link

    # Generate a new shareable link
    token = secrets.token_urlsafe(16)
    expiry = datetime.now(timezone.utc) + timedelta(hours=1)  # Token expires in 1 hour

    try:
        save_token_metadata(token, document_uuid, expiry, current_user_uuid, driver)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to save token metadata: {str(e)}")

    shareable_link = f"{CurrentConfig.SITE_URL}{CurrentConfig.ROOT_PATH}/documents/{document_uuid}?token={token}&format_type={format_type}"
    return shareable_link

def validate_share_token(token: str, document_uuid: str, driver):
    """
    Validates a share token for document access.

    Args:
        token (str): Token to validate
        document_uuid (str): UUID of the document
        driver: Neo4j driver instance

    Returns:
        dict: Token metadata if valid

    Raises:
        HTTPException: If token is invalid, expired, or doesn't match document
    """
    token_data = get_token_metadata(token, driver)
    if not token_data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    if token_data['document_uuid'] != document_uuid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token does not match the requested document")

    # Use timezone-aware current datetime in UTC
    current_time = datetime.now(timezone.utc)
    
    if token_data['expiry'] < current_time:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    return token_data

