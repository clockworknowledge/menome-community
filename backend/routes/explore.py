from fastapi import APIRouter, HTTPException, Query, Body
from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel

import logging 
import time
import sys
import json

from neo4j import GraphDatabase
from fastapi import Depends

from backend.dependencies.auth import get_current_user, User
from backend.config import CurrentConfig
from backend.schemas.document import FindRequest
router = APIRouter()

validTypes = CurrentConfig.VALID_TYPES



from backend.tools.find_tools import tools_available
from langchain.schema import SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import START, StateGraph
from langgraph.prebuilt import tools_condition
from langgraph.prebuilt import ToolNode
from IPython.display import Image, display

from langgraph.graph import MessagesState
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage



@router.post("/find",
             summary="Find documents using natural language request",
             description="Find documents by time range and type",
             tags=["Explore"])
async def find_documents(find_request: FindRequest = Body(...), current_user: User = Depends(get_current_user)):
    start_time = time.time()
    llm = ChatOpenAI(model='gpt-4-turbo')

    tools = tools_available
    llm_with_tools = llm.bind_tools(tools)
    current_date = datetime.now().strftime('%Y-%m-%d')
 # System message
    sys_msg = SystemMessage(content=f"""You are a helpful assistant tasked with finding and returning relevant information about documents. 
            You will receive user requests that may include date-related instructions in natural language.
            
            Your responsibilities include:
            1. **Interpreting Date Ranges:** Accurately infer the `start_date` and `end_date` based on the user's request:
               - For specific months (e.g., "October 2023"): Use the FIRST day of the NEXT month as `end_date`
               - For relative dates (e.g., "past two weeks"): Use current date as `end_date`
               - Default to inclusive date ranges
            
            2. **Date Format Examples:**
               - "notes from October 2023":
                 - start_date: 2023-10-01
                 - end_date: 2023-11-01
                 - document_type: "Note"
               - "past two weeks":
                 - end_date: {current_date}
                 - start_date: {(datetime.now() - timedelta(weeks=2)).strftime('%Y-%m-%d')}
            
            3. **Important Rules:**
               - For month queries, ALWAYS set end_date to the first day of the next month
               - Use strict YYYY-MM-DD format for dates
               - Ensure start_date is before end_date
               - Default to UTC timezone unless specified
               - Use simple string values for document_type
            """)


    # Node
    def assistant(state: MessagesState):
        return {"messages": [llm_with_tools.invoke([sys_msg] + state["messages"])]}

    # Graph
    builder = StateGraph(MessagesState)

    # Define nodes: these do the work
    builder.add_node("assistant", assistant)
    builder.add_node("tools", ToolNode(tools))

    # Define edges: these determine how the control flow moves
    builder.add_edge(START, "assistant")
    builder.add_conditional_edges(
        "assistant",
        # If the latest message (result) from assistant is a tool call -> tools_condition routes to tools
        # If the latest message (result) from assistant is a not a tool call -> tools_condition routes to END
        tools_condition
    )
    builder.add_edge("tools", "assistant")
    react_graph = builder.compile()

    messages = [
        HumanMessage(
            content=find_request.query
        )
    ]

    messages = react_graph.invoke({"messages": messages})
    setup_time = time.time()

    # Extract ToolMessage content and log other messages
    nodes_data = []
    for message in messages["messages"]:
        if isinstance(message, ToolMessage):
            if isinstance(message.content, str):
                try:
                    tool_content = json.loads(message.content)
                except json.JSONDecodeError:
                    tool_content = message.content
            else:
                tool_content = message.content
            
            if isinstance(tool_content, list):
                nodes_data.extend(tool_content)
            else:
                nodes_data.append(tool_content)
        else:
            logging.debug(f"Message: {message}")

    nodes_data_payload = json.dumps(nodes_data).encode('utf-8')
    nodes_data_payload_size = sys.getsizeof(nodes_data_payload)

    # Measure time after fetching data from Neo4j
    neo4j_fetch_time = time.time()

    # Calculate elapsed times
    setup_duration = setup_time - start_time
    response_duration = 0
    fetch_duration = neo4j_fetch_time 
    total_duration = neo4j_fetch_time - start_time
    
    return {
        "answer": "",
        "sources": nodes_data,
        "timings": {
            "setup_duration": setup_duration,
            "langchain_response_duration": response_duration,
            "neo4j_fetch_duration": fetch_duration,
            "total_duration": total_duration
        },
        "payload_sizes": {
            "request_size": len(find_request.query),
            "response_size": len(json.dumps(nodes_data)),
            "db_response_size": nodes_data_payload_size
        }
    }


