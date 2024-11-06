import logging
from typing import Dict, Any
from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError
from langchain_openai.embeddings import OpenAIEmbeddings
from langchain_experimental.text_splitter import SemanticChunker
from langchain_openai import ChatOpenAI
import uuid

from backend.config import CurrentConfig
from backend.services.processing_services import generate_questions, generate_summaries
from backend.worker.task_category_logic import generate_category_logic

def process_text_logic(
    textToProcess: str,
    documentId: str,
    generateQuestions: bool,
    generateSummaries: bool,
    generateCategory: bool
) -> Dict[str, Any]:
    logging.info(f"Starting process for document {documentId}")

    embeddings = OpenAIEmbeddings(openai_api_key=CurrentConfig.OPENAI_API_KEY)
    llm = ChatOpenAI(temperature=0, model=CurrentConfig.OPENAI_CHAT_MODEL, openai_api_key=CurrentConfig.OPENAI_API_KEY)
    
    try:
        driver = GraphDatabase.driver(CurrentConfig.CELERY_NEO4_URL, auth=(CurrentConfig.NEO4J_USER, CurrentConfig.NEO4J_PASSWORD))
       

        parent_splitter = SemanticChunker(embeddings, breakpoint_threshold_type="percentile")
        child_splitter = SemanticChunker(embeddings, breakpoint_threshold_type="percentile")
        parent_documents = parent_splitter.create_documents([textToProcess])

        for i, parent in enumerate(parent_documents):
            logging.info(f"processing chunk {i+1} of {len(parent_documents)} for document {documentId}")

            child_documents = child_splitter.create_documents([parent.page_content])
            params = {
                "document_uuid": documentId,
                "parent_uuid": str(uuid.uuid4()),
                "name": f"Page {i+1}",
                "parent_text": parent.page_content,
                "parent_id": i,
                "parent_embedding": embeddings.embed_query(parent.page_content),
                "children": [
                    {
                        "text": c.page_content,
                        "id": str(uuid.uuid4()),
                        "name": f"{i}-{ic+1}",
                        "embedding": embeddings.embed_query(c.page_content),
                    }
                    for ic, c in enumerate(child_documents)
                ],
            }

            try:
                with driver.session() as session:
                    session.run(
                         """
                        MERGE (p:Page {uuid: $parent_uuid})
                        SET p.text = $parent_text,
                        p.name = $name,
                        p.type = "Page",
                        p.datecreated= datetime(),
                        p.source=$parent_uuid
                        WITH p
                        CALL db.create.setVectorProperty(p, 'embedding', $parent_embedding) YIELD node
                        WITH p
                            MATCH (d:Document {uuid: $document_uuid})
                            MERGE (d)-[:HAS_PAGE]->(p)
                        WITH p
                        UNWIND $children AS child
                            MERGE (c:Child {uuid: child.id})
                            SET
                                c.text = child.text,
                                c.name = child.name,
                                c.source=child.id
                            MERGE (c)<-[:HAS_CHILD]-(p)
                            WITH c, child
                                CALL db.create.setVectorProperty(c, 'embedding', child.embedding)
                            YIELD node
                            RETURN count(*)
                        """,
                        params,
                    )
            except Neo4jError as e:
                logging.error(f"Neo4j error in document {documentId}, chunk {i+1}: {e}")
                raise

        if generateQuestions:
            generate_questions(llm, parent_documents, documentId, embeddings, driver)

        if generateSummaries:
            generate_summaries(llm, parent_documents, documentId, embeddings, driver)
        
        if generateCategory:
            generate_category_logic(documentId, llm, driver)

    except Exception as e:
        logging.error(f"Failed to process document {documentId}: {e}")
        return {"message": "Failed", "error": str(e)}

    finally:
        driver.close()

    logging.info(f"Successfully processed document {documentId}")
    return {"message": "Success", "uuid": documentId}

