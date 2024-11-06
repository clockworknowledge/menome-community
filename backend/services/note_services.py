"""
Note Services Module

This module provides functionality for managing notes in the system, including saving notes to Neo4j
and handling MinIO file operations.

Functions:
    save_note_to_neo4j: Saves a note with metadata to Neo4j database
    save_note_with_files_to_neo4j: Saves a note with associated files to Neo4j
    get_minio_client: Creates and returns a configured MinIO client
    get_presigned_url: Generates presigned URLs for MinIO objects with appropriate content disposition
"""

from minio import Minio
from minio.error import S3Error
from fastapi import HTTPException
from typing import List
import os
from backend.services.file_services import save_document_with_files_to_neo4j
from datetime import timedelta
import logging

from backend.config import CurrentConfig

def save_note_to_neo4j(noteId, name: str, text: str, image_url: str, userId: str, neo4j_driver ):
    """
    Saves a note and its metadata to Neo4j database.
    
    Args:
        noteId: Unique identifier for the note
        name: Title/name of the note
        text: Content of the note
        image_url: URL of associated image
        userId: ID of user creating the note
        neo4j_driver: Neo4j database driver instance
    
    Returns:
        noteId: The ID of the created note
    """
    with neo4j_driver.session() as session:
        wordcount = len(text.split())
        url = CurrentConfig.SITE_URL + CurrentConfig.ROOT_PATH + '/getDocument/' + noteId
        query="""CREATE (n:Document {uuid: $noteId}) 
            set 
             n.name=$name,
             n.text=$text,
             n.imageurl=$image_url,
             n.addeddate= datetime(),
             n.thumbnail=$image_url,
             n.wordcount=$wordcount,
             n.type="Note",
             n.url=$url
             
              with n
                MATCH (u:User {uuid: $useruuid})
                MERGE (ua:UserAction {useruuid: u.uuid}) 
                ON CREATE SET ua.name = u.username, ua.uuid=randomUUID()
                MERGE (u)-[r:HAS_ACTION]->(ua)
                MERGE (ua)-[:ADDED]-(n) set r.dateadded= datetime()
             """
        session.run(query, { "noteId": noteId, "name": name, "text": text, "image_url": image_url, "wordcount": wordcount, "useruuid": userId, "url": url})
        session.close()
        return noteId


def save_note_with_files_to_neo4j(documentId, name: str, text: str, userId: str, files: List[str], neo4j_driver):
    """
    Saves a note with associated files to Neo4j database.
    
    Args:
        documentId: Unique identifier for the document/note
        name: Title/name of the note
        text: Content of the note
        userId: ID of user creating the note
        files: List of associated file paths
        neo4j_driver: Neo4j database driver instance
    """
    save_document_with_files_to_neo4j(documentId, name, text, userId, files, neo4j_driver, "Note")
    
    
def get_minio_client():
    """
    Creates and returns a configured MinIO client.
    
    Returns:
        Minio: Configured MinIO client instance
    """
    return Minio(
        CurrentConfig.MINIO_ENDPOINT_EXTERNAL,
        access_key=CurrentConfig.MINIO_ACCESS_KEY,
        secret_key=CurrentConfig.MINIO_SECRET_KEY,
        secure=CurrentConfig.MINIO_SECURE_DOWNLOAD
    )

def get_presigned_url(minio_client, bucket_name: str, object_name: str, content_type: str, secure: bool = True) -> str:
    """
    Generate a presigned URL for accessing an object in MinIO.
    
    Args:
        minio_client: The MinIO client instance
        bucket_name (str): Name of the bucket
        object_name (str): Name of the object
        content_type (str): MIME type of the object
        secure (bool): Whether to use HTTPS (not used in presigned_get_object)
    
    Returns:
        str: Presigned URL for the object
    
    Raises:
        Exception: If there's an error generating the presigned URL
    """
    try:
        url = minio_client.presigned_get_object(
            bucket_name,
            object_name,
            expires=timedelta(hours=1)  # URL expires in 1 hour
        )
        return url
    except Exception as e:
        logging.error(f"Error generating presigned URL: {str(e)}")
        raise