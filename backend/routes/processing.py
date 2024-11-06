"""
This module contains routes and functions for processing documents and managing authentication.

Key components:
- Authentication routes and functions
- Document processing routes
- User management
- Token generation and verification

Dependencies:
- FastAPI
- Neo4j
- Celery
- Pydantic
- Python-Jose
- Passlib

The module uses environment variables managed through the CurrentConfig class.

Routes:
- /token: For user authentication and token generation
- (Other routes to be implemented for document processing)

Functions:
- verify_password: Verifies a plain password against a hashed password
- create_access_token: Creates a JWT access token
- authenticate_user: Authenticates a user based on username and password

Models:
- Token: Pydantic model for access tokens
- User: Imported from models, represents a user in the system
- UserIn: Imported from models, represents user input data

Configuration:
- AppConfig: Imported from config, manages environment variables and configuration settings

Note: This module integrates with Celery tasks for document processing and context generation.
"""

import uuid
from fastapi import APIRouter, Query, Depends
from fastapi import Depends, HTTPException, status, APIRouter
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from neo4j import GraphDatabase  # Import Neo4j driver
import logging
from datetime import datetime,  timedelta

from backend.routes.user import get_user_from_db
from backend.worker.tasks import process_text_task
from backend.worker.tasks import generate_category_task
from backend.config import CurrentConfig as AppConfig
from backend.utilities.date_utils import neo4j_datetime_to_python_datetime  
from backend.schemas import User,UserIn  # Import your User model
from backend.worker.task_management import get_task_info, purge_celery_queue

# Initialize environment variables if needed
AppConfig.initialize_environment_variables()


class Token(BaseModel):
    access_token: str
    token_type: str

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Verify hashed password
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

# Create an access token
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, AppConfig.SECRET_KEY, algorithm=AppConfig.ALGORITHM)
    return encoded_jwt

# Authenticate a user (This function might need the get_user_from_db function, which should be imported from user_management.py)
def authenticate_user(username: str, password: str):
    user = get_user_from_db(username)
    if user and verify_password(password, user.password):
        return user
    return None


    
# Define the dependency function to get the current user
async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, AppConfig.SECRET_KEY, algorithms=[AppConfig.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception

        user = get_user_from_db(username)
        if user is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    return user


router = APIRouter()


from fastapi import APIRouter, Query, Depends

router = APIRouter()

# Batch process documents into chunks
# This endpoint will query the database for documents that have not been processed yet
# and queue them for processing. It will return a list of task IDs that can be used to
# check the status of the processing tasks.
@router.post("/documents", 
             summary="Processes documents into chunks",
             description="Processes documents into chunks",
             tags=["Processing"])
async def process_documents(
    
    document_limit: int = Query(default=None, description="Limit on number of documents to process"),
    generateQuestions: bool = Query(default=False, description="Flag to generate questions"),
    generateSummaries: bool = Query(default=False, description="Flag to generate summaries"),
    generateContext: bool = Query(default=False, description="Flag to generate context"),
    current_user: User = Depends(get_current_user)):
    logging.basicConfig(level=logging.INFO)
    
    # Assuming you have a Neo4j driver instance
    driver = GraphDatabase.driver(AppConfig.NEO4J_URI, auth=(AppConfig.NEO4J_USER, AppConfig.NEO4J_PASSWORD))

    query = "MATCH (a:Document) WHERE NOT (a)-[:HAS_PAGE]->(:Page) and a.text <> '' RETURN a.uuid as uuid"
    if document_limit is not None:
        query += f" LIMIT {document_limit}"
    
    logging.info("Querying for documents to process.")
    document_ids = []
    with driver.session() as session:
        result = session.run(query)
        document_ids = [record['uuid'] for record in result]

    logging.info(f"Found {len(document_ids)} documents to process.")
    
    task_ids = []
    for document_id in document_ids:
        try:
            logging.info(f"Queueing document {document_id} for processing.")
            with driver.session() as session:
                result = session.run("MATCH (a:Document {uuid: $uuid}) RETURN a", {"uuid": document_id})
                document_data = result.single().value()
                text = document_data['text']
                # Pass the generateQuestions and generateSummaries flags to the task
                task = process_text_task.delay(text, document_id, generateQuestions, generateSummaries, generateContext)
                task_ids.append(task.id)
                logging.info(f"Queued document {document_id} with task ID {task.id}")
        except Exception as e:
            logging.error(f"Failed to queue document {document_id}: {e}")
        finally:
            driver.close()
    
    return {
        "message": f"Processing started for {len(document_ids)} documents",
        "task_ids": task_ids
    }


# Process a single document into chunks
# This endpoint will take a document ID and process it into chunks.
@router.post("/document/{document_id}",
             summary="Processes single document into chunks",
             description="Takes the document id and processes it into chunks",
             tags=["Processing"]
             )
async def process_single_document_endpoint(
    document_id: str, 
    current_user: User = Depends(get_current_user)
):
    # Assuming you have a Neo4j driver instance
    driver = GraphDatabase.driver(AppConfig.NEO4J_URI, auth=(AppConfig.NEO4J_USER, AppConfig.NEO4J_PASSWORD))
    try:
        task_ids = []
        logging.info(f"Queueing document {document_id} for processing.")
        with driver.session() as session:
            result = session.run("MATCH (a:Document {uuid: $uuid}) RETURN a", {"uuid": document_id})
            document_data = result.single().value()
            text = document_data['text']
            # Pass the generateQuestions and generateSummaries flags to the task
            task = process_text_task.delay(text, document_id, True, True, True)
            task_ids.append(task.id)
            logging.info(f"Queued document {document_id} with task ID {task.id}")
    except Exception as e:
        logging.error(f"Failed to queue document {document_id}: {e}")
    finally:
        driver.close()

    return {
        "message": f"Processing started for {len(document_id)} documents",
        "task_ids": task_ids
    }


# Generate context for a document
# This endpoint will take a document ID and generate context for it.
# output will be a series of message-server messages that will be sent to
# the menome message server for processing into the context graph. 
@router.post("/documents/categories",
             summary="Generates categories for documents",
             description="Generates categories for specified number of documents without context",
             tags=["Processing"]
             )
async def get(document_limit: int = Query(default=None, description="Limit on number of documents to process"),
              text_length: int = Query(default=200, description="Minimum length of text to process"),
              current_user: User = Depends(get_current_user)):
    # Assuming you have a Neo4j driver instance
    driver = GraphDatabase.driver(AppConfig.NEO4J_URI, auth=(AppConfig.NEO4J_USER, AppConfig.NEO4J_PASSWORD))
    try:
        task_ids = []
        logging.info("Querying for documents to process.")
        query = "match (d:Document)-[]-(p:Page) where (size(d.text) > $text_length and d.type<>'Note') and  not (d)-[:MENTIONS]->(:Category) return d.uuid as uuid "
        if document_limit is not None:
            query += f" LIMIT {document_limit}"

        document_ids = []    
        
        with driver.session() as session:
            result = session.run(query, {"text_length": text_length})
            document_ids = [record['uuid'] for record in result]
    except Exception as e:
        logging.error(f"Exception querying for documents: {e}")
    finally:
        driver.close()

    logging.info(f"Found {len(document_ids)} documents to process.")
    
    task_ids = []
    for document_id in document_ids:
        try:
            logging.info(f"Queueing document {document_id} for processing.")
            
             
            # Pass the generateQuestions and generateSummaries flags to the task
            task = generate_category_task.delay(document_id  )
            task_ids.append(task.id)
            logging.info(f"Queued document {document_id} with task ID {task.id}")
        except Exception as e:
            logging.error(f"Failed to queue document {document_id}: {e}")
  
    return {
        "message": f"Processing started for {len(document_ids)} documents",
        "task_ids": task_ids
    }


# Generate context for a document
# This endpoint will take a document ID and generate context for it.
# output will be a series of message-server messages that will be sent to
# the menome message server for processing into the context graph. 
@router.post("/documents/categories/{document_id}",
             summary="Generates categories for the document",
             description="Takes the document id and processes it into chunks",
             tags=["Processing"]
             )
async def get(document_id: str, current_user: User = Depends(get_current_user)):
    # Assuming you have a Neo4j driver instance
    driver = GraphDatabase.driver(AppConfig.NEO4J_URI, auth=(AppConfig.NEO4J_USER, AppConfig.NEO4J_PASSWORD))
    try:
        task_ids = []
        logging.info(f"Generating context for document {document_id}.")
        with driver.session() as session:
            result = session.run("MATCH (a:Document {uuid: $uuid}) RETURN a", {"uuid": document_id})
            document_data = result.single().value()
            if document_data is None:
                raise HTTPException(status_code=404, detail="Document not found")
            
            text = document_data['text']
            
            # Pass the generateQuestions and generateSummaries flags to the task
            task = generate_category_task.delay(document_id)
            #test_generate_context_task(document_id)
            task_ids.append(task.id)
            logging.info(f"Queued document {document_id} with task ID {task.id}")
    except Exception as e:
        logging.error(f"Failed to queue document {document_id}: {e}")
    finally:
        driver.close()

    return {
    "message": f"Processing started for {document_id} document",
    "task_ids": task_ids
}


@router.get("/task/{task_id}",
            summary="Get task status",
            description="Return the status of a submitted task",
            response_description="Task status information",
            tags= ["Celery Queue Management"])
async def get_task_status(task_id: str,  current_user: User = Depends(get_current_user)): 
    """
    Get the status of a submitted Celery task.

    This endpoint retrieves the current status of a task in the Celery queue.
    It requires authentication and accepts a task ID as a path parameter.

    Args:
        task_id (str): The unique identifier of the task.
        current_user (User): The authenticated user making the request.

    Returns:
        dict: A dictionary containing task status information.

    Raises:
        HTTPException: If the user is not authenticated or the task is not found.
    """
    return get_task_info(task_id)


@router.post("/purge-queue", tags=["Celery Queue Management"])
async def purge_queue(current_user: User = Depends(get_current_user)):
    """
    Purge all tasks in the Celery queue.

    This endpoint removes all pending tasks from the Celery queue.
    It is only accessible to authenticated users with appropriate permissions.

    Args:
        current_user (User): The authenticated user making the request.

    Returns:
        dict: A dictionary containing the status of the operation and a message.

    Raises:
        HTTPException: If the user is not authorized to purge the queue.
    """
    if not current_user:  # Add your own authentication checks
        raise HTTPException(status_code=403, detail="Not authorized to purge queue")

    try:
        purge_celery_queue()
        return {"status": "success", "message": "Celery queue purged successfully"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

