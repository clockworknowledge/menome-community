"""
This module contains routes and functions for generating research articles based on provided topics.

Key components:
- Research generation route
- Database interactions with Neo4j
- Integration with MasterAgent for research workflow
- Document processing and task management

Dependencies:
- FastAPI
- Neo4j
- Celery
- Pydantic
- UUID

The module uses environment variables managed through the CurrentConfig class.

Routes:
- /research-topic: Generates a research article based on provided topics

Functions:
- generate_research: Main function to handle research generation request

Models:
- GenerateResearchRequest: Pydantic model for research generation request
- User: Represents the authenticated user

Configuration:
- CurrentConfig: Manages environment variables and configuration settings

Note: This module integrates with Celery tasks for document processing and uses Neo4j for data storage.
"""

from fastapi import APIRouter, Query, Depends
from fastapi import Depends, HTTPException, status, APIRouter

from neo4j import GraphDatabase
from datetime import datetime
import uuid
import logging
import traceback
from fastapi.responses import JSONResponse

from backend.routes.researcher_agent import MasterAgent
from backend.schemas import GenerateResearchRequest, User
from backend.dependencies.auth import get_current_user
from backend.config import CurrentConfig
from backend.routes.processing import process_documents, process_text_task
from backend.services.document_services import generate_shareable_link

router = APIRouter()

@router.post('/research-topic',
             summary="Generate a research article based on provided topics",
             tags=["Research"]
             )
async def generate_research(request_body: GenerateResearchRequest,
    current_user: User = Depends(get_current_user)                         
    ):
    """
    Generate a research article based on provided topics and layout.

    This function handles the entire process of research generation, including:
    1. Creating a new research document in the database
    2. Running the MasterAgent to generate research content
    3. Processing related documents
    4. Generating shareable links
    5. Queuing text processing tasks

    Args:
        request_body (GenerateResearchRequest): The request body containing research topics
        current_user (User): The authenticated user making the request

    Returns:
        dict: A dictionary containing:
            - research_document: The main research document
            - topic_research: Additional topic-specific research
            - sources: List of source documents used in the research
            - shareable_links: List of shareable links for the documents
            - task_ids: List of queued task IDs for text processing
            - message: Status message

    Raises:
        HTTPException: If there's an error during the research generation process
    """
    logging.basicConfig(level=logging.INFO)
    driver = GraphDatabase.driver(CurrentConfig.NEO4J_URI, auth=(CurrentConfig.NEO4J_USER, CurrentConfig.NEO4J_PASSWORD))
    researchUuid=str(uuid.uuid4())
    
    query="""CREATE (n:Document {uuid: $researchUuid})
        set 
            n.name=$name,
            n.addeddate= datetime(),
            n.type="Generated Research",
            n.process=True,
            n.topics=$topics
            with n
                MATCH (u:User {uuid: $useruuid})
                MERGE (ua:UserAction {useruuid: u.uuid}) 
                ON CREATE SET ua.name = u.username, ua.uuid=randomUUID()
                MERGE (u)-[r:HAS_ACTION]->(ua)
                MERGE (ua)-[:ADDED]-(n) set r.dateadded= datetime()
            """
    with driver.session() as session:
        session.run(query, { "researchUuid": researchUuid, "name": request_body.topics[0], "useruuid": current_user.uuid, "topics": request_body.topics})
        session.close()
    master_agent = MasterAgent()
    task_ids = []
    try:
        research = master_agent.run(current_user.uuid, request_body.topics, researchUuid)
        query = """
            MATCH (d:Document {uuid: $researchUuid})
            MATCH path = (d)-[:HAS_WORKFLOW]->(s1:Step)-[:NEXT*]-(step:Step)
            OPTIONAL MATCH (step)-[:CONTRIBUTED_NEW|DESIGNED]->(related_doc:Document)
            WITH COLLECT(DISTINCT related_doc.uuid) AS related_doc_uuids
            RETURN related_doc_uuids
        """
        with driver.session() as session:
            result = session.run(query, {"researchUuid": researchUuid})
            doc_uuids = result.single()["related_doc_uuids"]
        
        # add the research uuid to the list of related documents
        doc_uuids.append(researchUuid)

        # Prepare data for JSON result
        research_document = None
        topic_research = None
        sources = []
        task_ids = []
        shareable_links = []

        try:
            for documentId in doc_uuids:
                logging.info(f"Processing document {documentId}.")
                with driver.session() as session:
                    result = session.run("""
                        MATCH (a:Document {uuid: $uuid})
                        RETURN a.uuid as uuid, a.text as text, a.url as url, a.addeddate as date, a.type as type
                    """, {"uuid": documentId})
                    document_data = result.single()
                    
                    if document_data["type"] == "Generated Research":
                        research_document = {
                            "uuid": document_data["uuid"],
                            "text": document_data["text"],
                            "url": document_data["url"],
                            "date": document_data["date"]
                        }
                    elif document_data["type"] == "Generated Article":
                        topic_research = {
                            "uuid": document_data["uuid"],
                            "text": document_data["text"],
                            "url": document_data["url"],
                            "date": document_data["date"]
                        }
                    elif document_data["type"] == "Agent Contributed":
                        sources.append({
                            "uuid": document_data["uuid"],
                            "text": document_data["text"],
                            "url": document_data["url"],
                            "date": document_data["date"]
                        })
                
                # Process text task
                task = process_text_task.delay(document_data["text"], documentId, True, True, True)
                task_ids.append(task.id)
                logging.info(f"Queued document {documentId} with task ID {task.id}")
                
                # Generate shareable link
                shareable_link = generate_shareable_link(documentId, 'html', current_user.uuid, driver)
                shareable_links.append(shareable_link)
            
        except Exception as e:
            logging.error(f"Failed to process document {documentId}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to process document {documentId}: {e}")
        finally:
            driver.close()

        return {
            "research_document": research_document,
            "topic_research": topic_research,
            "sources": sources,
            "shareable_links": shareable_links,
            "task_ids": task_ids,
            "message": "Research documents processed successfully"
        }
    except Exception as e:
        # Get the full stack trace
        stack_trace = traceback.format_exc()
        # Log the error along with the stack trace
        logging.error(f"Error generating newspaper: {str(e)}\nStack trace: {stack_trace}")
        # Raising the HTTPException with the original error message, without the stack trace
        raise HTTPException(status_code=500, detail=str(e))

