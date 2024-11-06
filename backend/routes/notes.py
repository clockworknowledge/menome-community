from typing import Optional
from fastapi import APIRouter, File, HTTPException, UploadFile, Form, Depends
from minio import Minio
from minio.error import S3Error
import uuid
from neo4j import GraphDatabase
import logging
import requests
from typing import Optional, List
import mimetypes
from urllib.parse import unquote

import io

from minio.error import S3Error
from fastapi import HTTPException, Depends
from typing import List
from pydantic import BaseModel
import os
import mimetypes

from backend.config import CurrentConfig
from backend.schemas import User, NotePayload, FileUpload, NoteResponse
from backend.dependencies.auth import get_current_user
from backend.worker.tasks import process_text_task
from backend.services.note_services import save_note_to_neo4j,  get_minio_client, get_presigned_url
from backend.utilities.mime_types import MimeTypeUtil
from backend.services.file_services import save_document_with_files_to_neo4j
# Global Variables
router = APIRouter()


@router.post("/note",
          summary="Capture a note from the user and store it in the graph database for processing",
          description="""This endpoint allows authenticated users to upload a note to the system. The note is stored in the graph database (Neo4j) and queued for processing by the worker service.

          The endpoint accepts a JSON payload with the following structure:
          {
              "name": "string",
              "note_text": "string"
          }

          The 'name' field is used as a title or identifier for the note, while 'note_text' contains the actual content of the note.

          Upon successful upload, the endpoint returns:
          - documentId: A unique identifier for the uploaded note
          - message: A confirmation message
          - task_ids: A list of task IDs associated with the processing of the note

          The worker service will process the note to generate questions, summaries, and perform other analysis tasks.

          Authentication is required to use this endpoint. Users must provide a valid authentication token in the request header.

          Potential errors:
          - 401 Unauthorized: If the user is not authenticated
          - 500 Internal Server Error: If there's an issue saving the note or queueing it for processing""",
          tags=["Notes"])
async def upload_note(payload: NotePayload, current_user: User = Depends(get_current_user)):
    """
    Upload a note to the system.

    This endpoint allows authenticated users to upload a note to the system. The note is stored in Neo4j
    and queued for processing by the worker service.

    Args:
        payload (NotePayload): The note payload containing the name and text of the note.
        current_user (User): The authenticated user making the request.

    Returns:
        dict: A dictionary containing the document ID, a message, and task IDs.

    Raises:
        HTTPException: If there's an error saving the note or queueing it for processing.

    Flow:
    1. Extract name and note_text from the payload.
    2. Generate a unique ID for the note.
    3. Save the note to Neo4j.
    4. Queue the note for processing by the worker service.
    5. Return the response with document ID and task information.
    """

    name = payload.name
    note_text = payload.note_text
  
    # Save note in Neo4j
    driver = GraphDatabase.driver(CurrentConfig.NEO4J_URI, auth=(CurrentConfig.NEO4J_USER, CurrentConfig.NEO4J_PASSWORD))
    noteId=str(uuid.uuid4())
    save_note_to_neo4j(noteId, name, note_text, None, current_user.uuid, driver)
    driver.close()

    try:
        task_ids = []
        logging.info(f"Queueing document {noteId} for processing.")
        with driver.session() as session:
            result = session.run("MATCH (a:Document {uuid: $uuid}) RETURN a", {"uuid": noteId})
            document_data = result.single().value()
            text = document_data['text']
            # Pass the generateQuestions and generateSummaries flags to the task
            task = process_text_task.delay(text, noteId, True, True, True)
            task_ids.append(task.id)
            logging.info(f"Queued document {noteId} with task ID {task.id}")
    except Exception as e:
        logging.error(f"Failed to queue document {noteId}: {e}")

    return {
        "documentId": noteId,    
        "message": f"Processing started for {len(noteId)} document",
        "task_ids": task_ids
    }





@router.post("/upload-image-from-openai",
             summary="Capture a image and a note about the image from the user and store it in the graph database for processing",
             description="""This endpoint allows the user to upload an image from OpenAI along with a note. The process involves:

             1. Receiving a NotePayload containing note text and OpenAI file references.
             2. Downloading each referenced file from OpenAI.
             3. Determining the file type and appropriate MIME type.
             4. Generating a unique filename and uploading the file to MinIO.
             5. Storing the note text and MinIO file URLs in the Neo4j graph database.
             6. Queueing the note for further processing by the worker service.

             The endpoint requires user authentication and handles various file types including images and documents.
             It returns a response containing the new document ID, processing status, and associated task IDs.

             Potential errors include file download issues, MinIO upload failures, or Neo4j storage problems.""",
             tags=["Notes"])
async def upload_image_from_openai(
        noteRequest: NotePayload,
        current_user: User = Depends(get_current_user)):
    """
    Upload a note with images from OpenAI.

    This endpoint allows authenticated users to upload a note along with images from OpenAI.
    The note is stored in Neo4j, and the images are downloaded from OpenAI and stored in MinIO.
    The note is then queued for processing by the worker service.

    Args:
        noteRequest (NotePayload): The note payload containing note information and OpenAI file references.
        current_user (User): The authenticated user making the request.

    Returns:
        dict: A dictionary containing the document ID, a message, and task IDs.

    Raises:
        HTTPException: If there's an error downloading files from OpenAI, uploading to MinIO, or saving to Neo4j.

    Flow:
    1. Process OpenAI file references.
    2. For each file reference:
        a. Download the file from OpenAI.
        b. Determine file extension and MIME type.
        c. Generate a unique filename and upload to MinIO.
        d. Store the MinIO URL.
    3. Save the note with image URLs to Neo4j.
    4. Queue the note for processing by the worker service.
    5. Return the response with document ID and task information.
    """

    logging.info(f"Received note upload request from user {current_user.uuid}")
    
    # Process OpenAI file references
    image_urls = []
    if noteRequest.openaiFileIdRefs:
        for file_ref in noteRequest.openaiFileIdRefs:
            try:
                logging.info(f"Downloading file from {file_ref.download_link}")
                response = requests.get(file_ref.download_link)
                response.raise_for_status()

                # Extract filename from the name field
                filename = file_ref.name
                
                # Determine file extension and MIME type
                file_extension = os.path.splitext(filename)[1].lower()
                
                # Use the provided mime_type if available, otherwise use the utility class
                if file_ref.mime_type:
                    mime_type = file_ref.mime_type
                else:
                    mime_type = MimeTypeUtil.get_mime_type(file_extension)

                if not mime_type:
                    # Fallback to content-type from response if mapping doesn't provide info
                    mime_type = response.headers.get('content-type', 'application/octet-stream')
                
                if not file_extension:
                    file_extension = MimeTypeUtil.get_extension(mime_type)

                logging.info(f"Determined file extension: {file_extension}, MIME type: {mime_type}")

                # Generate a unique filename
                unique_filename = f"{uuid.uuid4()}{file_extension}"
                logging.info(f"Unique filename: {unique_filename}")
                # MinIO Client Setup
                try:
                    minio_client = Minio(
                        CurrentConfig.MINIO_ENDPOINT,
                        access_key=CurrentConfig.MINIO_ACCESS_KEY,
                        secret_key=CurrentConfig.MINIO_SECRET_KEY,
                        secure=CurrentConfig.MINIO_SECURE
                    )

                    minio_client.put_object(
                        CurrentConfig.MINIO_NOTES_BUCKET,
                        unique_filename,
                        io.BytesIO(response.content),
                        length=len(response.content),
                        content_type=mime_type
                    )
                    logging.info(f"File uploaded to MinIO: {unique_filename}")

                    # Construct the MinIO file URL
                    file_url = f"{CurrentConfig.MINIO_ENDPOINT}/{CurrentConfig.MINIO_NOTES_BUCKET}/{unique_filename}"
                    image_urls.append(file_url)
                except S3Error as minio_error:
                    logging.error(f"MinIO error: {minio_error}")
                    raise HTTPException(status_code=500, detail=f"Failed to upload file to MinIO: {str(minio_error)}")
            except requests.RequestException as download_error:
                logging.error(f"File download error: {download_error}")
                raise HTTPException(status_code=500, detail=f"Failed to download file from OpenAI: {str(download_error)}")

    # Save note in Neo4j
    driver = GraphDatabase.driver(CurrentConfig.NEO4J_URI, auth=(CurrentConfig.NEO4J_USER, CurrentConfig.NEO4J_PASSWORD))
    noteId = str(uuid.uuid4())
    try:
        logging.info(f"Saving note {noteId} to Neo4j")
        save_document_with_files_to_neo4j(noteId, noteRequest.name, noteRequest.note_text, current_user.uuid, image_urls, driver, "Note")
    except Exception as neo4j_error:
        logging.error(f"Neo4j error: {neo4j_error}")
        raise HTTPException(status_code=500, detail=f"Failed to save note in Neo4j: {str(neo4j_error)}")
    finally:
        driver.close()

    # Queue note for processing
    task_ids = []
    try:
        logging.info(f"Queueing document {noteId} for processing.")
        driver = GraphDatabase.driver(CurrentConfig.NEO4J_URI, auth=(CurrentConfig.NEO4J_USER, CurrentConfig.NEO4J_PASSWORD))
        with driver.session() as session:
            result = session.run("MATCH (a:Document {uuid: $uuid}) RETURN a", {"uuid": noteId})
            document_data = result.single()
            if not document_data:
                raise HTTPException(status_code=404, detail="Document not found in Neo4j")

            text = document_data['a']['text']
            # Pass the generateQuestions and generateSummaries flags to the task
            task = process_text_task.delay(text, noteId, True, True, True)
            task_ids.append(task.id)
            logging.info(f"Queued document {noteId} with task ID {task.id}")
    except Exception as processing_error:
        logging.error(f"Failed to queue document {noteId} for processing: {processing_error}")
        raise HTTPException(status_code=500, detail=f"Failed to queue document for processing: {str(processing_error)}")
    finally:
        driver.close()

    return {
        "documentId": noteId,
        "message": f"Processing started for document {noteId}",
        "task_ids": task_ids
    }


@router.get("/note/{note_id}", response_model=NoteResponse,
            summary="Retrieve a note and its associated files",
            description="This endpoint retrieves a note and its associated files from the graph database and returns them in a structured format.",
            tags=["Notes"])         
async def get_note(note_id: str, current_user: User = Depends(get_current_user)):
    """
    Retrieve a note and its associated files.

    This endpoint allows authenticated users to retrieve a specific note and its associated files.
    The note data is fetched from Neo4j, and presigned URLs are generated for any associated files in MinIO.

    Args:
        note_id (str): The unique identifier of the note to retrieve.
        current_user (User): The authenticated user making the request.

    Returns:
        NoteResponse: A structured response containing the note details and presigned URLs for associated files.

    Raises:
        HTTPException: If the note is not found or if there's an error retrieving the note data.

    Flow:
    1. Log the retrieval attempt.
    2. Connect to Neo4j and MinIO.
    3. Query Neo4j for the note data.
    4. If the note is found, process any associated files:
        a. Generate presigned URLs for each file in MinIO.
    5. Prepare and return the NoteResponse with note details and file URLs.
    6. Handle any exceptions and log errors.
    """
    logging.info(f"Attempting to retrieve note with ID: {note_id} for user: {current_user.username}")
    driver = GraphDatabase.driver(CurrentConfig.NEO4J_URI, auth=(CurrentConfig.NEO4J_USER, CurrentConfig.NEO4J_PASSWORD))
    logging.info(f"Minio endpoint: {CurrentConfig.MINIO_ENDPOINT_EXTERNAL}")
    minio_client = get_minio_client()
    
    try:
        with driver.session() as session:
            logging.debug(f"Executing Neo4j query for note: {note_id}")
            result = session.run(
               """ MATCH (d:Document {uuid: $uuid})-[]-(i:File) WHERE d.type='Note'
                RETURN d.uuid as id, d.name as name, d.text as note_text, collect(i.miniouuid) as miniouuid, collect(i.url) as image_urls""",
                {"uuid": note_id}
            )
            note_data = result.single()
            
            if not note_data:
                logging.warning(f"Note not found: {note_id}")
                raise HTTPException(status_code=404, detail="Note not found")
            
            logging.info(f"Note {note_id} found. Processing associated files.")
            files = []
            for image_url in note_data['image_urls']:
                object_name = image_url.split('/')[-1]
                file_extension = os.path.splitext(object_name)[1].lower()
                mime_type = mimetypes.guess_type(object_name)[0] or 'application/octet-stream'
                logging.debug(f"Generating presigned URL for object: {object_name} with MIME type: {mime_type}")
                presigned_url = get_presigned_url(
                    minio_client, 
                    CurrentConfig.MINIO_NOTES_BUCKET, 
                    object_name, 
                    mime_type,
                    secure=CurrentConfig.MINIO_SECURE
                )
                files.append(presigned_url)

            # Then, prepare the response
            response = NoteResponse(
                id=note_data['id'],
                name=note_data['name'],
                note_text=note_data['note_text'],
                files=files  
            )

            return response
    except Exception as e:
        logging.error(f"Failed to retrieve note {note_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve note: {str(e)}")
    finally:
        logging.debug("Closing Neo4j driver connection")
        driver.close()

