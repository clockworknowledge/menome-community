from typing import List, Optional, Dict
from fastapi import APIRouter, Body, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

import pandas as pd
import numpy as np

from langchain_community.vectorstores import Neo4jVector
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain.chains import LLMChain
from langchain_core.output_parsers import StrOutputParser

import json
import networkx as nx
from graphdatascience import GraphDataScience
from neo4j.exceptions import ClientError, ResultConsumedError
from neo4j import GraphDatabase

from backend.config import CurrentConfig
from backend.dependencies.auth import get_current_user, User
from backend.services.similarity_services import prepare_string,extract_categories, group_by_community, process_community, entity_resolution, remove_loop_relationships, remove_duplicate_relationships, remove_reverse_duplicate_relationships, normalize_name

router = APIRouter()
# Configure logging
logging.basicConfig(level=CurrentConfig.LOG_LEVEL)
logger = logging.getLogger(__name__)


@router.get("/initialize-index",
                summary="Initialize the category index",
                description="""
    Initializes the similarity index for the categories in the Neo4j graph database.

    This endpoint performs the following operations:
    1. Creates a Neo4jVector object using the existing graph structure.
    2. Utilizes OpenAI's embedding model to generate embeddings for Category nodes.
    3. Configures the vector to use the 'name' property of Category nodes for text representation.
    4. Sets up the 'embedding' property to store the generated embeddings.
    5. Creates an index named 'Category' for efficient similarity searches.

    The similarity index allows for fast and accurate retrieval of similar categories
    based on their semantic meaning, enabling advanced search and recommendation features.

    Note:
    - This operation may take some time depending on the number of Category nodes in the database.
    - Ensure that the Neo4j database is properly configured and accessible.
    - The OpenAI API key should be set up correctly in the environment for embedding generation.

    Returns:
        JSONResponse: A JSON object with a success message and a 200 status code.

    Raises:
        HTTPException: If there's an error during the index initialization process.
    """,
                tags=["Categories"])
def initializeIndex(current_user: User = Depends(get_current_user)):
    """
    Initialize the similarity index
    """
    vector = Neo4jVector.from_existing_graph(
        OpenAIEmbeddings(),
        node_label='Category',
        text_node_properties=['name'],
        embedding_node_property='embedding',
        index_name='Category'
    )

    return JSONResponse(content={"message": "Similarity index initialized"}, status_code=200)




@router.get("/deduplicate",
             summary="Detect and merge similar categories",
             description="""
    Performs advanced similarity detection and deduplication of categories using a multi-step approach:

    1. Graph Projection: Projects a graph of Category nodes with their embeddings.
    2. KNN Algorithm: Applies K-Nearest Neighbors to detect similar categories based on embedding similarity.
    3. Weakly Connected Components (WCC): Groups similar categories into communities.
    4. Jaro-Winkler Distance: Further refines similarity within communities using string similarity.
    5. LLM-based Entity Resolution: Employs a language model to make final decisions on merging categories.
    6. Neo4j Merging: Executes the merging of similar categories in the Neo4j database.
    7. Relationship Cleanup: Removes duplicate and loop relationships post-merging.

    This approach combines graph algorithms, string similarity, and AI-driven decision-making to achieve
    high-quality category deduplication while preserving the integrity of the knowledge graph structure.

    Parameters:
    - similarity_cutoff (float): Threshold for embedding-based similarity in KNN algorithm. 
      Range: 0 to 1, where higher values indicate stricter similarity criteria.
    - word_similarity (float): Threshold for Jaro-Winkler distance in string comparison. 
      Range: 0 to 1, where lower values indicate higher similarity.
    - current_user (User): The authenticated user making the request.

    Returns:
    - JSONResponse: Contains the number of merged categories and a success message.

    Note: This operation can be computationally intensive and may take some time to complete,
    especially for large category sets.
    """,
             tags=["Categories"])
def similarCategories(similarity_cutoff: float = Query(default=0.955, description="The cutoff threshold for embedding-based similarity used in community detection. Nodes with similarity above this threshold will be considered for the same community"), 
                      word_similarity: float = Query(default=0.05, description="The similarity threshold for fuzzy matching. Pairs with a similarity score above this threshold (when multiplied by 100) will be considered similar. 1.0 means only exact matches, 0.0 means all pairs match. Example: 0.85 would match 'band' and 'bands'."),
                      current_user: User = Depends(get_current_user)):
    """
    Detect and resolve similarity between categories
    """
    logger.info("Starting similarity detection and resolution process.")
    logger.info(f"Using similarity cutoff: {similarity_cutoff}")
    logger.info(f"Using word edit distance: {word_similarity}")

    # Setup graph data science connection
    gds = GraphDataScience(CurrentConfig.NEO4J_URI, auth=(CurrentConfig.NEO4J_USER, CurrentConfig.NEO4J_PASSWORD))
    G = None

    try:
        logger.info("Projecting the graph for similarity detection.")
        try:
            G, result = gds.graph.project(
                "entities",                   # Graph name
                "Category",                 # Node projection
                "*",                          # Relationship projection
                nodeProperties=["embedding"]  # Configuration parameters
            )
        except ClientError as e:
            if "A graph with name 'entities' already exists" in str(e):
                logger.warning("Graph 'entities' already exists. Dropping and recreating the projection.")
                gds.graph.drop("entities", False)
                G, result = gds.graph.project(
                    "entities",                   # Graph name
                    "Category",                 # Node projection
                    "*",                          # Relationship projection
                    nodeProperties=["embedding"]  # Configuration parameters
                )
            else:
                logger.error(f"An unexpected error occurred: {e}")
                raise

        logger.info("Running KNN algorithm to detect similar categories.")
        gds.knn.mutate(
            G,
            nodeProperties=['embedding'],
            mutateRelationshipType='SIMILAR',
            mutateProperty='score',
            similarityCutoff=similarity_cutoff
        )

        logger.info("Writing the similarity results back to the graph.")
        gds.wcc.write(
            G,
            writeProperty="wcc",
            relationshipTypes=["SIMILAR"]
        )

        logger.info("Querying potential duplicate candidates.")

        categories = extract_categories(CurrentConfig.NEO4J_URI, CurrentConfig.NEO4J_USER, CurrentConfig.NEO4J_PASSWORD)
        logger.info(f"Found {len(categories)} categories.")

        logger.info("Grouping categories by community.")
        community_groups = group_by_community(categories)
        logger.info(f"Found {len(community_groups)} community groups.")
        
        similar_groups = set()
        for community, nodes in community_groups.items():
            if len(nodes) <= 1:
                continue
            similar_pairs = process_community(nodes, word_similarity)
            similar_groups.update(similar_pairs)

        logger.info(f"Found {len(similar_groups)} potential duplicate pairs.")

        logger.info("Processing potential duplicates using LLM.")

        # Build UUID to name mapping
        uuid_to_name = {uuid: name for uuid, name, _ in categories}

        # Build graph from similar pairs
        G_similar = nx.Graph()
        G_similar.add_edges_from(similar_groups)

        # Find connected components (clusters)
        clusters = list(nx.connected_components(G_similar))

        logger.info(f"Found {len(clusters)} clusters.")

        # Define the LLM
        extraction_llm = ChatOpenAI(
            model_name=CurrentConfig.OPENAI_EXTRACTION_MODEL,
            temperature=0.0,
            max_tokens=1000
        )

        system_prompt = """You are a data processing assistant. Your task is to identify duplicate entities in a list and decide which of them should be merged.
        The entities might be slightly different in format or content, but essentially refer to the same thing. Use your analytical skills to determine duplicates.

        Here are the rules for identifying duplicates:
        1. Entities with minor typographical differences should be considered duplicates.
        2. Entities with different formats but the same content should be considered duplicates.
        3. Entities that refer to the same real-world object or concept, even if described differently, should be considered duplicates.
        4. If it refers to different numbers, dates, or products, do not merge results.

        Your response should be a JSON array containing the merged list of entities, without any additional text. that the 'text' field is a valid JSON object without any additional explanations or text.
        """

        user_template = """Here is the list of entities to process (in JSON format):
            {entities}

            Please identify duplicates, merge them, and provide the merged results in JSON format as a mapping from the merged entity to a list of original entities.

            Example output:
            {{
            "merged entity 1": ["original entity 1", "original entity 2"],
            "merged entity 2": ["original entity 3"],
            ...
            }}

            Your response should only be the JSON object, and not include any additional text."""



        # Create message prompt templates
        system_message_prompt = SystemMessagePromptTemplate.from_template(system_prompt)
        human_message_prompt = HumanMessagePromptTemplate.from_template(user_template)

        # Combine into a chat prompt
        chat_prompt = ChatPromptTemplate.from_messages([system_message_prompt, human_message_prompt])

        # Create the LLM chain
        extraction_chain = LLMChain(
            llm=extraction_llm,
            prompt=chat_prompt
        )

        # Process duplicate entities in parallel
        MAX_WORKERS = 10  # Adjust based on system : TODO: make this dynamic based on the number of clusters and/or move to config
        merged_entities = []
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = [
                executor.submit(
                    entity_resolution,
                    [uuid_to_name[uuid] for uuid in cluster],
                    extraction_chain
                )
                for cluster in clusters
            ]

            for future in tqdm(
                as_completed(futures), total=len(futures), desc="Processing clusters"
            ):
                merged_dict = future.result()
                if merged_dict:
                    merged_entities.append(merged_dict)

        logger.info(f"Total merged entities: {len(merged_entities)}")

        # process the merged entities in batches to neo4j 
        # Constants and configurations
        MERGE_BATCH_SIZE = 20
        uri = CurrentConfig.NEO4J_URI
        user = CurrentConfig.NEO4J_USER
        password = CurrentConfig.NEO4J_PASSWORD

        # Initialize Neo4j driver
        driver = GraphDatabase.driver(uri=uri, auth=(user, password))
        merged_count = 0  # Initialize merged_count

        with driver.session() as session:
            for i in range(0, len(merged_entities), MERGE_BATCH_SIZE):
                batch = merged_entities[i:i + MERGE_BATCH_SIZE]
                uuids_batches = []
                for merged_dict in batch:
                    # Ensure merged_dict is a dictionary
                    if isinstance(merged_dict, dict):
                        for merged_entity, original_names in merged_dict.items():
                            logger.debug(f"Processing merged entity '{merged_entity}' with original names {original_names}")
                            uuids_to_merge = []
                            for original_name in original_names:
                                # Normalize the name
                                original_name_normalized = normalize_name(original_name)
                                # Find UUIDs corresponding to the original names
                                uuids = [
                                    uuid for uuid, name in uuid_to_name.items()
                                    if normalize_name(name) == original_name_normalized
                                ]
                                if not uuids:
                                    logger.warning(f"No UUID found for original name: '{original_name}'")
                                uuids_to_merge.extend(uuids)
                            uuids_to_merge = list(set(uuids_to_merge))  # Remove duplicates
                            logger.debug(f"Collected UUIDs to merge: {uuids_to_merge}")
                            if len(uuids_to_merge) > 1:
                                logger.debug(f"Merging UUIDs {uuids_to_merge} for merged entity '{merged_entity}'")
                                uuids_batches.append(uuids_to_merge)
                            else:
                                logger.debug(f"No merge needed for merged entity '{merged_entity}'")
                    else:
                        logger.error(f"Expected a dictionary for merged_dict, got {type(merged_dict)}")
                        continue  # Skip if merged_dict is not a dict

                if not uuids_batches:
                    logger.debug(f"No nodes to merge in batch {i//MERGE_BATCH_SIZE + 1}")
                    continue  # No nodes to merge in this batch

                params = {'uuids_batches': uuids_batches}

                # Run the merge query
                try:
                    result = session.run("""
                        UNWIND $uuids_batches AS uuids
                        MATCH (n:Category)
                        WHERE n.uuid IN uuids
                        WITH collect(n) AS nodes
                        WHERE size(nodes) > 1
                        CALL apoc.refactor.mergeNodes(nodes, {properties: 'discard'})
                        YIELD node
                        RETURN count(node) AS merged_count
                    """, params)

                    record = result.single()
                    if record:
                        batch_merged_count = record.get("merged_count", 0)
                        merged_count += batch_merged_count
                        logger.info(f"Merged {batch_merged_count} nodes in this batch. Total nodes merged so far: {merged_count}")
                    else:
                        logger.debug(f"No merges performed in this batch.")

                except Exception as e:
                    logger.error(f"Error during merge operation: {e}")

        driver.close()

        logger.info(f"Total nodes merged: {merged_count}")

        # clean loop relationships that emerge from the de-duplication:
        remove_loop_relationships(CurrentConfig.NEO4J_URI, CurrentConfig.NEO4J_USER, CurrentConfig.NEO4J_PASSWORD)
        remove_duplicate_relationships(CurrentConfig.NEO4J_URI, CurrentConfig.NEO4J_USER, CurrentConfig.NEO4J_PASSWORD)
        remove_reverse_duplicate_relationships(CurrentConfig.NEO4J_URI, CurrentConfig.NEO4J_USER, CurrentConfig.NEO4J_PASSWORD)

        logger.info(f"Successfully merged {merged_count} categories.")

        return JSONResponse(content={
            "message": "Similarity between categories detected and resolved",
            "merged_count": merged_count
        }, status_code=200)
    
    except Exception as e:
        logger.error(f"An error occurred during the operation: {e}")
        raise

    finally:
        if G:
            logger.info("Dropping the graph projection.")
            G.drop()
        if gds:
            logger.info("Closing the Neo4j driver connection.")
            gds.close()



from neo4j import GraphDatabase

@router.get("/generate-communities",
            summary="Generates communities from category nodes",
            description="""
    Generates community clusters from category nodes using graph algorithms.

    This function performs the following steps:
    1. Projects a graph named "communities" using Category nodes and all relationships.
    2. Runs the Weakly Connected Components (WCC) algorithm to analyze the graph structure.
    3. Applies the Leiden algorithm for community detection, storing results in the 'communities' property.
    4. Generates a hierarchical community structure in the graph database.
    5. Calculates and sets a community rank based on the number of associated documents.
    6. Computes statistics on community sizes at different hierarchical levels.

    The approach:
    - Uses Neo4j's Graph Data Science library for efficient graph algorithms.
    - Employs the Leiden algorithm, known for its effectiveness in detecting communities in large networks.
    - Creates a hierarchical community structure, allowing for multi-level analysis of category clusters.
    - Calculates community ranks to identify the most significant communities based on document associations.
    - Provides detailed statistics on community sizes, including percentiles, to give insights into the cluster distribution.

    Returns:
        JSONResponse: A JSON object containing a success message and percentile statistics of community sizes at each level.

    Raises:
        HTTPException: If an error occurs during the clustering process.

    Note:
        This function requires appropriate Neo4j setup with Graph Data Science library and 
        assumes the existence of Category nodes with appropriate properties in the graph database.
    """,
            tags=["Categories"])
def clusterCategories(current_user: User = Depends(get_current_user)):
    
    
    logger.info("Starting clustering process.")
   

    # Setup graph data science connection
    gds = GraphDataScience(CurrentConfig.NEO4J_URI, auth=(CurrentConfig.NEO4J_USER, CurrentConfig.NEO4J_PASSWORD))
    driver = GraphDatabase.driver(CurrentConfig.NEO4J_URI, auth=(CurrentConfig.NEO4J_USER, CurrentConfig.NEO4J_PASSWORD))
    G = None
    try:
        G, result = gds.graph.project(
            "communities",  #  Graph name
            "Category",  #  Node projection
            {
                "_ALL_": {
                    "type": "*",
                    "orientation": "UNDIRECTED",
                    "properties": {"weight": {"property": "*", "aggregation": "COUNT"}},
                }
            },
        )
        wcc = gds.wcc.stats(G)
        logging.info(f"Component count: {wcc['componentCount']}")
        logging.info(f"Component distribution: {wcc['componentDistribution']}")

        gds.leiden.write(
            G,
            writeProperty="communities",
            includeIntermediateCommunities=True,
            relationshipWeightProperty="weight",
        )

        # TODO: Produce modulatriy - write to graph - take average of communities
        # produces result metrics that alllow for determining if communities are representative of the overall
        # category domain 
        # Get key stats for initial graph of communities
        # Track this over time - 
        # always write back the modulatriy score 
        # Generate hierarchy 
        with driver.session() as session:
            session.run("""
                MATCH (e:Category)
                UNWIND range(0, size(e.communities) - 1 , 1) AS index
                CALL {
                    WITH e, index
                    WITH e, index
                    WHERE index = 0
                    MERGE (c:Community {name: toString(index) + '-' + toString(e.communities[index])})
                    ON CREATE SET c.level = index
                    MERGE (e)-[:IN_COMMUNITY]->(c)
                    RETURN count(*) AS count_0
                }
                CALL {
                    WITH e, index
                    WITH e, index
                    WHERE index > 0
                    MERGE (current:Community {name: toString(index) + '-' + toString(e.communities[index])})
                    ON CREATE SET current.level = index
                    MERGE (previous:Community {name: toString(index - 1) + '-' + toString(e.communities[index - 1])})
                    ON CREATE SET previous.level = index - 1
                    MERGE (previous)-[:IN_COMMUNITY]->(current)
                    RETURN count(*) AS count_1
                }
                RETURN count(*)
                """)
        
        # set community rank
        with driver.session() as session:
            session.run("""
                MATCH (c:Community)<-[:IN_COMMUNITY*]-(:Category)<-[:MENTIONS]-(d:Document)
                WITH c, count(distinct d) AS rank
                SET c.community_rank = rank;
                """)
        
        # Execute the query to get community sizes
        with driver.session() as session:
            result = session.run(
                """
                MATCH (c:Community)<-[:IN_COMMUNITY*]-(e:Category)
                WITH c, count(distinct e) AS entities
                RETURN split(c.name, '-')[0] AS level, entities
                """
            )
            community_size = result.data()  # Collect all data before processing

        # Convert the query result to a DataFrame
        community_size_df = pd.DataFrame(community_size)

        # Initialize list to hold percentile data
        percentiles_data = []

        # Calculate percentiles for each unique level
        for level in community_size_df["level"].unique():
            subset = community_size_df[community_size_df["level"] == level]["entities"]
            num_communities = len(subset)
            percentiles = np.percentile(subset, [25, 50, 75, 90, 99])
            percentiles_data.append({
                "Level": level,
                "Number of communities": num_communities,
                "25th Percentile": percentiles[0],
                "50th Percentile": percentiles[1],
                "75th Percentile": percentiles[2],
                "90th Percentile": percentiles[3],
                "99th Percentile": percentiles[4],
                "Max": max(subset)
            })

        # Convert the percentile data to a JSON object
        percentiles_json = json.dumps(percentiles_data, indent=4)

        # Return the JSON object
        logger.info(percentiles_json)
        return JSONResponse(content={"message": "Community clustering completed", "percentiles": percentiles_json}, status_code=200)
  
    
    except ResultConsumedError as e:
        logger.error(f"Error: Result was consumed prematurely: {str(e)}")
        raise HTTPException(status_code=500, detail="An error occurred while processing query results")
    except Exception as e:
        logger.error(f"An error occurred during the operation: {str(e)}")
        logger.exception("Detailed traceback:")
        raise HTTPException(status_code=500, detail=f"An error occurred during community clustering: {str(e)}")

    finally:
        if G:
            logger.info("Dropping the graph projection.")
            G.drop()
        if gds:
            logger.info("Closing the Neo4j driver connection.")
            gds.close()
        if driver:
            driver.close()





from neo4j import GraphDatabase

@router.post("/generate-summaries-for-communities",
            summary="Generate summaries for category communities",
            description="""
    Generates natural language summaries for communities of categories based on their similarity and clustering.

    This endpoint performs the following steps:
    1. Retrieves community information from the Neo4j graph database for specified community levels.
    2. For each community:
       a. Extracts nodes (categories) and their relationships within the community.
       b. Prepares a structured representation of the community's graph structure.
       c. Uses a language model (LLM) to generate a natural language summary of the community.
    3. Stores the generated summaries back in the Neo4j database.

    The approach:
    - Utilizes Neo4j's graph querying capabilities to extract relevant community data.
    - Employs parallel processing with ThreadPoolExecutor for efficient summary generation.
    - Leverages OpenAI's language model for generating coherent and contextual summaries.
    - Uses a custom prompt template to guide the LLM in generating appropriate summaries.
    - Implements error handling and logging for robust operation.

    Key components:
    - Neo4jGraph: For interacting with the Neo4j database.
    - ChatOpenAI: The language model used for summary generation.
    - ChatPromptTemplate: Custom prompt for guiding the LLM.
    - ThreadPoolExecutor: For parallel processing of communities.

    Parameters:
    - levels_to_summarize (list[int]): The community levels to be summarized.
    - current_user (User): The authenticated user making the request.

    Returns:
    - JSONResponse: Contains a success message and the generated summaries.

    Note: This operation can be computationally intensive for large numbers of communities or complex graph structures.
    The quality of summaries depends on the configured language model and the structure of the category communities.
    """,
            tags=["Categories"])
async def summarizeCategories(levels_to_summarize: list[int] = Body(default=[0, 1, 2, 3], description="List of levels to summarize"), current_user: User = Depends(get_current_user)):
    
    llm = ChatOpenAI(temperature=0, model_name=CurrentConfig.OPENAI_CHAT_MODEL, openai_api_key=CurrentConfig.OPENAI_API_KEY)

    logger.info("Starting category summarization process.")
    logger.info(f"Summarizing levels: {levels_to_summarize}")
    
    driver = GraphDatabase.driver(CurrentConfig.NEO4J_URI, auth=(CurrentConfig.NEO4J_USER, CurrentConfig.NEO4J_PASSWORD))
    
    try:
        with driver.session() as session:
            # Execute the query to get community information
            result = session.run(
                """
                MATCH (c:Community)<-[:IN_COMMUNITY*]-(e:Category)
                WHERE c.level IN $levels
                WITH c, collect(e) AS nodes
                WHERE size(nodes) > 1
                CALL apoc.path.subgraphAll(nodes[0], {
                    whitelistNodes:nodes
                })
                YIELD relationships
                RETURN c.name AS communityId,
                    [n in nodes | {name: n.name, description: n.description, type: [el in labels(n) WHERE el <> 'Category'][0]}] AS nodes,
                    [r in relationships | {start: startNode(r).name, type: type(r), end: endNode(r).name, description: r.description}] AS rels
                """, 
                parameters={"levels": levels_to_summarize}
            )
            community_info = result.data()

        community_template = """Based on the provided nodes and relationships that belong to the same graph community,
        generate a natural language summary of the provided information:
        {community_info}

        Summary:"""  # noqa: E501

        community_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "Given an input triples, generate the information summary. No pre-amble.",
                ),
                ("human", community_template),
            ]
        )

        community_chain = community_prompt | llm | StrOutputParser()

        def process_community(community):
            stringify_info = prepare_string(community)
            summary = community_chain.invoke({'community_info': stringify_info})
            return {"community": community['communityId'], "summary": summary}

        summaries = []
        with ThreadPoolExecutor() as executor:
            futures = {executor.submit(process_community, community): community for community in community_info}

            for future in tqdm(as_completed(futures), total=len(futures), desc="Processing communities"):
                summaries.append(future.result())

        # log number of summaries
        logger.info(f"Number of summaries: {len(summaries)}")
        logger.info(f"Summaries: {summaries}")

        # Store summaries
        with driver.session() as session:
            session.run("""
            UNWIND $data AS row
            MERGE (c:Community {name:row.community})
            SET c.summary = row.summary
            """, parameters={"data": summaries})

        return JSONResponse(content={"message": "Category summarization completed", "community_info": summaries}, status_code=200)
    except Exception as e:
        logger.error(f"An error occurred during the operation: {e}")
        raise HTTPException(status_code=500, detail=f"An error occurred during category summarization: {str(e)}")
    finally:
        driver.close()




