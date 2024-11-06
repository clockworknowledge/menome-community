from datetime import datetime
import uuid
import logging
from neo4j.exceptions import Neo4jError
from typing import List
import tempfile
import os
import subprocess

from langchain_core.documents import Document
from langchain_text_splitters import TokenTextSplitter
from langchain_experimental.text_splitter import SemanticChunker
from langchain_community.embeddings import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.document_loaders import Docx2txtLoader

from backend.config import CurrentConfig
from backend.schemas import User
from backend.schemas.constants import DefaultIcons
from backend.utilities.utils import add_document, add_page, add_chunk, setupSourceChunks

"""
Functions for handling file processing and storage in Neo4j.

This module contains functions for extracting text from Word documents and saving documents with associated files to Neo4j.
"""

def extract_text_from_word_file(file_content: bytes, filename: str):
    """
    Extract text content from a Word document (.doc or .docx).

    Args:
        file_content (bytes): The binary content of the Word file
        filename (str): Name of the file including extension

    Returns:
        str: The extracted text content from the Word document

    Raises:
        ValueError: If file format is unsupported or conversion fails
    """
    logging.info(f"Processing {filename}")

    # save file to temp directory
    tmpfile_path = tempfile.gettempdir() + "/" + filename
    with open(tmpfile_path, "wb") as f:
        f.write(file_content)

    if tmpfile_path is None:
        raise ValueError("Failed to save the file content")

    base_filename, file_extension = os.path.splitext(filename)
    if file_extension.lower() in ['.docx', '.doc']:
        if file_extension.lower() == '.doc':
            # Remove self.update_state since this isn't in a class
            converted_file_path = convert_doc_to_docx(tmpfile_path)
            if converted_file_path is None:
                raise ValueError("Failed to convert .doc to .docx")
        else:
            converted_file_path = tmpfile_path

        loader = Docx2txtLoader(str(converted_file_path))
        doc = loader.load()
        extracted_content = doc[0].page_content

        # Clean up temporary files
        if tmpfile_path and os.path.exists(tmpfile_path):
            os.remove(str(tmpfile_path))
        if converted_file_path and os.path.exists(str(converted_file_path)) and str(converted_file_path) != str(tmpfile_path):
            os.remove(str(converted_file_path))

    else:
        raise ValueError("Unsupported file format.")

    return extracted_content

def convert_doc_to_docx(doc_path):
    """
    Convert a .doc file to .docx format using LibreOffice.

    Args:
        doc_path (str): Path to the .doc file to convert

    Returns:
        str: Path to the converted .docx file, or None if conversion fails
    """
    try:
        subprocess.run(['libreoffice', '--headless', '--convert-to', 'docx', '--outdir', tempfile.gettempdir(), doc_path], check=True)
        base, _ = os.path.splitext(doc_path)
        return os.path.join(tempfile.gettempdir(), base + ".docx")
    except subprocess.CalledProcessError as e:
        print(f"Error converting file: {e}")
        return None

def save_document_with_files_to_neo4j(documentId, name: str, text: str, userId: str, files: List[str], neo4j_driver, type: str):
    """
    Save a document and its associated files to Neo4j.

    Args:
        documentId (str): Unique identifier for the document
        name (str): Name/title of the document
        text (str): Text content of the document
        userId (str): ID of the user creating the document
        files (List[str]): List of file URLs associated with the document
        neo4j_driver: Neo4j driver instance
        type (str): Type of document

    Returns:
        str: The document ID
    """
    with neo4j_driver.session() as session:
        wordcount = len(text.split())
        
        url = CurrentConfig.SITE_URL + CurrentConfig.ROOT_PATH + '/documents/' + documentId
        query = """CREATE (n:Document {uuid: $documentId}) 
                   SET n.name = $name,
                       n.text = $text,
                       n.addeddate = datetime(),
                       n.wordcount = $wordcount,
                       n.type = $type,
                       n.url = $url
                   WITH n
                   UNWIND $files AS file_url
                   CREATE (img:File {url: file_url})
                        set img.addeddate = datetime(),
                        img.uuid = randomUUID(),
                        img.miniouuid = SPLIT(SPLIT(file_url, "/")[-1], ".")[0],
                        img.extension = SPLIT(SPLIT(file_url, "/")[-1], ".")[1]
                   CREATE (n)-[:HAS_FILE]->(img)
                   WITH n
                   MATCH (u:User {uuid: $useruuid})
                   MERGE (ua:UserAction {useruuid: u.uuid}) 
                   ON CREATE SET ua.name = u.username, ua.uuid = randomUUID()
                   MERGE (u)-[r:HAS_ACTION]->(ua)
                   MERGE (ua)-[:ADDED]-(n) SET r.dateadded = datetime()"""
        session.run(query, {
            "documentId": documentId, 
            "name": name, 
            "text": text, 
            "wordcount": wordcount, 
            "useruuid": userId, 
            "url": url, 
            "files": files,
            "type": type
        })
        session.close()
        return documentId
    


def process_document_chunks(self, driver, documentId, file_content, embeddings):
    """
    Process a document into chunks and store them in Neo4j with embeddings.

    Args:
        self: Instance of the class containing this method
        driver: Neo4j driver instance
        documentId (str): ID of the document being processed
        file_content (str): Content to be chunked and processed
        embeddings: Embeddings model instance

    Returns:
        list: List of parent documents after splitting

    Raises:
        Neo4jError: If there's an error storing chunks in Neo4j
    """
    parent_splitter = TokenTextSplitter(chunk_size=512, chunk_overlap=0)
    child_splitter = SemanticChunker(embeddings, breakpoint_threshold_type="percentile")
    parent_documents = parent_splitter.split_documents([Document(page_content=file_content)])

    for i, parent in enumerate(parent_documents):
        self.update_state(state=CurrentConfig.PROCESSING_PAGES, meta={"page": i+1, "total_pages": len(parent_documents), "documentId": documentId})
        logging.info(f"processing chunk {i+1} of {len(parent_documents)} for document {documentId}")

        child_documents = child_splitter.create_documents([parent.page_content])
        params = {
            "document_uuid": documentId,
            "parent_uuid": str(uuid.uuid4()),
            "name": f"Page {i+1}",
            "parent_text": parent.page_content,
            "parent_id": i,
            "parent_embedding": embeddings.embed_query(parent.page_content),
            "children": [
                {
                    "text": c.page_content,
                    "id": str(uuid.uuid4()),
                    "name": f"{i}-{ic+1}",
                    "embedding": embeddings.embed_query(c.page_content),
                }
                for ic, c in enumerate(child_documents)
            ],
        }

        try:
            with driver.session() as session:
                session.run(
                    """
                    MERGE (p:Page {uuid: $parent_uuid})
                    SET p.text = $parent_text,
                    p.name = $name,
                    p.type = "Page",
                    p.datecreated= datetime(),
                    p.source=$parent_uuid
                    WITH p
                    CALL db.create.setVectorProperty(p, 'embedding', $parent_embedding) YIELD node
                    WITH p
                        MATCH (d:Document {uuid: $document_uuid})
                        MERGE (d)-[:HAS_PAGE]->(p)
                    WITH p
                    UNWIND $children AS child
                        MERGE (c:Child {uuid: child.id})
                        SET
                            c.text = child.text,
                            c.name = child.name,
                            c.source=child.id
                        MERGE (c)<-[:HAS_CHILD]-(p)
                        WITH c, child
                            CALL db.create.setVectorProperty(c, 'embedding', child.embedding)
                        YIELD node
                        RETURN count(*)
                    """,
                    params,
                )
        except Neo4jError as e:
            logging.error(f"Neo4j error in document {documentId}, chunk {i+1}: {e}")
            raise

    return parent_documents



# Process PDF files use the same pattern as Doc
def extract_text_from_pdf(file_content: bytes, filename: str):
    """
    Extract text content from a PDF file.

    Args:
        file_content (bytes): The binary content of the PDF file
        filename (str): Name of the file including extension

    Returns:
        str: The extracted text content from the PDF document

    Raises:
        ValueError: If file format is unsupported or conversion fails
    #TODO : Add OCR for images in PDF
    # TODO: will want to support specific PDF decomposition with semantic chunks reflecting specific PDF structure
    """
    logging.info(f"Processing {filename}")

    # Save file to temp directory
    tmpfile_path = tempfile.gettempdir() + "/" + filename
    with open(tmpfile_path, "wb") as f:
        f.write(file_content)

    if tmpfile_path is None:
        raise ValueError("Failed to save the file content")

    # Load and extract text using PyPDFLoader
    loader = PyPDFLoader(tmpfile_path)
    pages = loader.load()
    
    # Combine text from all pages
    extracted_content = "\n".join([page.page_content for page in pages])

    # Clean up temporary file
    if tmpfile_path and os.path.exists(tmpfile_path):
        os.remove(tmpfile_path)

    return extracted_content



def process_pdf(pdf_folder_path: str, driver):

    # Connect to the database
    with driver.session() as session:
        
        # List all PDF files from the directory
        pdf_files = [f for f in os.listdir(pdf_folder_path) if f.endswith('.pdf')]
        files = [{"name": os.path.splitext(f)[0], "path": os.path.join(pdf_folder_path, f)} for f in pdf_files]

        for file in files[:24]:  # Process only the first N files
            loader = PyPDFLoader(file["path"])
            pages = loader.load_and_split()
            
            # Document properties
            doc_properties = {
                "uuid": str(uuid.uuid4()),
                "name": file["name"],
                "title": pages[0].page_content.split("\n")[0],  
                "url": file["path"],
                "sourceUrl": pages[0].metadata["source"], 
                "thumbnailUrl": "Some Thumbnail URL",  
                "fullText": pages[0].page_content
            }
            # Add Document to Neo4j
            doc_node = session.write_transaction(add_document, doc_properties)

            # Add Pages and Chunks
            for i, page in enumerate(pages):
                # Page properties
                page_properties = {
                    "uuid": str(uuid.uuid4()),
                    "name": f"Page {i+1}",
                    "fullText": page.page_content  
                }
                # Add Page to Neo4j
                page_node = session.write_transaction(add_page, doc_properties["uuid"], page_properties)
                
                # Split page into chunks and generate embeddings
                text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=0, length_function=len)
                chunks = text_splitter.split_documents([page])
                embeddings = OpenAIEmbeddings()
                
                # Add each chunk
                for j, chunk in enumerate(chunks):
                    chunk_properties = {
                        "uuid": str(uuid.uuid4()),
                        "name": f"Chunk {j+1}",
                        "embedding": embeddings.embed_query(chunk.page_content),  # Replace with actual embedding
                        "fullText": chunk.page_content  # Replace with actual text for the chunk
                    }
                    session.write_transaction(add_chunk, page_properties["Uuid"], chunk_properties)

        # Setup the source for the chunks
        session.write_transaction(setupSourceChunks)
