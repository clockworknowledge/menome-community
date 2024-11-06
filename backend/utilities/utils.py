from langchain.chains.summarize import load_summarize_chain
from langchain_community.chat_models import ChatOpenAI
from langchain.docstore.document import Document

from backend.config import CurrentConfig

## fetches node properties by uuid
def fetch_node_properties_by_uuid(driver, uuids: list):
    output = []
    with driver.session() as session:
        # Query to fetch specific node properties based on UUIDs
        query = """
            MATCH (d:Document)-[]-(p:Page)-[]-(c:Child)
            WHERE c.uuid IN $uuids 
            OPTIONAL MATCH (p)-[]-(q:Question)
            OPTIONAL MATCH (p)-[]-(s:Summary)

            WITH d, p, 
                collect(DISTINCT {uuid: q.uuid, name: q.name, text: q.text}) AS questions,
                collect(DISTINCT {uuid: s.uuid, name: s.name, text: s.text}) AS summaries,
                collect(DISTINCT {uuid: c.uuid, name: c.name, text: c.text}) AS children
            ORDER BY d.name, toInteger(replace(p.name, 'Page ', ''))

            WITH d,
                collect({
                    uuid: p.uuid, 
                    name: p.name, 
                    summaries: summaries, 
                    questions: questions, 
                    children: children
                }) AS pages
            RETURN 
                d.uuid AS doc_uuid, d.name AS doc_name, toString(d.addeddate) AS doc_addeddate, 
                d.imageurl AS doc_imageurl, d.publisher AS doc_publisher, 
                d.thumbnail AS doc_thumbnail, d.url AS doc_url, d.wordcount AS doc_wordcount,
                pages

        """
        results = session.run(query, uuids=uuids)
            
        
        for record in results:
            # Structuring the output
            document_data = {
                "uuid": record["doc_uuid"],
                "name": record["doc_name"],
                "addeddate": record["doc_addeddate"],
                "imageurl": record["doc_imageurl"],
                "publisher": record["doc_publisher"],
                "thumbnail": record["doc_thumbnail"],
                "url": record["doc_url"],
                "wordcount": record["doc_wordcount"]
            }

            pages_data = record["pages"]

            output.append({
                "document": document_data,
                "pages": pages_data
            })

        session.close()
        # Return the output as a single JSON-formatted object
        return output


## generates a summary of text being returned
def summarize_text_with_openai(text: str) -> str:
    """Generate a summary for the given text using OpenAI."""
    llm = ChatOpenAI(temperature=0, model_name=CurrentConfig.OPENAI_CHAT_MODEL)
    #loader=langchain.document_loaders.TextLoader(text)
    docs = [Document(page_content=text)]
    # Run the summarization chain and get the summary
    chain = load_summarize_chain(llm, chain_type="stuff")
    summary = chain.run(docs)
    return summary


## checks if an index exists in the neo4j graph 
def index_exists(driver, index_name: str) -> bool:
    """Check if a given index exists in the Neo4j database."""
    query = f"""
    SHOW INDEXES
    YIELD name
    WHERE name = '{index_name}'
    RETURN name
    """
    with driver.session() as session:
        result = session.run(query).single()
        return bool(result)
    
## Sets up the graph database index
def setup_graph_db(driver, index_name, node_label="Child", property_name="embedding"):

    query = f"""
    CALL db.index.vector.createNodeIndex(
      '{index_name}',      // index name
      '{node_label},             // node label
      '{property_name}',         // node property
      1536,                // vector size
      'cosine'             // similarity metric
    )
    """

    with driver.session() as session:
        result=session.run(query)
    return True

# Define functions for adding documents, pages, and chunks to the graph
def add_document(tx, properties):
    query = (
        "CREATE (d:Document {uuid: $uuid, name: $name, title: $title, url: $url, "
        "sourceurl: $sourceurl, thumbnailurl: $thumbnailurl, text: $text}) "
        "RETURN d"
    )
    return tx.run(query, properties).single()["d"]

def add_page(tx, doc_uuid, properties):
    query = (
        "MATCH (d:Document {uuid: $doc_uuid}) "
        "CREATE (p:Page {uuid: $uuid, name: $name, text: $text}) "
        "MERGE (d)-[:HAS_PAGE]->(p) "
        "RETURN p"
    )
    return tx.run(query, {"doc_uuid": doc_uuid, **properties}).single()["p"]

def add_chunk(tx, parent_uuid, properties):
    query = (
        "MATCH (p {uuid: $parent_uuid}) "
        "CREATE (cu:Child {uuid: $uuid, name: $name,  text: $text}) "
        "MERGE (p)-[:HAS_CHILD]->(cu) "
        "with cu CALL db.create.setVectorProperty(cu, 'embedding', $embedding) YIELD node as c "
        "RETURN c"
    )
    return tx.run(query, {"parent_uuid": parent_uuid, **properties}).single()["c"]

def setupSourceChunks(tx):
    query1="""match (c:Chunk)-[]-(p:Page)-[]-(d:Document) where  c.source is null
        set c.source=p.Name + ', PDF ' + d.SourceUrl"""
    
    query2="""match (c:Chunk)-[]-(p:Page)-[]-(d:Document) 
        set c.source=p.uuid"""
    return tx.run(query2)

def compute_embedding_cost(text: str) -> float:
    tokens = len(text.split())  # Simplified tokenization by splitting on whitespace
    cost_per_thousand_tokens = 0.0001
    total_cost = (tokens / 1000) * cost_per_thousand_tokens
    return total_cost


def compute_gpt4_cost(input_text: str, output_text: str, context: str) -> float:
    tokens_input = len(input_text.split())  # Simplified tokenization by splitting on whitespace
    tokens_output = len(output_text.split())  # Simplified tokenization by splitting on whitespace
    if context == '8K':
        cost_per_thousand_tokens_input = 0.03
        cost_per_thousand_tokens_output = 0.06
    elif context == '32K':
        cost_per_thousand_tokens_input = 0.06
        cost_per_thousand_tokens_output = 0.12
    else:
        raise ValueError("Invalid context. Choose either '8K' or '32K'.")
    
    total_cost = ((tokens_input + tokens_output) / 1000) * (cost_per_thousand_tokens_input + cost_per_thousand_tokens_output)
    return total_cost


