
from langchain.schema import HumanMessage
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_community.utilities.tavily_search import TavilySearchAPIWrapper
from langchain_community.vectorstores import Neo4jVector
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.chains import RetrievalQAWithSourcesChain
from langchain.agents import Tool

from backend.config import CurrentConfig
import json

def classifyQuestionTool(question: str) -> str:
    """
    Classifies a given question as either 'general' or 'specific'.

    Args:
        question (str): The question to be classified.
        model: The language model used for classification (expected to be a ChatOpenAI instance).

    Returns:
        str: The classification result, either 'general' or 'specific'.
             Returns 'general' if the classification is unsuccessful.

    Description:
        This function uses a language model to classify a question as either 'general' (broad and open-ended)
        or 'specific' (narrow and detailed). It constructs a prompt, sends it to the model,
        and interprets the response to determine the classification.
    """
    # Define the prompt to classify the question
    prompt = f"""
    Classify the following question as 'general' or 'specific'. 
    A general question is broad and open-ended, while a specific question is narrow and detailed.
    Question: "{question}"
    Classification: 
    """
    # Create a HumanMessage object
    message = HumanMessage(content=prompt)
    model = ChatOpenAI(model=CurrentConfig.OPENAI_CHAT_MODEL, openai_api_key=CurrentConfig.OPENAI_API_KEY)
    # Use the ChatOpenAI object to get the response
    response = model.invoke([message])

    # Ensure the response contains a colon before attempting to split
    if ':' in response.content:
        parts = response.content.split(':')
        if len(parts) > 1:
            classification = parts[1].strip().lower()
            if classification in ["general", "specific"]:
                return classification

    # If the expected format is not found, return "undetermined"
    return "general"
    

def general_answer_retriever(question: str):
    """
    Retrieves answers for general questions using a Neo4j vector store and a language model.

    Args:
        question (str): The general question to be answered.
        config (BaseConfig): Configuration object containing necessary API keys and database credentials.

    Returns:
        str: A string representation of the results, including the answer and source information.

    Description:
        This function sets up a Neo4j vector store with a specific retrieval query, creates a
        RetrievalQAWithSourcesChain using the OpenAI chat model, and then invokes this chain
        with the given question. It's designed to handle broader, more general questions.
    """
    
    retrieval_query = """
    WITH node, score
    MATCH (d:Document)-[]-(node)
                
                OPTIONAL MATCH (node)-[]-(q:Question)
                WITH node, score, d, 
                    collect(DISTINCT {uuid: q.uuid, name: q.name, text: q.text}) AS questions,
                    collect(DISTINCT {uuid: node.uuid, name: node.name}) AS pages
                RETURN 
                    'Name:' + node.text AS text, score, {doc_uuid:d.uuid, doc_name:d.name,doc_addeddate:d.addeddate,doc_publisher:d.publisher,doc_url:d.url,doc_wordcount:d.wordcount, pages:pages,source:d.url} 
                    AS metadata"""

    vectorstore = Neo4jVector.from_existing_index(
        OpenAIEmbeddings(openai_api_key=CurrentConfig.OPENAI_API_KEY),
        index_name="typical_rag",
        url=CurrentConfig.NEO4J_URI,
        username=CurrentConfig.NEO4J_USER,
        password=CurrentConfig.NEO4J_PASSWORD,
        text_node_property="text",
        node_label="Page",
        retrieval_query=retrieval_query,
    )

    chain = RetrievalQAWithSourcesChain.from_chain_type(
        ChatOpenAI(temperature=1, max_tokens=4096, model_name=CurrentConfig.OPENAI_CHAT_MODEL, openai_api_key=CurrentConfig.OPENAI_API_KEY),
        chain_type="stuff",
        retriever=vectorstore.as_retriever(search_kwargs={"k": 5, 'score_threshold': 0.5}),
        return_source_documents=True
    )
    results = chain.invoke({"question": question}, return_only_outputs=True)
    return str(results)


def specific_answer_retriever(question: str):
    """
    Retrieves answers for specific questions using a Neo4j vector store and a language model.

    Args:
        question (str): The specific question to be answered.
        config (BaseConfig): Configuration object containing necessary API keys and database credentials.

    Returns:
        str: A string representation of the results, including the answer and source information.

    Description:
        This function is similar to general_answer_retriever but is optimized for more specific questions.
        It uses a different retrieval query and index name in the Neo4j vector store setup. The function
        creates a RetrievalQAWithSourcesChain and invokes it with the given specific question.
    """
      
    retrieval_query = """
    WITH node, score
    MATCH (d:Document)-[]-(p:Page)-[]-(node)
                
                OPTIONAL MATCH (p)-[]-(q:Question)
                OPTIONAL MATCH (p)-[]-(s:Summary)

                WITH node, score, d, p, 
                    collect(DISTINCT {uuid: q.uuid, name: q.name, text: q.text}) AS questions,
                    collect(DISTINCT {uuid: s.uuid, name: p.name}) AS pages
                RETURN 
                    'Name:' + node.text AS text, score, {doc_uuid:d.uuid, doc_name:d.name,doc_addeddate:d.addeddate,doc_publisher:d.publisher,doc_url:d.url,doc_wordcount:d.wordcount, pages:pages,source:d.url} 
                    AS metadata"""


    vectorstore=Neo4jVector.from_existing_index(
        OpenAIEmbeddings(openai_api_key=CurrentConfig.OPENAI_API_KEY),
        index_name="parent_document",
        url=CurrentConfig.NEO4J_URI,
        username=CurrentConfig.NEO4J_USER,
        password=CurrentConfig.NEO4J_PASSWORD,
        text_node_property="text",
        node_label="Child",
        retrieval_query=retrieval_query
    )

    chain = RetrievalQAWithSourcesChain.from_chain_type(
        ChatOpenAI(temperature=1, max_tokens=4096, model_name=CurrentConfig.OPENAI_CHAT_MODEL, openai_api_key=config.OPENAI_API_KEY),
        chain_type="stuff",
        retriever=vectorstore.as_retriever(search_kwargs={"k": 5, 'score_threshold': 0.5}),
        return_source_documents=True
    )
    results = chain.invoke({"question":question},return_only_outputs=True)  
    
    return str(results)



search = TavilySearchAPIWrapper(tavily_api_key=CurrentConfig.TAVILY_API_KEY)
tavily_tool = TavilySearchResults(api_wrapper=search, max_results=5)


tools_available = [
    Tool(
        name="ClassifyQuestion",
        func=classifyQuestionTool,
        description='Use to classify the question as general or specific'
    ),
    Tool(
        name="Internal Specific Answer Search",
        func=specific_answer_retriever,
        description='Use internal specific Answer Search for searching and retrieve answers and sources for specific questions'
    ),
    Tool(
        name="Internal General Answer Search",
        func=general_answer_retriever,
        description='Use internal answer for Searching and retrieve answers and sources for general questions'
    ),
    Tool(
        name="External Search",
        func=tavily_tool,
        description='Only use External Search when internal searches dont have information to search external source for answers to question'
    ),
]