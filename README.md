# Welcome to the Menome Personal Knowledge API

Greetings, and welcome to the Menome Personal Knowledge API! This platform is designed to empower individuals to capture, curate, and manage their personal knowledge.

With recent advances in AI, we have a unique opportunity to [rethink how we engage with knowledge](https://clockworknowledge.medium.com/ai-is-the-new-os-577aa15eb905). The key objective of the project is to leverage AI to enhance people's ability to capture, organize, and maintain personal insights and memories.

## Project Goal

This project aims to create a functional toolset specifically for a close acquaintance with functional memory challenges. The goal is to help them capture and organize memories and thoughts, ultimately allowing them to utilize their accumulated knowledge to write memoirs. Consequently, the API layer has been developed with features tailored to support this specific need.

![Clockwork Knowledge Menome](documentation/images/clockworknowledge-menome.png)

## Current Focus: ChatGPT Integration

Given the urgency of this use case, development has prioritized a ChatGPT-based interface for the frontend. By integrating Menome into ChatGPT, users gain access through multiple platforms—Mac, iPhone, iPad, and more—while leveraging the extensive AI capabilities for understanding and interpreting user interactions. This approach provides wide accessibility with minimal setup, making the system available on ChatGPT apps across devices.

## Future Development

Although the initial release centers on ChatGPT integration, a more traditional frontend is planned. This current implementation, however, provides a solid foundation to meet the immediate needs of the project.


More information about the motivation and use cases for the project is available in the [documentation/project_background.md](documentation/project_background.md) file.

Currently supported features are:
The clockworKnowledge Menome API supports the following interactions:

1. **Authentication**  
   - `/auth/token` (POST): Obtain an access token for user authentication.

2. **User Management**  
   - `/users/me` (GET): Get the current authenticated user's details.  
   - `/users/add-roles` (POST): Add roles to a specific user.  
   - `/users/create` (POST): Create a new user in the database.  
   - `/users/user/{uuid}` (DELETE): Delete a user by their UUID.  
   - `/users/user/{username}` (DELETE): Delete a user by their username.

3. **Explore and Chat**  
   - `/explore/answer-question` (POST): Provides chat responses with source references for user questions.  
   - `/explore/find` (POST): Find documents based on natural language queries.

4. **File Management**  
   - `/files/upload-file` (POST): Upload a file to the MinIO storage and process it into a graph document.

5. **Document Management**  
   - `/documents/document/add-document-from-url` (POST): Add a document to the graph from a specified URL.  
   - `/documents/document/generate-share-link/{document_uuid}` (POST): Generate a shareable link for a document.  
   - `/documents/document/{uuid}` (GET): Retrieve a document by its UUID.

6. **Note Management**  
   - `/notes/note` (POST): Capture and store a note in the graph database.  
   - `/notes/upload-image-from-openai` (POST): Upload an image from OpenAI along with a note.  
   - `/notes/note/{note_id}` (GET): Retrieve a note and its associated files.

7. **Research**  
   - `/research/research-topic` (POST): Generate a research article based on provided topics.

8. **Processing**  
   - `/process/documents` (POST): Process documents into chunks.  
   - `/process/document/{document_id}` (POST): Process a single document into chunks.  
   - `/process/documents/categories` (POST): Generate categories for documents.  
   - `/process/documents/categories/{document_id}` (POST): Generate categories for a specific document.  
   - `/process/task/{task_id}` (GET): Get the status of a processing task.  
   - `/process/purge-queue` (POST): Purge all tasks in the Celery queue.

9. **Category Management**  
   - `/category/initialize-index` (GET): Initialize the category similarity index in Neo4j.  
   - `/category/deduplicate` (GET): Detect and merge similar categories.  
   - `/category/generate-communities` (GET): Generate community clusters from category nodes.  
   - `/category/generate-summaries-for-communities` (POST): Generate summaries for category communities.


## History of Menome

I have been working on the Menome platform in some form since registering the [menome.com](https://www.menome.com) domain in may 2000 - culminating with starting Menome Technologies in 2016.

Additional information is available on my [medium blog](https://medium.com/@clockworknowledge).

I am grateful to everyone who has supported the project over the years - and am particularly indebted to the Menome team and to Arcurve! I have provided some of the history and background in the [documentation/history_of_menome.md](documentation/history_of_menome.md) file.

Thanks to the following:
* [Menome Team](https://www.menome.com), Menome Advisors, Menome Customers and the Menome Community for bringing the original vision to life through the work we did on dataLink.
* [Arcurve](https://www.arcurve.com) and the Arcurve team for supporing the development of this project. 
* [Tomaz Bratanic's article series on RAG, LLMs, Langraph and neo4j](https://medium.com/@bratanic-tomaz)
* The great work that neo4j has done in the graph space. 


## Technology Stack Overview
Currently clockworKnowledge Menome is an API layer that has a set of tools for capturing, processing and retrieving knowledge contributed by the user. It is developed using FastAPI backend, Neo4j for database and vector search, MinIO object storage, RabbitMQ message broker, Celery for async processing, Flower for process monitoring and Langchain for RAG. I focused on using openAI API, ChatGPT and Tavily as initial AI model and search providers in order to expedite the development of the project. 

The front end currently leverages ChatGPT GPT application, which is provided as well. I do plan to build a proper react/nextJS front end for the platform in the future, but the immediate goal was to get a functional system up and running. I also wanted to experiment with full AI interactions rather than traditional user interface, so the GPT approach provided the most expedient path to that goal. 

* This code is provided under the MIT license as is, without any guarantees or warranties. Use at your own risk.
* It is provided for educational and research purposes only.
* The code is for single user personal knowledge management
* **The security is not production grade.**

## Prerequisites

The system is setup to be run on a single machine for development purposes using Docker Compose. It is not designed to be a distributed system. It may be possible to run additional celery workers on other machines, but I havent tested this at this time. It can be setup to be hosted on a cloud service using SSL and nginx reverse proxy to provide secured access, but I do not provide details or support for this configuration in this project. 

The system is currently setup to use chatGPT and OpenAI for LLM processing, so you will need an OpenAI API key. 

**Be aware that the processing costs can add up if you are not careful.**I monitor the costs using the openAI usage dashboard, and I set cost limits in the OpenAI account managment tool to prevent unexpected charges. 

It also uses Tavily for external search, so you will need a Tavily API key. Tavily is a paid service, but they do offer a free tier that should be sufficient for development purposes. I have not run into its limits for my use case. 

The agents are structured such that additional agents can be added to the system by adding new python modules in the backend/agents directory. 

## Stack Components

The objective of the project is to provide a flexible and extensible platform for personal knowledge management implimented as an API layer on top of a full-stack application featuring FastAPI backend, Neo4j database, MinIO object storage, and RabbitMQ message broker. A celery task queue is also used for background asyncrhonous processing of long running tasks, such as document decomposition into graph document structure. 

- **FastAPI Backend**: REST API service
- **Neo4j**: Graph database for data storage
- **MinIO**: S3-compatible object storage
- **RabbitMQ**: Message broker for async operations
- **Celery**: Task queue for background processing
- Uses Langchain for RAG, Langgraph for workflow orchestration, and OpenAI for LLM processing

## Quick Start

### 1. Environment Variables
* Create a ./neo4jdata directory in the root of the project.
* Create a ./miniodata directory in the root of the project.
* create a ./neo4jtestdata directory in the root of the project.

```bash
mkdir ./neo4jdata
mkdir ./miniodata
mkdir ./neo4jtestdata
```

Create a `.env` file in the main directory with the following variables:

```
CONFIG_VERSION=0.1.0
CONFIG_MODE=development

# Neo4j Configuration
NEO4J_URI=bolt://neo4j-dev
NEO4J_USER=neo4j
NEO4J_PASSWORD=test_neo4j_password
NEO4J_AUTH=neo4j/test_neo4j_password
NEO4J_DBMS_MEMORY_HEAP_INITIALSIZE=8G
NEO4J_DBMS_MEMORY_HEAP_MAXSIZE=8G
NEO4J_INDEX_NAME=parent_document
NEO4J_CHUNK_NODE_LABEL=Child

# OpenAI Configuration
OPENAI_API_KEYS=your-open-ai-api-key-here
EMBEDDING_DIMENSION=1536
OPENAI_CHAT_MODEL=gpt-4o
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_EXTRACTION_MODEL=gpt-4o-mini

# External Search Utilities
TAVILY_API_KEY=Tavily API Key Here

# API Config 
SECRET_KEY = asecretkeythatnoonewilleverguessinazillonyears
ALGORITHM = HS256
DOCUMENT_ACCESS_TOKEN_EXPIRE_MINUTES = 1440 
INVALIDATE_TOKEN_AFTER_USE=False
MAX_QUESTIONS_PER_PAGE =5
API_ACCESS_TOKEN_EXPIRE_MINUTES = 43200

# RabbitMQ Configuration
RABBITMQ_HOST=amqp://guest:guest@rabbit:5672//
RABBMITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest

# Minio configuration
MINIO_ENDPOINT=minio-dev:9000
MINIO_ACCESS_KEY=thelinklocal
MINIO_SECRET_KEY=boserboser
MINIO_NOTES_BUCKET=notes
MINIO_FILES_BUCKET=files
MINIO_MEMORY_BUCKET=memories
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin
MINIO_SECURE=False

# External access - localhost on local machine
MINIO_ENDPOINT_EXTERNAL=localhost:9000

# Celery Configuration
CELERY_BROKER_URL=amqp://guest:guest@localhost:5672//
CELERY_RESULT_BACKEND_URL=rpc://
CELERY_NEO4J_URL=bolt://neo4j-dev:7687
SIMILARITY_THRESHOLD=0.8
NODE_LIST=Category
RELATIONSHIP_LIST=MENTIONS
MAX_CONCURRENT_TASKS=5
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP=True

# Service information
VERSION=1.6.2
SERVICE_NAME='MenomeProcessingService'
NAME=Menome Knowledge Vault Processing API

# Environment parameters
FLOWER_HOST=localhost

# Logging parameters.
LOG_LEVEL=debug
LOG_DIAGNOSE=true
LOG_FORMAT="<level>{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<8} | {module}:{function}:{line} - {message}</level>"
FRONTEND_ORIGIN_DEV=http://localhost:3000
FRONTEND_ORIGIN_TEST=http://localhost:3000
FRONTEND_ORIGIN_PROD=https://your.domain.com

# Database Initialization
DATABASE_INITIALIZATION_ENABLED=true
ADMIN_USER_UUID=ba377768-889f-4653-aba9-16dc662648cf
ADMIN_USER_USERNAME=serviceuser
ADMIN_USER_PASSWORD=servicepassword
ADMIN_USER_EMAIL=service@user.com
ADMIN_USER_NAME=Service User

```


### 2. Start the Stack

Clone the repository and start all services using Docker Compose: 

```bash
docker compose build
docker compose up -d
```

If you need to see the logs for the services, you can use the following command:

```bash
docker compose logs -f
```

There will be a stream of output and some errors as the services start up. This is normal. The services should eventually stabilize and report in as ready. Flower in particular will report a number of errors as it starts up, but it should eventually stabilize. Neo4j typically takes the longest to start up, so wait until it reports in as **Started** before trying to initialize the system. 

```neo4j-dev        | 2024-11-05 17:22:54.512+0000 INFO  Bolt enabled on 0.0.0.0:7687.
neo4j-dev        | 2024-11-05 17:22:55.042+0000 INFO  HTTP enabled on 0.0.0.0:7474.
neo4j-dev        | 2024-11-05 17:22:55.043+0000 INFO  Remote interface available at http://localhost:7474/
neo4j-dev        | 2024-11-05 17:22:55.046+0000 INFO  id: 79BC03E7C9CA15D8877F7B9859FEA695564EB2608CE9AB514041874A5E2259C1                                                                                                                                                                                                 
neo4j-dev        | 2024-11-05 17:22:55.048+0000 INFO  name: system                                                                                                                                                                                                                                                           
neo4j-dev        | 2024-11-05 17:22:55.048+0000 INFO  creationDate: 2024-11-05T17:19:43.28Z                                                                                                                                                                                                                                  
neo4j-dev        | 2024-11-05 17:22:55.049+0000 INFO  Started.      
```

### 3. Initialize the System

With the stack running, run the initialization shell script or batch file if you are on windows to set up the database and miniostorage.

This will create the necessary buckets in MinIO and initialize the database. 
* It will create a default service user with the username "serviceuser" and the password "servicepassword".
* It creates a set of baseline role nodes. 
* It will setup base buckets in minio for notes, files, and memories. 

You will then be able to login with the service user credentials and begin adding your own content. 

```bash
./init-stack.sh
```
or for windows:
``` powershell
./init-stack.ps1
```

In neo4j [browser](http://localhost:7474), you should see a set of nodes and relationships created in the database for the base user and roles:

![alt text](documentation/images/neo4j-initialized.png)

In minio at [http://localhost:9001](http://localhost:9001), you should see the following buckets:

![alt text](documentation/images/minio-key-initialized.png)

![alt text](documentation/images/minio-bucket-initialized.png)

### 4. Access Services

Once the stack is running, you can access the following services:

#### API Documentation
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

#### MinIO Console
- URL: http://localhost:9001
- Access Key: minioadmin
- Secret Key: minioadmin

#### RabbitMQ Management Console
- URL: http://localhost:15672
- Username: guest
- Password: guest

#### Neo4j Browser
- URL: http://localhost:7474
- Connection URL: bolt://localhost:7687
- Username: neo4j
- Password: test_neo4j_password

#### Flower - Celery Process Monitoring
- URL: http://localhost:5555


## Trying out the API

The system uses basic JWT tokens for authentication. The default service user has the ADMIN role. 
SSL Certificates setup are not part of this baseline setup. The system can be secured by adding SSL certificates and nginx reverse proxy. 

First - login with the service user credentials:
* Username: serviceuser
* Password: servicepassword

Then you can use the API documentation to try out the API. 

Test the api using the get users me endpoint:
http://localhost:8000/users/me

This should return a response like the following:

```
{
  "uuid": "ba377768-889f-4653-aba9-16dc662648cf",
  "username": "serviceuser",
  "email": "service@user.com",
  "name": "Service User",
  "disabled": false,
  "datecreated": "2024-11-05T18:10:36.923000Z"
}
```

### Adding a Document using a URL

Add a document to the system using the add-document-from-url endpoint. :

https://en.wikipedia.org/wiki/As_We_May_Think

You should see a response like the following in the API documentation:

```
{
  "documentId": "129fbe30-3360-4484-84e2-4d330ac28535",
  "shareable_link": "http://localhost:3000/documents/129fbe30-3360-4484-84e2-4d330ac28535?token=hqOTXgTIKzeCjkz7vijBBg&format_type=html",
  "message": "Processing started for document 129fbe30-3360-4484-84e2-4d330ac28535",
  "task_ids": [
    "963ece35-6460-44dd-861f-f0b7cd2a172e"
  ]
} 
```

and the following response in the logs:

```

api-dev          | DEBUG:neo4j:[#D35E]  S: SUCCESS {'t_first': 5, 'fields': []}                                                                                                                                                                                                                             
api-dev          | DEBUG:neo4j:[#D35E]  _: <CONNECTION> state: READY > STREAMING                                                                                                                                                                                                                            
api-dev          | DEBUG:neo4j:[#D35E]  S: SUCCESS {'bookmark': 'FB:kcwQrIser1NPRyix0m65xBAN9ViQ', 'stats': {'contains-updates': True, 'labels-added': 1, 'relationships-created': 2, 'nodes-created': 1, 'properties-set': 5}, 'type': 'w', 't_last': 0, 'db': 'neo4j'}
api-dev          | DEBUG:neo4j:[#D35E]  _: <CONNECTION> state: STREAMING > READY                                                                                                                                                                                                                            
api-dev          | DEBUG:neo4j:[#D35E]  _: <POOL> released bolt-8                                                                                                                                                                                                                                           
api-dev          | DEBUG:backend.services.document_services:ShareToken created: hqOTXgTIKzeCjkz7vijBBg for Document: 129fbe30-3360-4484-84e2-4d330ac28535, User: ba377768-889f-4653-aba9-16dc662648cf, Expiry: 2024-11-05 19:23:30.977657+00:00, Format Type: markdown
api-dev          | DEBUG:neo4j:[#0000]  _: <POOL> close                                                                                                                                                                                                                                                     
api-dev          | DEBUG:neo4j:[#D35E]  C: GOODBYE
api-dev          | DEBUG:neo4j:[#D35E]  C: <CLOSE>                                                                                                                                                                                                                                                          
api-dev          | INFO:     172.18.0.1:40640 - "POST /documents/document/add-document-from-url HTTP/1.1" 200 OK
celery-worker-1  | [2024-11-05 18:23:31,580: INFO/ForkPoolWorker-16] HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
celery-worker-1  | [2024-11-05 18:23:31,733: INFO/ForkPoolWorker-16] processing chunk 1 of 2 for document 129fbe30-3360-4484-84e2-4d330ac28535
celery-worker-1  | [2024-11-05 18:23:32,262: INFO/ForkPoolWorker-16] HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
celery-worker-1  | [2024-11-05 18:23:33,420: INFO/ForkPoolWorker-16] HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
celery-worker-1  | [2024-11-05 18:23:34,070: INFO/ForkPoolWorker-16] HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
```

Notice the celery workers processing the document in the logs. These workers are processing the document in chunks and embedding the chunks. These processes are handled asynchronously, so the API response is quick, and that the user does not have to wait for the processing to complete before getting a response for these longer running processes. 

### File Upload:

You can also upload files to the system using the add-document-from-file endpoint. This will allow you to upload local files to the system. Currently only PDF, Doc and Docx file processing is supported. 

I have provided a test file in the documentation directory to try out the file upload endpoint: [text](<documentation/240619 Insights from Initial Implementation of the Personal Knowledge Vault.docx>)

You should see a response like the following in the API documentation:

```
{
  "documentId": "62fe3741-f206-4cb7-b37b-6e5271ca16d9",
  "message": "Processing started for 1 task(s)",
  "task_ids": [
    "f4527617-2401-4340-b351-27d6357452c3"
  ]
}
```

and the logs should show the extraction of text from the file, and storage to neo4j, followed by the celery workers processing the document in chunks. 

```
api-dev          | DEBUG:celery.utils.functional:                                                                                                                                                                                                                                                           
api-dev          | def process_text_task(self, textToProcess, documentId, generateQuestions, generateSummaries, generateCategory):                                                                                                                                                                          
api-dev          |     return 1                                                                                                                                                                                                                                                                             
rabbit           | 2024-11-05 18:40:07.847653+00:00 [info] <0.954.0> accepting AMQP connection <0.954.0> (172.18.0.6:42384 -> 172.18.0.4:5672)                                                                                                                                                              
api-dev          |                                                                                                                                                                                                                                                                                          
rabbit           | 2024-11-05 18:40:07.849698+00:00 [info] <0.954.0> connection <0.954.0> (172.18.0.6:42384 -> 172.18.0.4:5672): user 'guest' authenticated and granted access to vhost '/'                                                                                                                 
api-dev          | DEBUG:amqp:Start from server, version: 0.9, properties: {'capabilities': {'publisher_confirms': True, 'exchange_exchange_bindings': True, 'basic.nack': True, 'consumer_cancel_notify': True, 'connection.blocked': True, 'consumer_priorities': True, 'authentication_failure_close': True, 'per_consumer_qos': True, 'direct_reply_to': True}, 'cluster_name': 'rabbit@4118362311a4', 'copyright': 'Copyright (c) 2007-2024 Broadcom Inc and/or its subsidiaries', 'information': 'Licensed under the MPL 2.0. Website: https://rabbitmq.com', 'platform': 'Erlang/OTP 25.3.2.13', 'product': 'RabbitMQ', 'version': '3.12.14'}, mechanisms: [b'AMQPLAIN', b'PLAIN'], locales: ['en_US']
celery-worker-1  | [2024-11-05 18:40:07,858: INFO/MainProcess] Task celery_worker.process_text_task[f4527617-2401-4340-b351-27d6357452c3] received
api-dev          | DEBUG:amqp:using channel_id: 1                                                                                                                                                                                                                                                           
rabbit           | 2024-11-05 18:40:07.862812+00:00 [info] <0.971.0> accepting AMQP connection <0.971.0> (172.18.0.5:40336 -> 172.18.0.4:5672)                                                                                                                                                              
api-dev          | DEBUG:amqp:Channel open                                                                                                                                                                                                                                                                  
celery-worker-1  | [2024-11-05 18:40:07,866: INFO/ForkPoolWorker-16] Starting process for document 62fe3741-f206-4cb7-b37b-6e5271ca16d9                                                                                                                                                                     
rabbit           | 2024-11-05 18:40:07.864653+00:00 [info] <0.971.0> connection <0.971.0> (172.18.0.5:40336 -> 172.18.0.4:5672): user 'guest' authenticated and granted access to vhost '/'
api-dev          | INFO:root:Queued document 62fe3741-f206-4cb7-b37b-6e5271ca16d9 with task ID f4527617-2401-4340-b351-27d6357452c3                                                                                                                                                                         
api-dev          | INFO:     172.18.0.1:33298 - "POST /files/upload-file HTTP/1.1" 200 OK                                                                                                                                                                                                                   
celery-worker-1  | [2024-11-05 18:40:09,567: INFO/ForkPoolWorker-16] HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"                                                                                                                                                              
celery-worker-1  | [2024-11-05 18:40:10,061: INFO/ForkPoolWorker-16] processing chunk 1 of 7 for document 62fe3741-f206-4cb7-b37b-6e5271ca16d9
celery-worker-1  | [2024-11-05 18:40:10,706: INFO/ForkPoolWorker-16] HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
celery-worker-1  | [2024-11-05 18:40:11,330: INFO/ForkPoolWorker-16] HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
celery-worker-1  | [2024-11-05 18:40:11,489: INFO/ForkPoolWorker-16] HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
celery-worker-1  | [2024-11-05 18:40:12,420: INFO/ForkPoolWorker-16] processing chunk 2 of 7 for document 62fe3741-f206-4cb7-b37b-6e5271ca16d9
celery-worker-1  | [2024-11-05 18:40:13,296: INFO/ForkPoolWorker-16] HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
celery-worker-1  | [2024-11-05 18:40:14,495: INFO/ForkPoolWorker-16] HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"

```

### Graph Database:

You can view the graph database in the neo4j browser at http://localhost:7474. 

You should see the following type of graph document emerging in the graph as the documents are processed:

![alt text](documentation/images/neo4j-graph-document-example.png)


### Explore API:

The API currently supports two methods for exploring the personal knowledge stored in the neo4j graph database. 

1. /explore/answer-question - this uses a ReAct Langgraph agent that has two tools it can use to answer questions based on the nature of the question - general or specific. The Agent is conditioned to detect if knowledge is present in the graph or not sufficent to answer the question. If not, the Agent will use the Tavily search tool to find more knowlege with which to generate an answer. We go into the details of this agent : [ReAct Agent](https://www.youtube.com/watch?v=vEmwwbLx-ps)

The question: 'who is vannevar bush?' should return the following response:

```
{
  "question": "who is vannevar bush?",
  "answer": "Vannevar Bush was an American engineer and inventor, known for his visionary contributions to the development of information technology and technology policy. He is most famous for his 1945 essay \"As We May Think,\" published in The Atlantic, where he conceptualized the \"memex,\" a collective memory machine that anticipated aspects of the modern information society, including hypertext and the internet. Bush was concerned with the direction of scientific efforts and advocated for advancements that would make knowledge more accessible and useful for humanity.\n\nTools Used: \n- ClassifyQuestion\n- Internal General Answer Search\n\nThoughts and Observations: \n- The question was classified as general, indicating a broad, introductory inquiry about Vannevar Bush.\n- The Internal General Answer Search provided comprehensive information about Bush's contributions and ideas.\n\nSources of Information:\n- \"As We May Think - Wikipedia\", retrieved from [Wikipedia](https://en.wikipedia.org/wiki/As_We_May_Think) (last edited on October 24, 2024).",
  "setup_duration": 0.03246164321899414,
  "response_duration": 1730832851.7410095,
  "total_duration": 14.23608660697937
}
```

Notice the agent returns the sources found, and also the toughts and observations of the agent as it works through the question. 

2. /explore/find - this is a single agent pattern that currently has a tool that generates a cypher query to find the most relevant nodes and relationships to answer the question. This is a basic implementation and could be improved. It is based on Tomaz Bratanic's post on medium: [Limitations of Text Embeddings in RAG applications](https://medium.com/neo4j/limitations-of-text-embeddings-in-rag-applications-b060020b543b)


If you enter the query: "find documents about the personal knowledge vault from 2024" you should get a response like the following:

```
{
  "answer": "",
  "sources": [
    {
      "document": {
        "uuid": "62fe3741-f206-4cb7-b37b-6e5271ca16d9",
        "name": "240619 Insights from Initial Implementation of the Personal Knowledge Vault.docx",
        "addeddate": "2024-11-05T18:40:06.57Z",
        "imageurl": null,
        "publisher": null,
        "thumbnail": null,
        "type": "Document",
        "url": "http://localhost:3000/documents/62fe3741-f206-4cb7-b37b-6e5271ca16d9",
        "wordcount": 2833
      },
      "pages": [
        {
          "name": "Page 1",
          "questions": [
            {
              "text": "What are the benefits of using a personal knowledge vault for knowledge storage and retrieval?",
              "name": "1-4",
              "uuid": "9a87b8ba-8322-4ff5-a215-4bcceff56ddd"
            },
            {
              "text": "What is the primary function of the personal knowledge vault?",
              "name": "1-1",
              "uuid": "4ff09c31-86fa-4333-9ef1-03b2bc1fc6dd"
            },
            {
              "text": "How does the personal knowledge vault handle knowledge stored in different locations or formats?",
              "name": "1-5",
              "uuid": "15fb2738-6cc8-4ff2-9306-015bfa1de54e"
            },
            {
              "text": "In what ways is the personal knowledge vault similar to reading glasses for the mind?",
              "name": "1-3",
              "uuid": "e7f9d6df-dcab-402d-80fd-d3e32a41a87c"
            },
            {
              "text": "How does the personal knowledge vault assist in managing knowledge?",
              "name": "1-2",
              "uuid": "434631a7-9643-4ff9-968c-5d7de348bd99"
            }
          ],
          "summaries": [
            {
              "text": "The personal knowledge vault simplifies the process of capturing, storing, curating, and retrieving knowledge, regardless of its location or format, acting like reading glasses for the mind.",
              "name": null,
              "uuid": "e0906fdd-4524-4aca-b7af-2c43687d7b77"
            }
          ],
          "uuid": "49f4089a-669b-4904-86e1-424fadeeac6a"
        }
      ]
    },
    {
      "document": {
        "uuid": "129fbe30-3360-4484-84e2-4d330ac28535",
        "name": "As We May Think - Wikipedia",
        "addeddate": "2024-11-05T18:23Z",
        "imageurl": "/static/images/icons/wikipedia.png",
        "publisher": "en.wikipedia.org",
        "thumbnail": "/static/images/icons/wikipedia.png",
        "type": "Document",
        "url": "https://en.wikipedia.org/wiki/As_We_May_Think",
        "wordcount": 490
      },
      "pages": [
        {
          "name": "Page 1",
          "questions": [
            {
              "text": "What is the concept of the 'memex' as described by Vannevar Bush?",
              "name": "1-5",
              "uuid": "00506894-e4a0-40a9-b16e-8402889f3065"
            },
            {
              "text": "What concerns did Vannevar Bush express in his essay regarding scientific efforts?",
              "name": "1-4",
              "uuid": "6bea8c90-ffe1-478c-83c9-b8713ba5e136"
            },
            {
              "text": "How did Vannevar Bush's essay anticipate aspects of the information society?",
              "name": "1-3",
              "uuid": "cd49ee6e-aa4c-427d-9d84-81bf7a4fbd4f"
            },
            {
              "text": "When was 'As We May Think' first published and in which magazine?",
              "name": "1-2",
              "uuid": "34705f43-f9d9-44f2-899a-d3d95dcc049a"
            },
            {
              "text": "What is the main theme of Vannevar Bush's essay 'As We May Think'?",
              "name": "1-1",
              "uuid": "ecdd39ff-4482-4862-a9b5-2b11b96e0301"
            }
          ],
          "summaries": [
            {
              "text": "\"As We May Think\" is a 1945 essay by Vannevar Bush, published in The Atlantic, which is considered visionary and influential in anticipating the information society. Written before and after the atomic bombings of Hiroshima and Nagasaki, Bush expresses concern over scientific efforts being directed towards destruction rather than understanding. He proposes the concept of the \"memex,\" a collective memory machine designed to make knowledge more accessible and transform an information explosion into a knowledge explosion. The essay is significant in the history of computing, the Internet, and human-computer interaction.",
              "name": null,
              "uuid": "b677f313-3df9-4b3e-aadd-c92fd0b8d76c"
            }
          ],
          "uuid": "6e91f172-a9af-436f-b696-29448e9ba093"
        }
      ]
    }
  ],
  "timings": {
    "setup_duration": 13.364689826965332,
    "langchain_response_duration": 0,
    "neo4j_fetch_duration": 1730833075.5450926,
    "total_duration": 13.365027904510498
  },
  "payload_sizes": {
    "request_size": 59,
    "response_size": 3450,
    "db_response_size": 3483
  }
}
```


The agent prompt is supposed to be able to translate non-specific dates such as "today" or 'this month' into actual dates, but for some reason it doesn't always perform the translation correctly. I have to investigate this further. 


### Notes Endpoints:

These endpoints can be used directly, but are intended primarily for use through openAI ChatGPT Gpt. The upload-file-from-openai for example is specifically designed to pull files from the OpenAI chat history, and store them in minio along with the note data as extracted from the chatGPT side. 

Code for the GPT configuration is here: [text](gpt/clockworKnowledgeMenome_GPT.yml)

**TODO: add documentation for setting up GPT application in openAI.** 

### Processing Endpoints:

The processing subsystems are also exposed as routes. These can be triggered directly for batch processing if needed, but are integrated into the document submission endpoints. 


### Categories Endpoints:

This is based on the GraphRag articles published originally by Microsoft, but based on Tomaz Bratanic's implimentation [Implimenting from Global to Local with Neo4j and GraphRag](https://medium.com/neo4j/implementing-from-local-to-global-graphrag-with-neo4j-and-langchain-constructing-the-graph-73924cc5bab4)

I narrowed the processing down to only extract categories from chunks due to costs and complextiy. Currently the categories are not used in the context of retrieval, but I plan to use the Global to Local retrieval method to provide more relevant results. [Tomaz post - Global to Local](https://medium.com/towards-data-science/integrating-microsoft-graphrag-into-neo4j-e0d4fa00714c)

The endpoints are setup in the API in the order they are to be run as per the article. They are memory intensive, and I have not made them async, as they need to run across the entire graph. 

Documentation is provided in the endpoints. 

For the category-deduplicate endpoint, try setting the simliarity_cutoff to 0.91 and the word_similiarty to .85

For the small test data set they run pretty quickly, and if you run them in sequence using the sample data you should get the following results:

```
╒═══════╤═════════════════╤══════════════════════════════════════════════════════════════════════╕
│cluster│size(clusterName)│clusterName                                                           │
╞═══════╪═════════════════╪══════════════════════════════════════════════════════════════════════╡
│4      │7                │["Statistics", "Wikipedia", "Wikimedia Foundation, Inc.", "History Of │
│       │                 │Computing", "History Of The Internet", "Information Society", "Telemet│
│       │                 │ry"]                                                                  │
├───────┼─────────────────┼──────────────────────────────────────────────────────────────────────┤
│0      │5                │["Privacy Policy", "Disclaimers", "Code Of Conduct", "Cookie Statement│
│       │                 │", "Terms Of Use"]                                                    │
├───────┼─────────────────┼──────────────────────────────────────────────────────────────────────┤
│24     │3                │["Multimodal Ai", "Natural Language Processing (Nlp)", "Conversational│
│       │                 │ Ai"]                                                                 │
├───────┼─────────────────┼──────────────────────────────────────────────────────────────────────┤
│6      │2                │["Mobile View", "Smart Device"]                                       │
├───────┼─────────────────┼──────────────────────────────────────────────────────────────────────┤
│10     │2                │["Futurology Books", "Library Science Publications"]                  │
├───────┼─────────────────┼──────────────────────────────────────────────────────────────────────┤
│3      │1                │["Developers"]                                                        │
├───────┼─────────────────┼──────────────────────────────────────────────────────────────────────┤
│11     │1                │["1945 Essays"]                                                       │
├───────┼─────────────────┼──────────────────────────────────────────────────────────────────────┤
│15     │1                │["Hypertext"]                                                         │
├───────┼─────────────────┼──────────────────────────────────────────────────────────────────────┤
│16     │1                │["Vannevar Bush"]                                                     │
├───────┼─────────────────┼──────────────────────────────────────────────────────────────────────┤
│18     │1                │["As We May Think"]                                                   │
├───────┼─────────────────┼──────────────────────────────────────────────────────────────────────┤
│19     │1                │["Atomic Bombings Of Hiroshima And Nagasaki"]                         │
├───────┼─────────────────┼──────────────────────────────────────────────────────────────────────┤
│20     │1                │["Visual And Audio Inputs"]                                           │
├───────┼─────────────────┼──────────────────────────────────────────────────────────────────────┤
│21     │1                │["Typing"]                                                            │
├───────┼─────────────────┼──────────────────────────────────────────────────────────────────────┤
│22     │1                │["Memory Capture"]                                                    │
├───────┼─────────────────┼──────────────────────────────────────────────────────────────────────┤
│23     │1                │["Secure Cloud Storage"]                                              │
├───────┼─────────────────┼──────────────────────────────────────────────────────────────────────┤
│26     │1                │["Autogen"]                                                           │
├───────┼─────────────────┼──────────────────────────────────────────────────────────────────────┤
│29     │1                │["Cladistic Taxonomic Classification"]                                │
├───────┼─────────────────┼──────────────────────────────────────────────────────────────────────┤
│30     │1                │["Hierarchical Metadata Structures"]                                  │
├───────┼─────────────────┼──────────────────────────────────────────────────────────────────────┤
│31     │1                │["File Naming Standards"]                                             │
├───────┼─────────────────┼──────────────────────────────────────────────────────────────────────┤
│32     │1                │["Full Text Search Systems"]                                          │
├───────┼─────────────────┼──────────────────────────────────────────────────────────────────────┤
│33     │1                │["Internal Knowledge Vault"]                                          │
└───────┴─────────────────┴──────────────────────────────────────────────────────────────────────┘
```

The graph should look like this:

![alt text](documentation/images/communities-categories-documents.png) [alt text](README.md)

Due to the fact its a sparse graph, the communties will only be 1 level deep. 

## Development Setup

To develop on the system, you will need to have python installed on your machine, and the requirements installed. This will also allow for local development.  

Its definitly a best practice to use a virtual environment to run the development server with this application. 

The stack is designed to be run with a docker compose stack, which includes a local instance of Neo4j, MinIO, RabbitMQ, and a celery worker. These services must be running for the application to function. I have included a docker compose file for the development stack, which will start these services locally:

```bash
docker compose -f docker-compose_dev_local.yml up -d
```

### Config files:

Its also necessary to create config file for the development environment. This should be placed in the config directory.

It can be copied from the .env file, and should be renamed to .env.dev.

NOTE **You will have to change the NEO4J_URI to point to the local instance of neo4j at bolt://localhost:7687. as debug running is outside the docker container.**

This allows for different environment variables to be used for development and testing, and hopefully to allow for running the same code base for multiple instances. 

### VSCode or cursorAI Setup for debugging:

The configuration for VSCode or cursorAI is provided in the .vscode directory.

launch.json
```
{
    "version": "0.2.0",
    "configurations": [
      { 
        "name": "Python: Pytest",
        "type": "debugpy",
        "request": "launch",
        "module": "pytest",
       
        "console": "integratedTerminal",
        "justMyCode": false,
        "env": {
          "ENV_MODE": "test"
        }
      },
           
      {
        "name": "Python: FastAPI (backend)",
        "type": "debugpy",
        "request": "launch",
        "module": "uvicorn",
        "args": [
          "backend.main:app", 
          "--reload",
          "--port",
          "8000",
          "--host",
          "0.0.0.0" // If necessary
        ],
        "cwd": "${workspaceFolder}", 
        "env": {
          "ENV_MODE": "development",
          "NEO4J_URI": "bolt://localhost:7687"
        }
      },
    ],
    "justMyCode": false
  }
```


### Install Dependencies

This will install development dependencies including pytest and libraries required for testing.

```bash
cd backend
pip install -r requirements-dev.txt
```

### Start Docker Stack for Development

```bash
docker-compose -f docker-compose_dev_local.yml 
```

### Run Development Server

```bash
uvicorn backend.main:app --reload
```
Or use the VSCode launch configuration.



## Common Issues

1. **Services Not Ready**: If initialization fails, ensure all Docker services are healthy:
```bash
docker-compose ps
```

2. **Port Conflicts**: Make sure the required ports are available:
- 8000: FastAPI
- 7474, 7687: Neo4j
- 9000, 9001: MinIO
- 5672, 15672: RabbitMQ

3. **Initialization Failures**: Check logs for specific services:
```bash
docker-compose -f docker-compose_dev_local.yml logs neo4j-dev minio-dev rabbit-dev
```

## Testing

A basic set of tests are provided to get you started. 

In order for the tests to run, you need to run the test docker compose stack, which starts a local instance of Neo4j, rabbitmq and MinIO. It will also start the celery worker and the API service for handling route tests. 

```bash
docker compose -f docker-compose.test.yml up -d
```

Then you can run the tests with the following command (make sure pytest is installed):

```bash
pytest 
```

or using the VSCode test configuration, which will work with debugger. 

The tests are not exhaustive, but they should give you a good starting point. There are tests for basic API routes, focusing on authentication and user management. The neo4j database is setup to be seperate from the dev instance and uses a different folder and docker container for testing, and is reset for each test, so there is no need to reset the database between tests. 

## Maintenance

### Reset the Stack

To completely reset the stack:

```bash
# Stop all services
docker-compose down

# Remove volumes
docker-compose down -v

# Restart services
docker-compose up -d

# Reinitialize the system
python -m backend.commands.init_stack --force
```

### Backup Data

1. **Neo4j**: Use Neo4j's backup procedures
2. **MinIO**: Use MinIO Client (mc) for bucket backups
3. **RabbitMQ**: Export definitions from management console



## Contributing

**TODO: add contributing guidelines**

1. Fork the repository
2. Create a feature branch
3. Commit changes
4. Push to the branch
5. Create a Pull Request

## License
Code is licensed under the Apache 2.0 license. [license](LICENSE)

**This code is provided as is, without any guarantees or warranties. Use at your own risk.**
It is provided for educational and research purposes only.
The code is for single user personal knowledge management - the security is not production grade.









