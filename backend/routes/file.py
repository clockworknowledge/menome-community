from fastapi import APIRouter, HTTPException, Depends
from minio import Minio
from minio.error import S3Error
import uuid
from neo4j import GraphDatabase
import logging
from io import BytesIO

from backend.schemas import User, FileUpload
from backend.config import CurrentConfig
from backend.dependencies.auth import get_current_user
from backend.services.file_services import save_document_with_files_to_neo4j, extract_text_from_word_file, extract_text_from_pdf
from backend.worker.tasks import process_text_task

router = APIRouter()

# Inside file.py
print("File routes imported")   


@router.post("/upload-file",
             summary="Upload a file from the user and store it in the minio file repository. Process contents into graph document",
             description="""This endpoint allows the user to upload a file to minio storate and process the contents into a graph document structure

             Key features:
             - Accepts a file upload along with note metadata
             - Stores the file text in Neo4j graph database
             - If an image file is provided, it's stored in MinIO object storage
             - Generates a unique ID for the file
             - Queues the file for further processing by a worker service

             Request body:
             - file: The file to be uploaded 
             - content_type: MIME type of the file
             - note_text: Text content of a note associated with the file

             Returns:
             - documentId: Unique ID of the created file
             - message: Confirmation message
             - task_ids: List of IDs for queued processing tasks

             Authentication:
             - Requires a valid user token

             Error responses:
             - 400: Bad Request - Invalid input data
             - 401: Unauthorized - Invalid or missing token
             - 500: Internal Server Error - Failed to upload file or save note
             

             Flow:
             1. Check if a file was uploaded
             2. If a file is present, upload it to MinIO and generate a URL.
             3. Save the file (and image URL if applicable) to Neo4j.
             4. Queue the file for processing by the worker service.
             5. Return the response with document ID and task information.
             
             Notes:
                Current version only supports basic doc, docx and PDF file types.
                The PDF processing is limited to extracting text using simple PyPDFLoader.
                
             """,
             tags=["Files"])
async def upload_file(file_upload: FileUpload = Depends(), current_user: User = Depends(get_current_user)):
    """
    Upload a file to be processed.

    This endpoint allows authenticated users to upload a file to be processed.
    The file is stored in Neo4j, and if an image is provided, it's stored in MinIO.
    The file is then queued for processing by the worker service.

    Args:
        file_upload (FileUpload): The file upload data containing file information and optional file.
        current_user (User): The authenticated user making the request.

    Returns:
        dict: A dictionary containing the document ID, a message, and task IDs.

    Raises:
        HTTPException: If there's an error uploading the file to MinIO or saving the note to Neo4j.

    Flow:
    1. Check if an image file was uploaded.
    2. If a file is present, upload it to MinIO and generate a URL.
    3. Save the file (and image URL if applicable) to Neo4j.
    4. Queue the file for processing by the worker service.
    5. Return the response with document ID and task information.
    """

    # Check if an file was uploaded
    if file_upload.file:
        # return an error if no file is uploaded
        if file_upload.file.filename is None:
            raise HTTPException(status_code=400, detail="No file uploaded")

    # setup file context 
    file_id = str(uuid.uuid4())
    filename = f"{file_id}-{file_upload.file.filename}"
    original_filename = file_upload.file.filename
    extension = file_upload.file.filename.split('.')[-1]
    content_type = file_upload.file.content_type
    file_content = None
    file_type = None
    file_urls = []  

    # store file to minio
    try:
        # MinIO Client Setup
        minio_client = Minio(CurrentConfig.MINIO_ENDPOINT, access_key=CurrentConfig.MINIO_ACCESS_KEY, secret_key=CurrentConfig.MINIO_SECRET_KEY, secure=CurrentConfig.MINIO_SECURE)
        
        # Read the file content first
        file_content = await file_upload.file.read()  # Add await here
        
        # Create a BytesIO object from the content
        file_data = BytesIO(file_content)
        
        minio_client.put_object(
            CurrentConfig.MINIO_FILES_BUCKET, 
            filename, 
            file_data, 
            length=len(file_content),  # Specify the exact length
            content_type=file_upload.file.content_type
        )
        host = "https://" + CurrentConfig.MINIO_ENDPOINT_EXTERNAL
        file_url = f"{host}/{CurrentConfig.MINIO_FILES_BUCKET}/{filename}"
        file_urls = [file_url]  # Fix the list creation
    except S3Error as e:
        raise HTTPException(status_code=500, detail=str(e))
  
    # Determine file type from extension
    if filename.endswith('.pdf'):
        file_type = 'pdf'
    elif filename.endswith(('.doc', '.docx')):
        file_type = 'doc'
    elif filename.endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp')):
        file_type = 'image'
    else:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    # Extract text from file based on type - different types of files require different processing
    if file_type == 'doc' or filename.endswith('.docx'):
        # Convert DOCX to DOC if needed and extract text
        if filename.endswith('.docx'):
            file_content = extract_text_from_word_file(file_content, filename)

    elif file_type == 'pdf':
        # Extract text from PDF
        file_content = extract_text_from_pdf(file_content, filename)
        file_upload.content_type = 'text/plain'    
    elif file_type == 'image':
        # Extract text from image using openAI OCR
        #file_upload.file = extract_text_from_image(file_upload.file)
        file_upload.content_type = 'text/plain'


    # Save document in Neo4j with file node linked
    driver = GraphDatabase.driver(CurrentConfig.NEO4J_URI, auth=(CurrentConfig.NEO4J_USER, CurrentConfig.NEO4J_PASSWORD))
    documentId = str(uuid.uuid4())
    save_document_with_files_to_neo4j(documentId, original_filename, file_content, current_user.uuid, file_urls, driver, CurrentConfig.VALID_TYPES.Document.value)
    driver.close()

    try:
        task_ids = []
        logging.info(f"Queueing document {documentId} for processing.")
        with driver.session() as session:
            result = session.run("MATCH (a:Document {uuid: $uuid}) RETURN a", {"uuid": documentId})
            document_data = result.single().value()
            text = document_data['text']
            # Pass the generateQuestions and generateSummaries flags to the task
            task = process_text_task.delay(text, documentId, True, True, True)
            task_ids.append(task.id)
            logging.info(f"Queued document {documentId} with task ID {task.id}")
    except Exception as e:
        logging.error(f"Failed to queue document {documentId}: {e}")

    return {
        "documentId": documentId,    
        "message": f"Processing started for {len(task_ids)} task(s)",
        "task_ids": task_ids
    }
