# tests/services/test_document_services.py

import pytest
from bs4 import BeautifulSoup, Comment
from neo4j import GraphDatabase
from datetime import datetime, timedelta
import uuid
import json
from datetime import timezone

from backend.services.document_services import (
    save_token_metadata,
    get_existing_shareable_link,
    get_token_metadata,
    invalidate_token,
    generate_shareable_link,
    validate_share_token,
    get_document_by_uuid
)
from backend.schemas import DefaultIcons
from backend.config import CurrentConfig

@pytest.fixture(scope="module")
def neo4j_driver():
    """
    Fixture to initialize and teardown the Neo4j driver.
    """
    driver = GraphDatabase.driver(
        CurrentConfig.NEO4J_URI,
        auth=(CurrentConfig.NEO4J_USER, CurrentConfig.NEO4J_PASSWORD)
    )
    yield driver
    driver.close()

@pytest.fixture(scope="module")
def test_document(neo4j_driver):
    """
    Fixture to create a test document in the database.
    """
    document_uuid = str(uuid.uuid4())
    # Sample document data
    document = {
        "uuid": document_uuid,
        "name": "Test Document",
        "type": "Article",
        "publisheddate": "2023-01-01",
        "addeddate": "2023-01-02",
        "url": "https://example.com/test-document",
        "text": "This is the content of the test document.",
        "thumbnail": DefaultIcons.ARTICLE_ICON_SVG,
        "image": "https://example.com/test-document/image.png"
    }
    
    # Insert the document into the database
    insert_query = """
    CREATE (d:Document {
        uuid: $uuid,
        name: $name,
        type: $type,
        publisheddate: $publisheddate,
        addeddate: $addeddate,
        url: $url,
        text: $text,
        thumbnail: $thumbnail,
        image: $image
    })
    """
    with neo4j_driver.session() as session:
        session.run(insert_query, **document)
    
    yield document
    
    # Cleanup: Delete the test document
    delete_query = "MATCH (d:Document {uuid: $uuid}) DETACH DELETE d"
    with neo4j_driver.session() as session:
        session.run(delete_query, uuid=document_uuid)

@pytest.fixture(scope="module")
def test_user(neo4j_driver):
    """
    Fixture to create a test user in the database.
    """
    user_uuid = str(uuid.uuid4())
    username = "testuser"
    
    # Insert the user into the database
    insert_query = """
    CREATE (u:User {
        uuid: $uuid,
        username: $username
    })
    """
    with neo4j_driver.session() as session:
        session.run(insert_query, uuid=user_uuid, username=username)
    
    yield {
        "uuid": user_uuid,
        "username": username
    }
    
    # Cleanup: Delete the test user
    delete_query = "MATCH (u:User {uuid: $uuid}) DETACH DELETE u"
    with neo4j_driver.session() as session:
        session.run(delete_query, uuid=user_uuid)


@pytest.fixture(scope="module", autouse=True)
def cleanup_share_tokens(neo4j_driver):
    """
    Fixture to clean up any ShareToken nodes created during tests.
    """
    yield
    # After all tests, delete all ShareToken nodes
    delete_query = "MATCH (st:ShareToken) DETACH DELETE st"
    with neo4j_driver.session() as session:
        session.run(delete_query)

# --------------------------- Integration Tests ---------------------------

def test_token_management_functions(neo4j_driver, test_document, test_user):
    document_uuid = test_document["uuid"]
    user_uuid = test_user["uuid"]

    # Ensure no existing token
    existing_link = get_existing_shareable_link(document_uuid, user_uuid, neo4j_driver)
    assert existing_link is None, "There should be no existing shareable link initially."

    # Save token metadata with timezone-aware expiry
    token = str(uuid.uuid4())  # Use unique token
    format_type = "markdown"    # Define format_type
    expiry = datetime.now(timezone.utc) + timedelta(hours=1)  # Timezone-aware UTC datetime
    save_token_metadata(token, document_uuid, expiry, user_uuid, neo4j_driver, format_type=format_type)

    # Retrieve existing shareable link
    existing_link = get_existing_shareable_link(document_uuid, user_uuid, neo4j_driver)
    assert existing_link is not None, "Shareable link should exist after saving token metadata."
    assert token in existing_link, "Token should be present in the shareable link."
    assert f"format_type={format_type}" in existing_link, "Shareable link should contain the correct format type."
    
    # Get token metadata
    token_data = get_token_metadata(token, neo4j_driver)
    assert token_data is not None, "Token metadata should be retrievable."
    assert token_data["token"] == token
    assert token_data["document_uuid"] == document_uuid
    assert token_data["user_uuid"] == user_uuid
    assert token_data["expiry"] > datetime.now(timezone.utc), "Token should not be expired."
    
    # Validate token
    valid_token_data = validate_share_token(token, document_uuid, neo4j_driver)
    assert valid_token_data["user_uuid"] == user_uuid, "Validated user UUID should match the test user UUID."
    
    # Invalidate token
    invalidate_token(token, neo4j_driver)
    
    # Attempt to retrieve token metadata after invalidation
    token_data = get_token_metadata(token, neo4j_driver)
    assert token_data is None, "Token metadata should be None after invalidation."
    
    # Ensure the shareable link is removed
    existing_link = get_existing_shareable_link(document_uuid, user_uuid, neo4j_driver)
    assert existing_link is None, "Shareable link should be None after token invalidation."

def test_generate_shareable_link(neo4j_driver, test_document, test_user):
    document_uuid = test_document["uuid"]
    user_uuid = test_user["uuid"]
    format_type = "markdown"
    
    # Generate shareable link
    shareable_link = generate_shareable_link(document_uuid, format_type, user_uuid, neo4j_driver)
    assert shareable_link is not None, "Shareable link should be generated."
    assert f"token=" in shareable_link, "Shareable link should contain a token."
    assert f"format_type={format_type}" in shareable_link, "Shareable link should contain the correct format type."
    
    # Attempt to generate another link (should return the existing one)
    second_link = generate_shareable_link(document_uuid, format_type, user_uuid, neo4j_driver)
    assert second_link == shareable_link, "Should return the existing shareable link if it's still valid."
    
    # Cleanup: Invalidate the token
    token = shareable_link.split("token=")[1].split("&")[0]
    invalidate_token(token, neo4j_driver)
    
    # Generate a new link after invalidation
    new_shareable_link = generate_shareable_link(document_uuid, format_type, user_uuid, neo4j_driver)
    assert new_shareable_link != shareable_link, "A new shareable link should be generated after invalidation."
    assert f"token=" in new_shareable_link, "New shareable link should contain a new token."

def test_get_document_by_uuid(neo4j_driver, test_document):
    document_uuid = test_document["uuid"]
    
    # Retrieve the document
    document = get_document_by_uuid(document_uuid, neo4j_driver)
    assert document is not None, "Document should be retrievable by UUID."
    assert document["uuid"] == document_uuid, "Retrieved document UUID should match."
    
    # Attempt to retrieve a non-existent document
    fake_uuid = str(uuid.uuid4())
    document = get_document_by_uuid(fake_uuid, neo4j_driver)
    assert document is None, "Retrieving a non-existent document should return None."
