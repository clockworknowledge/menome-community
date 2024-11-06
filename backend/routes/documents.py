from fastapi import APIRouter, Depends, HTTPException, Query, Path
from fastapi.security import OAuth2PasswordBearer
from typing import List, Optional
from datetime import datetime, timedelta, timezone 
import uuid
import httpx
from neo4j import GraphDatabase
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import logging
import secrets
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import BaseModel, HttpUrl

from backend.config import CurrentConfig
from backend.dependencies.auth import get_current_user, get_optional_current_user
from backend.schemas import User, DocumentRequest
from backend.services.document_services import (
    get_token_metadata, invalidate_token,
    get_document_by_uuid,  generate_shareable_link
)
from backend.services.similarity_services import is_blocker_signal
from backend.services.document_formatting_services import (
    extract_title, extract_primary_image, extract_publisher, extract_thumbnail, extract_full_text,
    reformat_document_to_markdown, reformat_document_to_html
)
from backend.worker.tasks import process_text_task


router = APIRouter()

# Setup logging
logging.basicConfig(level=logging.INFO)

"""
This module contains routes for document-related operations.

Routes:
- POST /add-document-from-url: Add a document to the graph from a specified URL
- POST /generate-share-link/{document_uuid}: Generate a shareable link for a document
- GET /documents/{uuid}: Retrieve a document by its UUID

Each route is documented with its purpose, parameters, and return values.
"""

@router.post("/document/add-document-from-url",
             summary="Allows for adding a document to the graph from specified URL",
             description="Take the specified uri and add the document to the graph using beautiful soup to extract the content",
             tags=["Documents"])
async def add_document(request: DocumentRequest, current_user: User = Depends(get_current_user)):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.140 Safari/537.36 Edge/17.17134"
    }
    # Convert request.url to a string
    url_str = str(request.url)
    logging.info(f"Fetching document from {url_str}")
    driver = GraphDatabase.driver(CurrentConfig.NEO4J_URI, auth=(CurrentConfig.NEO4J_USER, CurrentConfig.NEO4J_PASSWORD)) 

    async with httpx.AsyncClient() as client:
        response = await client.get(url_str, headers=headers)
    soup = BeautifulSoup(response.content, 'html.parser')

    documentId = str(uuid.uuid4())
    title = extract_title(soup, documentId)
    text = extract_full_text(soup)
    imageurl = extract_primary_image(soup)
    publisher = extract_publisher(soup, url_str)
    thumbnail = extract_thumbnail(soup)
    wordcount = len(text.split())
    note = request.note
    logging.info(f"Document {documentId} has {wordcount} words")
    utc_now = datetime.utcnow().strftime('%Y-%m-%dT%H:%M') + 'Z'
    
    # check if there is a blocker for this url - if so, return an error - typically blocker text is less than 100 characters
    if len(text) < 100:
        blocker = is_blocker_signal(text, CurrentConfig.BLOCKER_JSON_PATH, 0.6)
        if blocker:
            raise HTTPException(status_code=400, detail=f"Blocker found for this url: {blocker}")
        
    
    # Check if the document already exists using similarity search



    query = """
    CREATE (d:Document {
        uuid: $uuid,
        name: $name,
        url: $url,
        text: $text,
        note: $note,
        imageurl: $imageurl,
        publisher: $publisher,
        addeddate: $addeddate,
        thumbnail: $thumbnail,
        wordcount: $wordcount,
        type: "Document"
    })
    WITH d
    MATCH (u:User {uuid: $useruuid})
    MERGE (ua:UserAction {useruuid: u.uuid}) 
    ON CREATE SET ua.name = u.username, ua.uuid = randomUUID()
    MERGE (u)-[r:HAS_ACTION]->(ua)
    MERGE (ua)-[:ADDED]->(d) SET r.dateadded = datetime()
    """
    try:
        with driver.session() as session:
            session.run(query, {
                "uuid": documentId,
                "name": title,
                "url": url_str,  # Use the string URL here
                "text": text,
                "note": note,
                "imageurl": imageurl,
                "publisher": publisher,
                "addeddate": utc_now,
                "thumbnail": thumbnail,
                "wordcount": wordcount,
                "useruuid": current_user.uuid
            })
    except Exception as e:
        logging.error(f"Error adding document to database: {e}")
        raise HTTPException(status_code=500, detail=f"Error adding document to database: {e}")
    finally:
        driver.close()

    try:
        task_ids = []
        logging.info(f"Queueing document {documentId} for processing.")
        with driver.session() as session:
            result = session.run("MATCH (a:Document {uuid: $uuid}) RETURN a", {"uuid": documentId})
            document_data = result.single().value()
            text = document_data['text']
            task = process_text_task.delay(text, documentId, True, True, True)
            task_ids.append(task.id)
            logging.info(f"Queued document {documentId} with task ID {task.id}")
            shareable_link=generate_shareable_link(documentId, 'html', current_user.uuid, driver)
    except Exception as e:
        logging.error(f"Failed to queue document {documentId}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to queue document {documentId}: {e}")
    finally:
        driver.close()

    return {
        "documentId": documentId,
        "shareable_link": shareable_link,
        "message": f"Processing started for document {documentId}",
        "task_ids": task_ids
    }


@router.post("/document/generate-share-link/{document_uuid}",
             summary="Allows user to generate a shareable link to a document",
             tags=["Documents"]
             )
async def generate_share_link(document_uuid: str,
                               format_type: str = Query('json', title="The format type to return", enum=["json", "markdown", "html"]),
                               current_user: User = Depends(get_current_user)):
    """
    Generate a shareable link for a document.

    Args:
        document_uuid (str): The UUID of the document to share.
        format_type (str): The format type for the shared document (json, markdown, or html).
        current_user (User): The authenticated user making the request.

    Returns:
        dict: A dictionary containing the shareable link.

    Raises:
        HTTPException: If there's an error generating the shareable link.
    """
    driver = GraphDatabase.driver(CurrentConfig.NEO4J_URI, auth=(CurrentConfig.NEO4J_USER, CurrentConfig.NEO4J_PASSWORD))
    try:
       shareable_link = generate_shareable_link(document_uuid, format_type, current_user.uuid, driver)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save token metadata: {str(e)}")
    finally:
        driver.close()
    
    return {"shareable_link": shareable_link}

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

@router.get("/document/{uuid}", summary="Get a document by UUID", tags=["Documents"])
async def get_document(
    uuid: str = Path(..., title="The UUID of the document to retrieve"),
    token: Optional[str] = Query(None),
    format_type: str = Query('json', title="The format type to return", enum=["json", "markdown", "html"]),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """
    Retrieve a document by its UUID.

    Args:
        uuid (str): The UUID of the document to retrieve.
        token (Optional[str]): An optional access token for authentication.
        format_type (str): The format type for the returned document (json, markdown, or html).
        current_user (Optional[User]): The authenticated user making the request (if any).

    Returns:
        Union[dict, PlainTextResponse, HTMLResponse]: The requested document in the specified format.

    Raises:
        HTTPException: If the token is invalid, expired, or doesn't match the document,
                       or if the user is not authenticated, or if the document is not found.
    """
    driver = GraphDatabase.driver(CurrentConfig.NEO4J_URI, auth=(CurrentConfig.NEO4J_USER, CurrentConfig.NEO4J_PASSWORD))
    try:
        if token:
            token_metadata = get_token_metadata(token, driver)
            
            # Check if token metadata is valid, return immediately if not
            if not token_metadata:
                raise HTTPException(status_code=403, detail="Invalid token")
            
            current_time = datetime.now(timezone.utc)
            
            # Ensure expiry is a datetime object and timezone-aware
            expiry = token_metadata['expiry'].replace(tzinfo=timezone.utc) if token_metadata else None
            logging.info(f"Token metadata: {token_metadata}")
            logging.info(f"Current time: {current_time}")
            logging.info(f"Expiry: {expiry}")
            logging.info(f"UUID comparison: {token_metadata['document_uuid']} == {uuid}")


            if token_metadata['document_uuid'] != uuid:
                raise HTTPException(status_code=403, detail="Token does not match document")
            if expiry < current_time:
                raise HTTPException(status_code=403, detail="Expired token")
            if token_metadata.get('invalid', False):
                raise HTTPException(status_code=403, detail="Invalid token")
            
            # Invalidate the token if it's a one-time use token
            if CurrentConfig.INVALIDATE_TOKEN_AFTER_USE:
                invalidate_token(token, driver)
        elif not current_user:
            raise HTTPException(status_code=401, detail="Not authenticated")

        document = get_document_by_uuid(uuid, driver)
        if document is None:
            raise HTTPException(status_code=404, detail="Document not found")


        if format_type == 'markdown':
            formatted_document = reformat_document_to_markdown(document)
            return PlainTextResponse(content=formatted_document)
        elif format_type == 'html':
            formatted_document = reformat_document_to_html(document)
            return HTMLResponse(content=formatted_document)
        else:
            return document

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
    finally:
        driver.close()

class DocumentRequest(BaseModel):
    url: HttpUrl
    note: str

