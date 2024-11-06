"""
Search Services Module

This module provides functionality for searching documents in the Neo4j database using full-text search.
It handles constructing and executing search queries against the Lucene index to find relevant documents
and pages based on search terms.

Functions:
    search_thelink: Searches documents using a query string
    construct_query: Builds a Neo4j Cypher query for full-text search
"""

from neo4j import GraphDatabase

from backend.config import CurrentConfig

def search_thelink(query: str):
    """
    Search for documents matching the given query using Neo4j's full-text search.

    Args:
        query (str): The search query string

    Returns:
        list: List of dictionaries containing matching document/page information:
            - pageuuid: UUID of the matching page
            - title: Document title
            - published date: Publication date of the document
            - content: Text content of the matching page
            - score: Search relevance score
            - url: URL of the document
            - uuid: UUID of the document
    """
    driver = GraphDatabase.driver(CurrentConfig.NEO4J_URI, auth=(CurrentConfig.NEO4J_USER, CurrentConfig.NEO4J_PASSWORD))

    neo4j_query = construct_query(CurrentConfig.PAGE_TEXT_INDEX, query, CurrentConfig.FULL_TEXT_SCORE_THRESHOLD)
    urls_from_neo4j = None
    try: # search for the query in the database
        with driver.session() as session:
            result = session.run(neo4j_query)
            urls_from_neo4j = [{"pageuuid":result["pageuuid"],"title": result["title"],"published date":result["publisheddate"],"content":result["content"],"score":result["score"],"url": result["url"],"uuid":result["uuid"]} for result in result]
    finally:
        driver.close()
    return urls_from_neo4j

def construct_query(index_name, query_term, similarity_score):
    """
    Construct a Neo4j Cypher query for full-text search.

    Args:
        index_name (str): Name of the Lucene index to search
        query_term (str): Search term to query
        similarity_score (float): Minimum similarity threshold for matches

    Returns:
        str: Constructed Cypher query string that searches the index and returns matching documents
    """
    # Ensure similarity_score is formatted correctly (e.g., 0.7 should be '0.7')
    similarity_score = str(similarity_score).rstrip('0').rstrip('.') if '.' in str(similarity_score) else str(similarity_score)
    
    search_query = f"""
    CALL db.index.fulltext.queryNodes('{index_name}', '{query_term}~{similarity_score}') YIELD node, score 
    WITH node, score
    WITH node, score ORDER BY score DESC LIMIT 10 
    MATCH (node)-[:HAS_PAGE]-(d:Document)
    RETURN d.uuid as uuid, d.name as title, node.uuid as pageuuid, d.url as url, node.text as content, score as score, node.publisheddate as publisheddate ORDER BY score DESC
    """
    return search_query
