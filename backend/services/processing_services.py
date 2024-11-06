"""
Document Processing Services Module

This module contains functions for processing documents and generating various outputs like questions and summaries.
It handles document analysis, question generation, and summary creation using language models and graph database storage.

Key Functions:
    generate_questions: Generates relevant questions from document content
    generate_summaries: Creates concise summaries of document content

Key Components:
- Document conversion functions
- Question generation using LLMs
- Summary generation and storage
- Access token retrieval
- Neo4j database integration

Dependencies:
- langchain: For language model interactions
- neo4j: For graph database operations
- requests: For HTTP requests
- subprocess: For system commands
- tempfile: For temporary file handling
- uuid: For unique identifier generation

Environment variables are managed through the CurrentConfig class.
"""

import logging
import uuid
from typing import List

import os
from pydantic import BaseModel, Field

from langchain.prompts import ChatPromptTemplate
from backend.config import CurrentConfig


class Questions(BaseModel):
    """
    Model class for generating hypothetical questions about text.
    
    Attributes:
        questions (List[str]): List of generated questions based on input text
    """

    questions: List[str] = Field(
        ...,
        description=(
            "Generated hypothetical questions based on " "the information from the text"
        ),
    )

# Initialize environment variables if needed
CurrentConfig.initialize_environment_variables()

def generate_questions(llm, parent_documents, documentId, embeddings, driver):
    """
    Generate questions from document content using language models.
    
    Args:
        llm: Language model instance for question generation
        parent_documents: List of document sections to process
        documentId (str): Unique identifier for the document
        embeddings: Embedding model for text vectorization
        driver: Neo4j database driver instance
        
    The function:
    1. Processes each document section
    2. Generates relevant questions using the language model
    3. Creates question nodes in Neo4j with embeddings
    4. Links questions to their source document sections
    """
    # Generate Questions for page node 
    logging.info(f"Generating questions for document {documentId}")
    questions_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                (
                    "You are generating questions that users might ask based on the information "
                    "found in the text. Make sure to provide full context in the generated "
                    "questions."
                ),
            ),
            (
                "human",
                (
                    "Use the given format to generate questions from the "
                    "following input: {input}"
                ),
            ),
        ]
    )
    
    logging.info(f"LLM type: {type(llm)}, Prompt: {questions_prompt}")
    
    # Create the chain
    question_chain = questions_prompt | llm.with_structured_output(Questions)

    for i, parent in enumerate(parent_documents):
        logging.info(f"Generating questions for page {i+1} of {len(parent_documents)} for document {documentId}")
        generated_questions = question_chain.invoke({"input": parent.page_content})
        limited_questions = generated_questions.questions[:CurrentConfig.MAX_QUESTIONS_PER_PAGE]  # Limit the number of questions

        params = {
            "parent_id": f"Page {i+1}",
            "document_uuid": documentId,
            "questions": [
                {
                    "text": q, 
                    "uuid": str(uuid.uuid4()), 
                    "name": f"{i+1}-{iq+1}", 
                    "embedding": embeddings.embed_query(q)
                }
                for iq, q in enumerate(limited_questions) if q  # Iterate over limited questions
            ],
        }
        with driver.session() as session :
            session.run(
                """
            match (d:Document)-[]-(p:Page) where d.uuid=$document_uuid and p.name=$parent_id
            WITH p
            UNWIND $questions AS question
            CREATE (q:Question {uuid: question.uuid})
            SET q.text = question.text, q.name = question.name, q.datecreated= datetime(), q.source=p.uuid
            MERGE (q)<-[:HAS_QUESTION]-(p)
            WITH q, question
            CALL db.create.setVectorProperty(q, 'embedding', question.embedding)
            YIELD node
            RETURN count(*)
            """,
            params,
        )
        
        

def generate_summaries(llm, parent_documents, documentId, embeddings, driver):
    """
    Generate summaries from document content using language models.
    
    Args:
        llm: Language model instance for summary generation
        parent_documents: List of document sections to process
        documentId (str): Unique identifier for the document
        embeddings: Embedding model for text vectorization
        driver: Neo4j database driver instance
        
    The function:
    1. Processes each document section
    2. Generates concise summaries using the language model
    3. Creates summary nodes in Neo4j with embeddings
    4. Links summaries to their source document sections
    """
    # Code for generating summaries
       
    # Ingest summaries

    summary_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                (
                    "You are generating concise and accurate summaries based on the "
                    "information found in the text."
                ),
            ),
            (
                "human",
                ("Generate a summary of the following input: {question}\n" "Summary:"),
            ),
        ]
    )

    summary_chain = summary_prompt | llm

    for i, parent in enumerate(parent_documents):
        
        logging.info(f"Generating summary for page {i+1} of {len(parent_documents)} for document {documentId}")
        
        summary = summary_chain.invoke({"question": parent.page_content}).content
        params = {
            "parent_id": f"Page {i+1}",
            "uuid": str(uuid.uuid4()),
            "summary": summary,
            "embedding": embeddings.embed_query(summary),
            "document_uuid": documentId
        }
        with driver.session() as session :
            session.run(
                """
            match (d:Document)-[]-(p:Page) where d.uuid=$document_uuid and p.name=$parent_id
            with p
            MERGE (p)-[:HAS_SUMMARY]->(s:Summary)
            SET s.text = $summary, s.datecreated= datetime(), s.uuid= $uuid, s.source=p.uuid
            WITH s
            CALL db.create.setVectorProperty(s, 'embedding', $embedding)
            YIELD node
            RETURN count(*)
            """,
                params,
            )
