"""
Tools module for finding and listing documents in the knowledge graph.

This module provides functionality for querying and retrieving documents from a Neo4j database,
with support for various filtering and sorting options. It integrates with OpenAI embeddings
for semantic search capabilities.

Key Functions:
- extract_param_name: Extracts parameter names from Cypher query filters
- document_list: Main function for retrieving filtered and sorted document lists

The module uses:
- Neo4j for graph database operations
- OpenAI embeddings for semantic search
- Langchain for tool definitions
"""

import re

from neo4j import GraphDatabase
from typing import Optional
from langchain.tools import Tool, StructuredTool

import logging
from backend.schemas.document import DocumentListInput
from typing import List, Dict, Optional

from backend.config import CurrentConfig
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Neo4jVector
from neo4j import GraphDatabase


logger = logging.getLogger(__name__)

def extract_param_name(filter: str) -> str:
    """
    Extract parameter names from a Cypher query filter string.

    Args:
        filter (str): The Cypher filter string containing parameters.

    Returns:
        str: The extracted parameter name without the $ prefix, or None if no parameter is found.

    Example:
        >>> extract_param_name("d.type = $document_type")
        'document_type'
    """
    # Regex to find parameters in the Cypher statement
    pattern = r'\$\w+'
    # Search for the first match
    match = re.search(pattern, filter)
    
    # Output the first found parameter, if it exists
    if match:
        return match.group()[1:]
    return None


def document_list(
    sort_by: str = "name",
    k: int = 4,
    description: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    document_type: Optional[str] = None,
) -> List[Dict]:
    """
    List documents from the Neo4j database based on specified filters and sorting criteria.

    Args:
        sort_by (str, optional): Field to sort results by. Defaults to "name".
        k (int, optional): Maximum number of results to return. Defaults to 4.
        description (str, optional): Text description for semantic search. Defaults to None.
        start_date (str, optional): Start date filter in ISO format. Defaults to None.
        end_date (str, optional): End date filter in ISO format. Defaults to None.
        document_type (str, optional): Type of document to filter by. Defaults to None.

    Returns:
        List[Dict]: List of documents with their associated pages, questions, and summaries.
            Each document contains metadata and a nested structure of pages.

    Raises:
        Exception: If there is an error executing the Neo4j query.

    The function supports both traditional filtering and semantic search using embeddings.
    When description is provided without other filters, it performs a pure vector similarity search.
    """
    logger.info(f"Starting document_list function with parameters: sort_by={sort_by}, k={k}, description={description}, start_date={start_date}, end_date={end_date}, document_type={document_type}")

    embedding = OpenAIEmbeddings(openai_api_key=CurrentConfig.OPENAI_API_KEY, model=CurrentConfig.OPENAI_EMBEDDING_MODEL)
    logger.debug(f"Initialized OpenAIEmbeddings with model: {CurrentConfig.OPENAI_EMBEDDING_MODEL}")

    neo4j_vector = Neo4jVector.from_existing_graph(
        embedding,
        index_name="document",
        url=CurrentConfig.NEO4J_URI,
        username=CurrentConfig.NEO4J_USER,
        password=CurrentConfig.NEO4J_PASSWORD,
        text_node_properties=["name","text"],
        node_label="Document",
        embedding_node_property="embedding"
    )
    logger.debug("Initialized Neo4jVector from existing index")
    
    # HACK: Forcing document_type to be None for now to avoid breaking changes, and to ensure that the default is used
    # this is because the document_type filter appears to be unreliable so needs more investigation
    document_type = None 

    # Handle vector-only search when no prefiltering is applied
    if description and not start_date and not end_date and not document_type:
        logger.info("Performing vector-only search")
        return neo4j_vector.similarity_search(description, k=k)

    filters = [
        (" date(datetime(coalesce(d.datepublished, d.addeddate))) >= date($start_date) ", start_date),
        (" date(datetime(coalesce(d.datepublished, d.addeddate))) <= date($end_date) ", end_date ),
        (" d.type = $document_type", document_type) if document_type is not None else (None, None),
    ]

    # Create parameters dynamically from function arguments
    params = {}
    for filter_condition, value in filters:
        if value is not None:
            param_name = extract_param_name(filter_condition)
            if param_name:
                params[param_name] = value
    where_clause = " AND ".join(
        [condition for condition, value in filters if value is not None]
    )

    cypher_statement = "MATCH (d:Document)-[:HAS_PAGE]->(p:Page {name:'Page 1'}) "
    if where_clause:
        cypher_statement += f"WHERE {where_clause} "

    # Add the return clause with sorting
    cypher_statement += """
            WITH d, p
                OPTIONAL MATCH (p)-[:HAS_QUESTION]->(q:Question)
                OPTIONAL MATCH (p)-[:HAS_SUMMARY]->(s:Summary)
                WITH d, p, 
                    collect(DISTINCT {uuid: q.uuid, name: q.name, text: q.text}) AS questions,
                    collect(DISTINCT {uuid: s.uuid, name: s.name, text: s.text}) AS summaries
                ORDER BY d.name, toInteger(replace(p.name, 'Page ', ''))
                WITH d,
                    collect({
                        uuid: p.uuid, 
                        name: p.name, 
                        summaries: summaries, 
                        questions: questions
                    }) AS pages
                RETURN 
                    d.uuid AS doc_uuid, d.name AS doc_name, toString(coalesce(d.addeddate, datetime('1900-01-01'))) AS doc_addeddate, 
                    d.imageurl AS doc_imageurl, d.publisher AS doc_publisher, 
                    d.thumbnail AS doc_thumbnail, d.url AS doc_url, d.wordcount AS doc_wordcount,  d.type as type,pages
                    ORDER BY 
     """
    # Handle sorting logic based on description or other criteria
    if description:
        cypher_statement += (
            "vector.similarity.cosine(d.embedding, $embedding) DESC "
        )
        params["embedding"] = embedding.embed_query(description)
    elif sort_by == "name":
        cypher_statement += "d.name DESC "
    else:  # sort by latest year
        cypher_statement += "d.addeddate DESC "

    cypher_statement += " LIMIT toInteger($limit)"
    params["limit"] = k or 4

    logger.debug(f"Cypher statement: {cypher_statement}")
    logger.debug(f"Query parameters: {params}")

    # Initialize Neo4j driver
    driver = GraphDatabase.driver(CurrentConfig.NEO4J_URI, auth=(CurrentConfig.NEO4J_USER, CurrentConfig.NEO4J_PASSWORD))
    output = []
    try:
        with driver.session() as session:
            results = session.run(cypher_statement, params)
            
            for record in results:
                # Structuring the output
                document_data = {
                    "uuid": record["doc_uuid"],
                    "name": record["doc_name"],
                    "addeddate": record["doc_addeddate"],
                    "imageurl": record["doc_imageurl"],
                    "publisher": record["doc_publisher"],
                    "thumbnail": record["doc_thumbnail"],
                    "type": record["type"],
                    "url": record["doc_url"],
                    "wordcount": record["doc_wordcount"]
                }

                pages_data = record["pages"]

                output.append({
                    "document": document_data,
                    "pages": pages_data
                })
        return output
    except Exception as e:
        logger.error(f"Error executing Neo4j query: {str(e)}")
        raise
    finally:
        driver.close()



tools_available = [
    StructuredTool.from_function(
        func=document_list,
        name="document-list",
        description="Use to list documents based on particular filters",
        args_schema=DocumentListInput
    ),
]
