from typing import List, Optional, Dict
from fastapi import HTTPException
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from neo4j import GraphDatabase
from collections import defaultdict
from rapidfuzz import process, fuzz
import json
import logging
from Levenshtein import distance


from backend.config import CurrentConfig

# setup classes for structured output
class DuplicateEntities(BaseModel):
    entities: List[str] = Field(
        description="Entities that represent the same object or real-world entity and should be merged"
    )


class Disambiguate(BaseModel):
    merge_entities: Optional[List[DuplicateEntities]] = Field(
        description="Lists of entities that represent the same object or real-world entity and should be merged"
    )


extraction_llm = ChatOpenAI(model_name=CurrentConfig.OPENAI_EXTRACTION_MODEL).with_structured_output(
    Disambiguate
)


def remove_loop_relationships(uri: str, user: str, password: str) -> None:
    """
    Remove self-referential relationships in the Neo4j database.

    Args:
        uri (str): The URI of the Neo4j database.
        user (str): The username for database authentication.
        password (str): The password for database authentication.

    This function connects to the Neo4j database and executes a Cypher query to
    remove relationships where the start and end nodes are the same.
    """
    driver = GraphDatabase.driver(uri=uri, auth=(user, password))
    cypher_query = """
    CALL apoc.periodic.iterate(
    "MATCH (n)-[r]->(n) RETURN r",
    "DELETE r",
    {batchSize: 1000, iterateList: true}
    )
    YIELD batches, total
    RETURN batches, total
    """
    with driver.session() as session:
        result = session.run(cypher_query)
        for record in result:
            print(f"Batches Processed: {record['batches']}, Total Relationships Deleted: {record['total']}")
    
    driver.close()


def remove_duplicate_relationships(uri: str, user: str, password: str) -> None:
    """
    Remove duplicate MENTIONS relationships in the Neo4j database.

    Args:
        uri (str): The URI of the Neo4j database.
        user (str): The username for database authentication.
        password (str): The password for database authentication.

    This function connects to the Neo4j database and executes a Cypher query to
    remove duplicate MENTIONS relationships between the same pair of nodes,
    keeping only one instance of each relationship.
    """
    driver = GraphDatabase.driver(uri=uri, auth=(user, password))
    cypher_query = """
    CALL apoc.periodic.iterate(
    "MATCH (a)-[r:MENTIONS]->(b)
    WITH a, b, collect(r) AS relationships
    WHERE size(relationships) > 1
    RETURN relationships[1..] AS relationshipsToDelete",
    "UNWIND relationshipsToDelete AS r
    DELETE r",
    {batchSize: 1000, iterateList: true}
    )
    YIELD batches, total
    RETURN batches, total
    """ 
    with driver.session() as session:
        result = session.run(cypher_query)
        for record in result:
            print(f"Batches Processed: {record['batches']}, Total Relationships Deleted: {record['total']}")
    
    driver.close()


def remove_reverse_duplicate_relationships(uri: str, user: str, password: str) -> None:
    """
    Remove reverse duplicate MENTIONS relationships in the Neo4j database.

    Args:
        uri (str): The URI of the Neo4j database.
        user (str): The username for database authentication.
        password (str): The password for database authentication.

    This function connects to the Neo4j database and executes a Cypher query to
    remove reverse duplicate MENTIONS relationships. For each pair of nodes with
    bidirectional MENTIONS relationships, it keeps only one direction.
    """
    driver = GraphDatabase.driver(uri=uri, auth=(user, password))
    cypher_query = """
    CALL apoc.periodic.iterate(
    "MATCH (a)-[r:MENTIONS]->(b)
    MATCH (b)-[r2:MENTIONS]->(a)
    WHERE id(r) < id(r2)
    RETURN r2 AS relationshipToDelete",
    "DELETE relationshipToDelete",
    {batchSize: 1000, iterateList: true}
    )
    YIELD batches, total
    RETURN batches, total
    """
    with driver.session() as session:
        result = session.run(cypher_query)
        for record in result:
            print(f"Batches Processed: {record['batches']}, Total Relationships Deleted: {record['total']}")
    
    driver.close()

    

def extract_categories(uri, user, password):
    with GraphDatabase.driver(uri, auth=(user, password)) as driver:
        with driver.session() as session:
            result = session.run("""
                MATCH (c:Category)
                RETURN c.uuid AS uuid, c.name AS name, c.wcc AS wcc
            """)
            return [(record["uuid"], record["name"], record["wcc"]) for record in result]

def group_by_community(categories: List[tuple]) -> Dict[str, List[tuple]]:
    """
    Group categories by their community.

    Args:
        categories (List[tuple]): A list of tuples containing (uuid, name, community) for each category.

    Returns:
        Dict[str, List[tuple]]: A dictionary where keys are community identifiers and values are
        lists of (uuid, name) tuples for categories in that community.
    """
    community_groups = defaultdict(list)
    for uuid, name, community in categories:
        community_groups[community].append((uuid, name))
    return community_groups

def process_community(community_nodes: List[tuple], word_similarity: float) -> set:
    """
    Process a community of nodes to find similar pairs based on name similarity.

    Args:
        community_nodes (List[tuple]): A list of (uuid, name) tuples for nodes in a community.
        word_similarity (float): The similarity threshold for considering two names as similar.

    Returns:
        set: A set of tuples, each containing UUIDs of similar node pairs.

    This function uses fuzzy string matching to identify similar category names within a community,
    returning pairs of UUIDs for categories that are considered similar based on the given threshold.
    """
    name_to_uuids = defaultdict(set)
    names = []
    for uuid, name in community_nodes:
        if not uuid or not name:
            continue
        lower_name = name.lower()
        name_to_uuids[lower_name].add(uuid)
        names.append(lower_name)

    score_cutoff = word_similarity * 100

    similar_pairs = set()
    for idx1, name1 in enumerate(names):
        matches = process.extract(
            name1,
            names,
            scorer=fuzz.WRatio,
            score_cutoff=score_cutoff,
            processor=None,
            limit=None
        )
        for match_name, score, idx2 in matches:
            if idx1 >= idx2:
                continue
            uuids1 = name_to_uuids[name1]
            uuids2 = name_to_uuids[match_name]
            for uuid1 in uuids1:
                for uuid2 in uuids2:
                    if uuid1 == uuid2:
                        continue
                    pair = tuple(sorted((uuid1, uuid2)))
                    similar_pairs.add(pair)
    return similar_pairs

def entity_resolution(entities: List[str], extraction_chain) -> Optional[Dict[str, List[str]]]:
    """
    Process a list of entities to identify and merge duplicates using an extraction chain.

    Args:
        entities (List[str]): The list of original entity names.
        extraction_chain: The extraction chain object responsible for invoking the LLM.

    Returns:
        Optional[Dict[str, List[str]]]: A dictionary mapping merged entities to lists of original entities,
        or None if an error occurs.

    This function uses a language model to identify and group similar entities, handling potential
    duplicates or variations of the same entity.
    """
    try:
        entities_str = json.dumps(entities, ensure_ascii=False)
        logging.debug(f"Entities JSON String: {entities_str}")

        response = extraction_chain.invoke({"entities": entities_str})
        logging.debug(f"Extraction Chain Response: {response}")

        if 'entities' not in response or 'text' not in response:
            logging.error(f"Response is missing required fields. Response: {response}")
            return None

        merged_dict_str = response.get('text')
        if not merged_dict_str:
            logging.error("The 'text' field is empty in the response.")
            return None

        logging.debug(f"Merged Dictionary String: {merged_dict_str}")

        merged_dict = json.loads(merged_dict_str)
        logging.debug(f"Merged Dictionary: {merged_dict}")

        if not isinstance(merged_dict, dict):
            logging.error(f"Merged dictionary is not a dictionary. Got type: {type(merged_dict)}")
            return None

        return merged_dict
    except json.JSONDecodeError as e:
        logging.error(f"JSON decoding failed: {e}")
        return None
    except Exception as e:
        logging.error(f"Error during entity resolution: {e}")
        return None

def normalize_name(name: str) -> str:
    """
    Normalize the name of an entity.

    Args:
        name (str): The original name of the entity.

    Returns:
        str: The normalized name.

    This function standardizes entity names by converting to lowercase,
    stripping whitespace, and replacing underscores and hyphens with spaces.
    """
    return name.strip().lower().replace('_', ' ').replace('-', ' ')

def prepare_string(data: Dict) -> str:
    """
    Prepare a string representation of nodes and relationships data.

    Args:
        data (Dict): A dictionary containing 'nodes' and 'rels' keys with corresponding data.

    Returns:
        str: A formatted string representation of the nodes and relationships.

    This function creates a human-readable string representation of graph data,
    including node information (name, type, description) and relationship information
    (start node, end node, relationship type, description).
    """
    nodes_str = "Nodes are:\n"
    for node in data['nodes']:
        node_id = node['name']
        node_type = node['type']
        node_description = f", description: {node['description']}" if 'description' in node and node['description'] else ""
        nodes_str += f"name: {node_id}, type: {node_type}{node_description}\n"

    rels_str = "Relationships are:\n"
    for rel in data['rels']:
        start = rel['start']
        end = rel['end']
        rel_type = rel['type']
        description = f", description: {rel['description']}" if 'description' in rel and rel['description'] else ""
        rels_str += f"({start})-[:{rel_type}]->({end}){description}\n"

    return nodes_str + "\n" + rels_str


def is_blocker_signal(incoming_text, blocker_json_path, similarity_threshold=0.9):
    """
    Determines if the incoming_text is a signal for a blocker based on Levenshtein similarity.

    Args:
        incoming_text (str): The text string to be evaluated.
        blocker_json_path (str): Path to the JSON file containing blocker strings.
        similarity_threshold (float, optional): Threshold for similarity (0 to 1). Defaults to 0.9.

    Returns:
        bool: True if incoming_text is similar to any blocker string above the threshold, else False.
    """
    try:
        # Load blocker strings from the JSON file
        with open(blocker_json_path, 'r', encoding='utf-8') as file:
            blocker_data = json.load(file)
            blocker_strings = blocker_data.get("blockers", [])
    except FileNotFoundError:
        print(f"Error: The file {blocker_json_path} was not found.")
        return True
    except json.JSONDecodeError:
        print(f"Error: The file {blocker_json_path} is not a valid JSON.")
        return True

    # Iterate through each blocker string and compute similarity
    for blocker in blocker_strings:
        lev_distance = distance(incoming_text, blocker)
        max_len = max(len(incoming_text), len(blocker))
        
        # Avoid division by zero
        if max_len == 0:
            similarity = 1.0
        else:
            similarity = 1 - (lev_distance / max_len)
        
        # Debug: Print comparison details (optional)
        # print(f"Comparing '{incoming_text}' with '{blocker}': Similarity = {similarity:.2f}")
        
        if similarity >= similarity_threshold:
            return True  # Incoming text is similar enough to a blocker string

    return False  # No blocker strings matched above the threshold