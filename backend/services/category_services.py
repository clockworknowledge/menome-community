"""
This module provides services for managing categories in a knowledge graph system.

The module handles category processing, storage, and analysis through several key functions:

Key Functions:
- merge_categories: Merges category nodes and relationships into a Neo4j database
- transform_to_json_structure: Transforms nodes and relationships into a JSON structure
- send_to_rabbitmq: Sends processed data to a RabbitMQ queue
- calculate_similarity: Calculates similarity between two category nodes
- batch_similarity_check: Performs batch similarity checks on multiple categories
- normalize_dates: Normalizes date nodes to UTC timezone
- clean_category_name: Cleans category names by removing invalid characters
- prefilter_category_nodes: Prefilters category nodes based on validity criteria
- score_and_filter_categories: Scores and filters categories based on suitability

The module integrates with several external services and libraries:
- Neo4j for graph database storage
- OpenAI for embeddings and language model inference
- RabbitMQ for message queuing
- LangChain for language model interactions

Dependencies:
- json: For JSON processing
- dateutil: For date parsing and manipulation
- pika: For RabbitMQ integration
- logging: For logging functionality
- pytz: For timezone handling
- re: For regular expressions
- pydantic: For data validation
- uuid: For unique identifier generation
- openai: For OpenAI API integration
- langchain: For language model interactions
"""

import json
import dateutil
import pika
import logging
import pytz
import re
from pydantic import BaseModel, ValidationError
from pydantic import BaseModel
from typing import List
from datetime import datetime, timezone
import uuid

from openai import OpenAIError

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.prompts import HumanMessagePromptTemplate
from langchain_core.messages import AIMessage
from langchain_openai import OpenAIEmbeddings


def merge_categories(nodes, relationships, documentId, openai_api_key, driver):
    """
    Merges category nodes and their relationships into a Neo4j database.

    Args:
    nodes (List): A list of node objects representing categories.
    relationships (List): A list of relationship objects between categories.
    documentId (str): The unique identifier of the document.
    openai_api_key (str): The API key for OpenAI services.
    driver (neo4j.Driver): The Neo4j database driver.

    This function performs the following steps:
    1. Generates embeddings for each node using OpenAI's embedding service.
    2. Creates Cypher statements to merge nodes and relationships into the Neo4j database.
    3. Executes the Cypher statements to update the database.

    The function handles both the creation of new nodes and the merging of existing ones,
    as well as establishing relationships between nodes and the document.
    """
    embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)
    
    # Generate Cypher statements to commit nodes and relationships to Neo4j
    cypher_statements = []

    # Define today's date outside the loop
    today = datetime.now(timezone.utc).isoformat()

    # Merge nodes and create relationships
    for node in nodes:
        node_embedding = embeddings.embed_query(node.id)
        
        cypher_statements.append({
            "query": """
            MERGE (n:Category {name: $name})
            ON CREATE SET n.addeddate = $today, n.embedding = $embedding, n.uuid =randomUUID(),
            n.description = $description, n.type = $type
            WITH n
            MATCH (d:Document {uuid: $documentId})
            MERGE (d)-[:MENTIONS]->(n)
            """,
            "parameters": {
                "name": node.id,
                "today": today,
                "embedding": node_embedding,
                "description": node.properties.get('description', ''),
                "type": node.type,
                "documentId": documentId
            }
        })

    # Create relationships between nodes
    for relationship in relationships:
        source_embedding = embeddings.embed_query(relationship.source.id)
        target_embedding = embeddings.embed_query(relationship.target.id)
        cypher_statements.append({
            "query": """
            MERGE (s:Category {name: $sourceName})
            ON CREATE SET s.dateAdded = $today, s.embedding = $sourceEmbedding, s.uuid = $uuid, s.description = $sourceDescription, s.type = $sourceType
            MERGE (t:Category {name: $targetName})
            ON CREATE SET t.dateAdded = $today, t.embedding = $targetEmbedding, t.uuid = $uuid, t.description = $targetDescription, t.type = $targetType

            MERGE (s)-[:MENTIONS {r:$targetType}]->(t)
            """,
            "parameters": {
                "sourceName": relationship.source.id,
                "targetType": relationship.target.type,
                "targetName": relationship.target.id,
                "sourceEmbedding": source_embedding,
                "targetEmbedding": target_embedding,
                "today": today,
                "uuid": str(uuid.uuid4()),
                "sourceDescription": relationship.source.properties.get('description', ''),
                "targetDescription": relationship.target.properties.get('description', ''),
                "sourceType": relationship.source.type,
                "targetType": relationship.target.type
            }
        })
    
    logging.info(f"Committing {len(cypher_statements)} nodes and relationship categories to Neo4j")
    # Execute Cypher statements
    with driver.session() as session:
        for statement in cypher_statements:
            logging.debug(f"Executing Cypher statement: {statement['query']}")
            session.run(statement["query"], statement["parameters"])
    # The session is automatically closed when exiting the 'with' block


def transform_to_json_structure(nodes, relationships, documentId, openai_api_key):
    """
    Transforms a set of nodes and relationships into a JSON structure suitable for further processing.

    Args:
    nodes (List): A list of node objects representing categories.
    relationships (List): A list of relationship objects between categories.
    documentId (str): The unique identifier of the document.
    openai_api_key (str): The API key for OpenAI services.

    Returns:
    List[dict]: A list of dictionaries representing the JSON structure of nodes and their relationships.

    This function performs the following steps:
    1. Generates embeddings for each node using OpenAI's embedding service.
    2. Creates a JSON structure for each node, including its properties and connections.
    3. Adds relationships to the JSON structure, including the document relationship.

    The resulting JSON structure includes node types, properties (including embeddings),
    conformed dimensions, and connections to other nodes and the document.
    """
    # Setup embeddings
    embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)
    
    json_structure = []

    for node in nodes:
        # Generate embeddings for the node
        try:
            node_embedding = embeddings.embed_query(node.id)
        except Exception as e:
            logging.error(f"Failed to generate embedding for node {node.id}: {e}")
            node_embedding = None
        
        node_json = {
            "NodeType": node.type,
            "Properties": {**node.properties, "embedding": node_embedding},
            "ConformedDimensions": {"name": node.id},
            "Connections": [
                {
                    "NodeType": "Document",
                    "RelType": "MENTIONS",
                    "ForwardRel": False,
                    "ConformedDimensions": {
                        "uuid": documentId
                    }
                }
            ]
        }

        for rel in relationships:
            if rel.source.id == node.id:
                connection = {
                    "NodeType": rel.target.type,
                    "RelType": "MENTIONS",
                    "ForwardRel": True,
                    "ConformedDimensions": {
                        "name": rel.target.id,  "embedding": embeddings.embed_query(rel.target.id)
                    },
                    "Properties": {"TYPE": rel.type}  
                }
                node_json["Connections"].append(connection)

        json_structure.append(node_json)

    return json_structure



def send_to_rabbitmq(json_structure, rabbitmq_host, rabbitmq_port, rabbitmq_user, rabbitmq_password, queue_name='messageserver'):
    """
    Sends a JSON structure to a RabbitMQ queue.

    Args:
    json_structure (List[dict]): The JSON structure to be sent to RabbitMQ.
    rabbitmq_host (str): The hostname of the RabbitMQ server.
    rabbitmq_port (int): The port number of the RabbitMQ server.
    rabbitmq_user (str): The username for RabbitMQ authentication.
    rabbitmq_password (str): The password for RabbitMQ authentication.
    queue_name (str, optional): The name of the queue to send messages to. Defaults to 'messageserver'.

    This function performs the following steps:
    1. Establishes a connection to the RabbitMQ server using the provided credentials.
    2. Declares a durable exchange and queue, and binds them together.
    3. Converts each message in the JSON structure to a JSON string.
    4. Publishes each message to the specified queue.
    5. Closes the connection after sending all messages.

    The function handles potential connection errors and logs relevant information.
    """
    logging.info(f"RabbitMQ Host: {rabbitmq_host}")
    
    try:
        # Connect to RabbitMQ server with authentication
        credentials = pika.PlainCredentials(rabbitmq_user, rabbitmq_password)
        connection = pika.BlockingConnection(pika.ConnectionParameters(
            host=rabbitmq_host,
            port=rabbitmq_port,
            credentials=credentials
        ))
        channel = connection.channel()
        exchange_name = 'messageserver_exchange'
        
        # Declare the exchange
        channel.exchange_declare(exchange=exchange_name, exchange_type='direct', durable=True)

        # Declare the queue as durable
        channel.queue_declare(queue=queue_name, durable=True)

        # Bind the queue to the exchange with the routing key same as queue name
        channel.queue_bind(exchange=exchange_name, queue=queue_name, routing_key=queue_name)

        for message in json_structure:
            # Convert the message to JSON
            message_json = json.dumps(message)
            # Send the message to the queue
            channel.basic_publish(exchange='messageserver_exchange',
                                  routing_key=queue_name,
                                  body=message_json)
            logging.info(f"Sent: {message_json}")

        # Close the connection
        connection.close()
    except pika.exceptions.AMQPConnectionError as e:
        logging.error(f"Failed to connect to RabbitMQ: {e}")
    except Exception as e:
        logging.error(f"An error occurred while sending message to RabbitMQ: {e}")



def calculate_similarity(node1, node2, llm):
    """
    Calculates the similarity between two nodes using a language model.

    Args:
    node1 (str): The identifier of the first node.
    node2 (str): The identifier of the second node.
    llm (LangChain LLM): The language model to use for similarity calculation.

    Returns:
    int: A similarity score between 0 and 100, where 0 means completely different and 100 means identical.

    This function performs the following steps:
    1. Constructs a prompt asking about the similarity of two categories.
    2. Sends the prompt to the language model.
    3. Extracts a numerical similarity score from the model's response.
    4. Handles potential errors and edge cases.

    The function uses regular expressions to extract the similarity score from the model's response.
    """
    try:
        # Ensure the nodes are not None
        if not node1 or not node2:
            logging.error(f"One of the nodes is None. Node1: {node1}, Node2: {node2}")
            return 0

        prompt_template = (
            "Given the two categories:\n"
            "1. {category1}\n"
            "2. {category2}\n\n"
            "How similar are these categories on a scale from 0 to 100, where 0 means completely different and 100 means identical?"
        )

        # Create a ChatPromptTemplate with placeholders
        prompt = ChatPromptTemplate(
            messages=[
                HumanMessagePromptTemplate.from_template(prompt_template)
            ],
            input_variables=["category1", "category2"]
        )

        # Format the prompt with actual values
        formatted_prompt = prompt.format(category1=node1, category2=node2)

        # Send the prompt to the LLM and get the response
        response = llm(formatted_prompt)

        # Check if the response is an AIMessage and extract the content
        if isinstance(response, AIMessage):
            response_text = response.content
        else:
            response_text = str(response)

        # Use regular expression to extract the first number found in the response
        match = re.search(r'\b\d+\b', response_text)
        if match:
            similarity_score = int(match.group())
            return similarity_score
        else:
            logging.error(f"Could not extract a similarity score from the response: {response_text}")
            return 0

    except OpenAIError as e:
        logging.error(f"OpenAI API error: {e}")
        return 0
    


class SimilarityPair(BaseModel):
    category1: str
    category2: str
    similarity_score: int

class SimilarityResponse(BaseModel):
    pairs: List[SimilarityPair]

class SimilarityPair(BaseModel):
    category1: str
    category2: str
    similarity_score: int

# Update the SimilarityResponse model to be a list of SimilarityPair
SimilarityResponse = list[SimilarityPair]

def batch_similarity_check(category_nodes, llm, threshold):
    """
    Performs a batch similarity check on a list of category nodes and filters out similar nodes.

    Args:
    category_nodes (List): A list of category node objects.
    llm (LangChain LLM): The language model to use for similarity calculation.
    threshold (int): The similarity threshold above which nodes are considered similar.

    Returns:
    List: A filtered list of category nodes with similar nodes removed.

    This function performs the following steps:
    1. Generates all possible pairs of category nodes.
    2. Constructs a batch prompt for the language model to evaluate similarities.
    3. Processes the language model's response to extract similarity scores.
    4. Filters out nodes that are too similar based on the given threshold.

    The function handles various edge cases and errors, logging relevant information throughout the process.
    """
    try:
        if len(category_nodes) < 2:
            return category_nodes  # If there's only one node, return it as is

        # Log the initial list of nodes and their count
        logging.info(f"Initial list of nodes: {[node.id for node in category_nodes]}")
        logging.info(f"Initial count of nodes: {len(category_nodes)}")

        # Construct the batch prompt
        pairs = []
        node_pairs = []
        for i in range(len(category_nodes)):
            for j in range(i + 1, len(category_nodes)):
                pairs.append(f'{{"category1": "{category_nodes[i].id}", "category2": "{category_nodes[j].id}"}}')
                node_pairs.append((category_nodes[i].id, category_nodes[j].id))  # Use node.id instead of Node object

        logging.info(f"Generated {len(pairs)} pairs for similarity check.")

        prompt_template = (
            f"Given the following pairs of categories, determine their similarity score on a scale from 0 to 100, "
            f"where 0 means completely different and 100 means identical.  "
            f"Return the results in a strict JSON format, with no additional information or explanation. The JSON should be an array of objects in the following format:\n\n"
            f'[{{"category1": "Category1", "category2": "Category2", "similarity_score": Score}}]\n\n'
            f"[{', '.join(pairs)}]"
        )

        # Send the batch prompt to the LLM
        response = llm(prompt_template)

        # Handle AIMessage response
        if isinstance(response, AIMessage):
            response_text = response.content  # Extract content from AIMessage
        else:
            response_text = str(response)

        # Use a regular expression to find and extract the JSON part of the response
        json_match = re.search(r'\[\s*\{.*?\}\s*\]', response_text, re.DOTALL)

        if not json_match:
            logging.error("Failed to extract JSON from LLM response.")
            return category_nodes

        json_part = json_match.group(0)

        # Log the extracted JSON for debugging
        logging.info(f"Extracted JSON: {json_part}")

        # Parse the extracted JSON as a list of SimilarityPair
        try:
            similarity_response = [SimilarityPair(**item) for item in json.loads(json_part)]
        except (json.JSONDecodeError, ValidationError) as e:
            logging.error(f"Failed to parse JSON: {e}")
            return category_nodes

        dissimilar_node_ids = {node.id for node in category_nodes}

        for pair in similarity_response:
            if pair.similarity_score >= threshold:
                node_to_remove = pair.category2 if pair.category1 in dissimilar_node_ids else pair.category1
                dissimilar_node_ids.discard(node_to_remove)

        # Filter the nodes that are not similar
        filtered_nodes = [node for node in category_nodes if node.id in dissimilar_node_ids]

        # Log the final list of nodes and their count
        logging.info(f"Filtered list of nodes: {[node.id for node in filtered_nodes]}")
        logging.info(f"Filtered count of nodes: {len(filtered_nodes)}")

        return filtered_nodes

    except OpenAIError as e:
        logging.error(f"OpenAI API error: {e}")
        return category_nodes  # Fallback to returning all nodes if there's an error





def normalize_dates(nodes):
    """
    Normalizes date nodes to UTC timezone.

    Args:
    nodes (List): A list of node objects, potentially containing date nodes.

    Returns:
    List: A list of nodes with date nodes normalized to UTC.

    This function performs the following steps:
    1. Iterates through each node in the input list.
    2. For nodes of type "DateTime", it attempts to parse and normalize the date.
    3. Converts parsed dates to UTC timezone.
    4. Updates the node's ID with the normalized date in ISO format.
    5. Skips nodes that cannot be normalized due to parsing errors.

    Non-date nodes are kept unchanged. The function handles potential errors in date parsing
    and logs warnings for skipped nodes.
    """
    normalized_nodes = []
    for node in nodes:
        if node.type == "DateTime":
            try:
                # Parse the date and convert it to UTC
                parsed_date = dateutil.parser.parse(node.id)
                if parsed_date.tzinfo is None:
                    parsed_date = parsed_date.replace(tzinfo=pytz.UTC)
                else:
                    parsed_date = parsed_date.astimezone(pytz.UTC)
                
                # Update the node with the normalized date
                node.id = parsed_date.isoformat()
                normalized_nodes.append(node)
            except (ValueError, OverflowError) as e:
                logging.warning(f"Failed to normalize date {node.id}: {e}")
                # Skip nodes that can't be normalized
                continue
        else:
            # Keep non-date nodes unchanged
            normalized_nodes.append(node)
    
    return normalized_nodes



import re

def clean_category_name(category_name):
    """
    Cleans a category name by removing non-alphabetic characters and normalizing spaces.

    Args:
    category_name (str): The original category name.

    Returns:
    str: The cleaned category name.

    This function performs the following steps:
    1. Removes all characters that are not alphabetic or spaces.
    2. Normalizes spaces by removing extra spaces between words.

    The resulting string contains only alphabetic characters and single spaces between words.
    """
    # Remove any characters that are not alphabetic or spaces
    cleaned_name = re.sub(r'[^A-Za-z\s]', '', category_name)
    # Normalize spaces (remove extra spaces)
    cleaned_name = ' '.join(cleaned_name.split())
    return cleaned_name

def prefilter_category_nodes(category_nodes):
    """
    Prefilters a list of category nodes based on various criteria.

    Args:
    category_nodes (List): A list of category node objects.

    Returns:
    List: A filtered list of category nodes that meet the specified criteria.

    This function applies the following filters:
    1. Proper case check: Ensures the category name starts with a capital letter.
    2. Minimum length check: Ensures the cleaned category name is at least 3 characters long.
    3. Exclusion of known invalid patterns: Filters out specific terms or patterns.
    4. Character set check: Excludes categories with non-English characters or invalid patterns.

    The function uses the clean_category_name helper function to preprocess each category name
    before applying the filters.
    """
    def is_valid_category(category_name):
        # Clean the category name by removing invalid characters
        cleaned_name = clean_category_name(category_name)

        # Proper case check
        if not cleaned_name.istitle():
            return False
        
        # Minimum length check after cleaning
        if len(cleaned_name) < 3:
            return False
        
        # Exclude known invalid patterns
        invalid_terms = {"ctx", "x0", "gpt-3.5-turbo", "gpt-4 turbo"}
        if cleaned_name.lower() in invalid_terms:
            return False
        
        # Check for non-English characters and invalid patterns
        if re.search(r'^[#\$\%\(\)\+\-\./0-9]', cleaned_name) or \
           re.search(r'[0-9]', cleaned_name) or \
           re.search(r'[\$\%\(\)\+\-\./]', cleaned_name) or \
           re.search(r'[\u4E00-\u9FFF\u3040-\u309F\u30A0-\u30FF\u0400-\u04FF\u0600-\u06FF\u0590-\u05FF\u0900-\u097F\u1200-\u137F\u1000-\u109F\u0370-\u03FF\u0530-\u058F\u00C0-\u00FF]', cleaned_name):
            return False

        return True

    filtered_nodes = [
        node for node in category_nodes
        if is_valid_category(node.id)
    ]

    return filtered_nodes


import json
import logging
import openai

def score_and_filter_categories(category_nodes, llm, threshold):
    """
    Scores and filters category nodes based on their suitability as proper categories.

    Args:
    category_nodes (List): A list of category node objects.
    llm (LangChain LLM): The language model to use for scoring categories.
    threshold (int): The minimum score for a category to be considered suitable.

    Returns:
    List: A filtered list of category nodes that meet or exceed the threshold score.

    This function performs the following steps:
    1. Constructs a prompt for the language model to evaluate each category.
    2. Sends the batch prompt to the language model for scoring.
    3. Parses the response to extract scores for each category.
    4. Filters the categories based on the provided threshold.

    The function handles potential errors in API communication and JSON parsing,
    logging relevant information throughout the process.
    """
    try:      
        # Construct the batch prompt
        nodes = []
        for i in range(len(category_nodes)):
                nodes.append(f'{{"category1": "{category_nodes[i].id}"}}')

        logging.info(f"Generated {len(nodes)} pairs for suitability check.")

        # Construct the prompt for GPT-4
        prompt_template = (
            f"Evaluate the following list of category names based on their suitability as proper categories. "
            f"Assign each category a score from 0 to 100, where 0 is completely unsuitable and 100 is highly suitable. "
            f"The evaluation should consider proper case, human readability, meaningfulness, and adherence to typical category naming conventions. "
            f"Return the results in a JSON format as an array of objects only do not return the assessment criteria, do not format the json in a string quoted block: "
            f'[{{"category": "Category Name", "score": Score}}].\n\n'
            f"Categories:\n"
            f"[{', '.join(nodes)}]"
        )

       # Send the batch prompt to the LLM
        response = llm.invoke(prompt_template)

        # Handle AIMessage response
        if isinstance(response, AIMessage):
            response_text = response.content  # Extract content from AIMessage
        else:
            response_text = str(response)

        # Use a regular expression to find and extract the JSON part of the response
        json_match = re.search(r'\[\s*\{.*?\}\s*\]', response_text, re.DOTALL)

        if not json_match:
            logging.error("Failed to extract JSON from LLM response.")
            return category_nodes
        json_part = json_match.group(0)
        
        category_scores = json.loads(json_part)

        # Filter the nodes based on the score threshold
        filtered_nodes = [
            node for node in category_nodes
            if any(
                score_data['category'] == node.id and score_data['score'] <= threshold
                for score_data in category_scores
            )
        ]

        return filtered_nodes

    except Exception as e:
        logging.error(f"Category filtering error: {e}")
        return category_nodes  # Fallback to returning all nodes if there's an error
