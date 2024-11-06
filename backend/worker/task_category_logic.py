import logging
from neo4j import GraphDatabase
from langchain_openai import ChatOpenAI
from langchain_experimental.graph_transformers import LLMGraphTransformer
from backend.config import CurrentConfig
from langchain_core.documents import Document

from backend.services.category_services import  normalize_dates
from backend.services.category_services import prefilter_category_nodes,score_and_filter_categories, merge_categories

def generate_category_logic(documentId, llm, driver):

    llm_transformer = LLMGraphTransformer(
        llm=llm,
        allowed_nodes=["Category"],
        node_properties=["description"],
        relationship_properties=["description"],
    )

    with driver.session() as session:
        logging.debug(f"Executing Neo4j query for document {documentId}")
        result = session.run(
            """
            MATCH (d:Document {uuid: $documentId})-[:HAS_PAGE]->(p:Page)-[:HAS_CHILD]->(c:Child)
            RETURN c.uuid as childId, c.name as name, c.text as text
            """,
            {"documentId": documentId}
        )

        for record in result:
            childId = record["childId"]
            name = record["name"]
            text = record["text"]

            logging.debug(f"Processing child node: ID={childId}, Name={name}")
            logging.info(f"Processing Child Node {childId} children for document {documentId}")

            documents = [Document(page_content=text)]
            logging.debug(f"Converting document to graph documents for child {childId}")
            graph_documents = llm_transformer.convert_to_graph_documents(documents)

            nodes = graph_documents[0].nodes
            relationships = graph_documents[0].relationships
            logging.debug(f"Extracted {len(nodes)} nodes and {len(relationships)} relationships for child {childId}")
            
            # TODO: Determine if this code is needed based on improved merge pattern 
            # Batch similarity check
            category_nodes = [node for node in nodes if node.type == "Category"]
            logging.debug(f"Found {len(category_nodes)} category nodes before pre-filtering")
            logging.info(f"Category Nodes: {category_nodes}")
            
            # Pre-filter the category nodes
            nodes = prefilter_category_nodes(category_nodes)
            logging.debug(f"After pre-filtering: {len(category_nodes)} category nodes remain")

            threshold = CurrentConfig.SIMILARITY_THRESHOLD
            logging.debug(f"Using similarity threshold: {threshold}")

            # Use GPT-4 to score and further filter the categories
            logging.debug("Starting GPT-4 scoring and filtering of categories")
            final_excluded_nodes = score_and_filter_categories(category_nodes, llm, threshold=75)
            logging.debug(f"GPT-4 filtering excluded {len(final_excluded_nodes)} nodes")

            # Replace the original nodes list with the filtered nodes
            nodes = [node for node in nodes if node not in final_excluded_nodes]
            logging.debug(f"After all filtering: {len(nodes)} nodes remain")

            # Normalize dates
            #logging.debug("Normalizing dates in nodes")
            #normalized_nodes = normalize_dates(nodes)

            # Update the nodes list with normalized dates
            #nodes = normalized_nodes
            #logging.debug(f"After date normalization: {len(nodes)} nodes")

            #logging.info(f"Filtered and normalized nodes: {[node.id for node in nodes]}")
            # Debug logging for nodes and relationships
            #logging.debug(f"Nodes after filtering and normalization:")
            if len(nodes) > 0:
                logging.info(f"Committing nodes and relationship categories to Neo4j")
                merge_categories(nodes, relationships, documentId, CurrentConfig.OPENAI_API_KEY, driver)
            else:
                logging.info(f"No nodes to commit for document {documentId}")

   