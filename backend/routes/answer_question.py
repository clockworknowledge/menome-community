from fastapi import APIRouter, Query, Depends

import time
import logging
import json

from langchain_openai import  ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain.agents import AgentExecutor, create_react_agent

from backend.config import CurrentConfig
from backend.dependencies.auth import get_current_user, User
from backend.schemas.document import QuestionRequest
from backend.tools.answer_question_tools import (
    tools_available
)


router = APIRouter()


# Set the logging level
logger = logging.getLogger(__name__)
logging.getLogger("langchain").setLevel(logging.INFO)

# Define the prompt template
promptToolSearch = PromptTemplate.from_template("""
Answer the following questions as best you can. 
Make sure the Final Answer contains the following information:
- The full answer to the original question.
- The Tools Used to answer the question.
- The Thoughts and Observations used to answer the question.
- The sources of information used to answer the question. The source list MUST include the source name, URL, and published date.


                    
These keywords must never be translated or transformed:
- Action:
- Thought:
- Action Input:
because they are part of the thinking process instead of the output.

You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat 1 times)

Thought: I now know the final answer  
Final Answer: the Final Answer to the original input question 
Begin!

Question: {input}  
Thought: {agent_scratchpad}

                                            
""")
@router.post("/answer-question",
             summary="Chat with source references",
             description="""
             This endpoint provides a chat response along with sources of information. It uses the ChatOpenAI model for generating responses.
             
             The endpoint performs the following steps:
             1. Receives a question from the user.
             2. Utilizes a React agent with access to various tools to process the question.
             3. Generates a response that includes:
                - A full answer to the original question
                - The tools used to answer the question
                - The thoughts and observations used in the reasoning process
                - Sources of information, including source name, URL, and published date
             
             The response is structured to provide transparency in the AI's reasoning process and to cite reliable sources.
             
             Note:
             - This endpoint requires user authentication.
             - The response time may vary depending on the complexity of the question and the number of tools used.
             - The quality and relevance of the sources depend on the available tools and the AI model's capabilities.
             """,
             tags=["Explore"])
def answerQuestion(request: QuestionRequest, current_user: User = Depends(get_current_user)):
    start_time = time.time()

    question = request.query
    logging.info(f"Starting chatSourcesquestion with question: {request.query}") 

    model = ChatOpenAI(model=CurrentConfig.OPENAI_CHAT_MODEL, openai_api_key=CurrentConfig.OPENAI_API_KEY)
    # only creates the logical steps for us
    react_agent = create_react_agent(model, tools=tools_available, prompt=promptToolSearch)
   
    react_agent_executor = AgentExecutor(
        agent=react_agent, tools=tools_available, verbose=True, handle_parsing_errors=True, return_intermediate_steps= True, include_run_info=True
    ) 
    setup_duration = time.time() - start_time

    agent_response =  react_agent_executor.invoke({"input": request.query})
    response_duration = time.time() - setup_duration

    response = agent_response.get("output", "")
    logging.info(f"Agent response: {response}")

    total_duration = time.time() - start_time

    return {
        "question": question,
        "answer": response,
        "setup_duration": setup_duration,
        "response_duration": response_duration,
        "total_duration": total_duration
    }

