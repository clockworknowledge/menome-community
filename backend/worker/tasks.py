"""
This module contains Celery tasks for processing documents and generating context.

Key components:
- Celery app configuration
- Document processing tasks
- Context generation tasks
- Helper functions for task management and queue operations

Dependencies:
- Celery
- Neo4j
- OpenAI
- LangChain
- RabbitMQ

Environment variables are managed through the CurrentConfig class.
"""

from celery import Celery
from celery.result import AsyncResult

from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError

from langchain_openai.embeddings import OpenAIEmbeddings
from langchain.text_splitter import TokenTextSplitter
from langchain.document_loaders import telegram
from langchain_openai import ChatOpenAI

from langchain_community.document_loaders import Docx2txtLoader
from langchain_experimental.text_splitter import SemanticChunker


from langchain_openai import ChatOpenAI
from langchain_core.documents import Document
from langchain_community.graphs import Neo4jGraph

import uuid
import logging
from typing import List
import time
import threading
from datetime import datetime
import os

from spire.doc import *
from spire.doc.common import *

from backend.services.processing_services import generate_questions, generate_summaries
from backend.config import CurrentConfig

from backend.worker.task_management import create_celery_app
from backend.services.file_services import process_document_chunks
from backend.worker.task_process_text_logic import process_text_logic

# Initialize environment variables if needed
CurrentConfig.initialize_environment_variables()
logging.info(f"Starting worker")
logging.basicConfig(level=CurrentConfig.LOG_LEVEL)

# Assuming you have a global variable to track the number of active tasks
active_tasks_lock = threading.Lock()
active_tasks_count = 0
MAX_CONCURRENT_TASKS = CurrentConfig.MAX_CONCURRENT_TASKS


# Define your broker and result backend URLs
broker_url = CurrentConfig.CELERY_BROKER_URL
result_backend_url = CurrentConfig.CELERY_RESULT_BACKEND_URL

logging.info(f"Starting worker")
logging.info(f"Broker URL: {broker_url}")

# Create the Celery app
celery_app = create_celery_app(broker_url, result_backend_url)
# Set a lower acknowledgment timeout, for example, 300 seconds (5 minutes)
celery_app.conf.broker_transport_options = {'confirm_publish': True, 'acknowledgement_timeout': 300}
# Set heartbeat interval and prefetch count
celery_app.conf.broker_heartbeat = 10  # seconds
celery_app.conf.worker_prefetch_multiplier = 1
celery_app.conf.broker_connection_retry_on_startup = True

# After Celery and config are initialized, adjust the task's rate_limit
from celery.result import AsyncResult
from celery.exceptions import TimeoutError, CeleryError
from celery.app.control import Inspect


## Worker tasks
# Test task
@celery_app.task(name="celery_worker.test_celery")
def divide(x, y):
    """
    A test Celery task that performs division.

    Args:
        x (float): The dividend
        y (float): The divisor

    Returns:
        float: The result of x divided by y

    Note:
        This task includes a 5-second delay to simulate processing time.
    """
    import time
    logging.info("Starting divide task")
    time.sleep(5)
    return x / y

# Celery task for processing text
@celery_app.task(bind=True, rate_limit="1/m", name="celery_worker.process_text_task")
def process_text_task(self, textToProcess: str, documentId: str, generateQuestions: bool, generateSummaries: bool, generateCategory: bool):
    """
    Celery task for processing text documents.

    This task performs the following operations:
    1. Splits the text into semantic chunks
    2. Embeds the chunks using OpenAI embeddings
    3. Stores the document structure in Neo4j
    4. Optionally generates questions, summaries, and context

    Args:
        self: The Celery task instance
        textToProcess (str): The text content to be processed
        documentId (str): Unique identifier for the document
        generateQuestions (bool): Flag to generate questions from the text
        generateSummaries (bool): Flag to generate summaries from the text
        generateCategory (bool): Flag to generate category from the text

    Returns:
        dict: A dictionary containing the task result information

    Raises:
        Exception: For any errors during processing
    """

    return process_text_logic(
        textToProcess,
        documentId,
        generateQuestions,
        generateSummaries,
        generateCategory
    )




# Celery task for generating context
from langchain_openai import ChatOpenAI
from backend.worker.task_category_logic import generate_category_logic

@celery_app.task(bind=True, rate_limit="1/m", name="celery_worker.generate_category_task")
def generate_category_task(self, documentId: str):
    """
    Celery task for generating context from processed documents.

    This task performs the following operations:
    1. Retrieves document chunks from Neo4j
    2. Uses LLM to transform chunks into graph documents
    3. Extracts nodes and relationships
    4. Filters and normalizes category nodes
    5. Commits the resulting graph structure to Neo4j

    Args:
        self: The Celery task instance
        documentId (str): Unique identifier for the document

    Returns:
        dict: A dictionary containing the task result information

    Raises:
        Exception: For any errors during context generation
    """
    logging.info(f"Starting category generation for document {documentId}")
    logging.debug(f"Task details: ID={self.request.id}, Document ID={documentId}")
    self.update_state(state=CurrentConfig.PROCESSING_DOCUMENT, meta={"documentId": documentId})

    global active_tasks_count

    # Task Concurrency Management
    with active_tasks_lock:
        logging.debug(f"Current active tasks: {active_tasks_count}")
        if active_tasks_count >= MAX_CONCURRENT_TASKS:
            logging.debug(f"Max concurrent tasks reached. Retrying in 60 seconds.")
            raise self.retry(countdown=60)  # Retry after 60 seconds

        active_tasks_count += 1
        logging.debug(f"Incremented active tasks count to: {active_tasks_count}")
    
    driver = GraphDatabase.driver(CurrentConfig.CELERY_NEO4_URL, auth=(CurrentConfig.NEO4J_USER, CurrentConfig.NEO4J_PASSWORD))
    logging.debug(f"Neo4j Driver URL: {CurrentConfig.CELERY_NEO4_URL}")

    llm = ChatOpenAI(temperature=0, model=CurrentConfig.OPENAI_EXTRACTION_MODEL, openai_api_key=CurrentConfig.OPENAI_API_KEY)
    logging.debug(f"Initializing ChatOpenAI with model: {CurrentConfig.OPENAI_EXTRACTION_MODEL}")

    logging.info(f"Drivers initiated, calling generate_category_logic for document {documentId}")
    
    try:    
        generate_category_logic(documentId, llm,  driver)
    
    except Exception as e:
        logging.error(f"Failed to process document context {documentId}: {e}")
        logging.debug(f"Exception details: {type(e).__name__}, {str(e)}")
        return {"message": "Failed", "error": str(e)}
    finally:
        with active_tasks_lock:
            active_tasks_count -= 1
            logging.debug(f"Decremented active tasks count to: {active_tasks_count}")
        if driver:
            logging.debug("Closing Neo4j driver connection")
            driver.close()