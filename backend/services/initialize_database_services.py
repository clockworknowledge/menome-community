"""
Database Initialization Services Module

This module provides functionality for initializing and setting up the Neo4j database and MinIO storage.
It handles creating database constraints, indexes, roles, and initial admin user setup.

Functions:
    create_base_roles: Creates basic role nodes in the database
    initialize_database: Sets up initial database state including admin user and roles
    initialize_index: Creates all required database constraints and indexes
    initialize_minio: Sets up MinIO buckets for file storage
"""

from neo4j import GraphDatabase

from backend.config import CurrentConfig
from backend.schemas.user import UserIn
from backend.services.user_service import create_user_from_schema
from backend.config import UserRole
from backend.services.user_service import add_roles_to_user
from neo4j.exceptions import Neo4jError
from backend.config import BaseConfig, CurrentConfig
import logging
from backend.db.database import db
import json

logger = logging.getLogger(__name__)

def create_base_roles():
    """
    Create the basic role nodes in the database.

    Creates Role nodes for each UserRole enum value if they don't already exist.
    Each role gets a UUID and creation timestamp.

    Returns:
        list: Messages indicating success/failure of role creation
    """
    messages = []
    with db.get_session() as session:
        for role in UserRole:
            try:
                result = session.run("""
                    MERGE (r:Role {name: $role})
                    ON CREATE SET r.uuid = randomUUID(),
                                r.created = datetime()
                    RETURN r
                """, role=role.value)
                messages.append(f"Created/verified role: {role.value}")
            except Exception as e:
                messages.append(f"Error creating role {role.value}: {str(e)}")
    return messages

def initialize_database(admin_user: UserIn):
    """
    Initialize the database with required setup and admin user.

    Creates initial database indexes, constraints, admin user and roles.

    Args:
        admin_user (UserIn): Admin user details for creating initial admin account

    Returns:
        list: Messages indicating progress and status of initialization steps
    """
    messages = []
    messages.append("Initializing database...")
    messages.extend(initialize_index())

    messages.append("Creating admin user...")
    try:
        create_user_from_schema(admin_user)
        messages.append("Admin user created successfully.")
    except Exception as e:
        if "already exists" in str(e).lower():
            messages.append("Admin user already exists, continuing...")
        else:
            messages.append(f"Error creating admin user: {str(e)}")

    # Create base roles first
    messages.append("Creating base roles...")
    messages.extend(create_base_roles())

    # Then assign roles to the admin user
    messages.append("Assigning roles to admin user...")
    roles = [role.value for role in UserRole]
    add_roles_to_user(admin_user.username, roles)

    return messages

def initialize_index():
    """
    Initialize all required database constraints and indexes.

    Creates:
    - Uniqueness constraints for UUIDs and emails
    - Name indexes for documents and categories
    - Full text search indexes
    - Vector indexes for embeddings
    
    Returns:
        list: Messages indicating success/failure of index/constraint creation
    """
    driver = GraphDatabase.driver(CurrentConfig.NEO4J_URI, auth=(CurrentConfig.NEO4J_USER, CurrentConfig.NEO4J_PASSWORD))
    messages = []
    embedding_dimension = CurrentConfig.EMBEDDING_DIMENSION

    with driver.session() as session:
        # Create UUID constraint for User
        try:
            session.run("CREATE CONSTRAINT unique_user_uuid FOR (u:User) REQUIRE u.uuid IS UNIQUE")
            messages.append("Created UUID constraint for User.")
        except Neo4jError as e:
            if "EquivalentSchemaRuleAlreadyExists" in str(e):
                messages.append("UUID constraint for User already exists.")
            else:
                messages.append(f"Error creating UUID constraint for User: {str(e)}")
        
        # Create Email constraint for User
        try:
            session.run("CREATE CONSTRAINT unique_user_email FOR (u:User) REQUIRE u.email IS UNIQUE")
            messages.append("Created email constraint for User.")
        except Neo4jError as e:
            if "EquivalentSchemaRuleAlreadyExists" in str(e):
                messages.append("Email constraint for User already exists.")
            else:
                messages.append(f"Error creating email constraint for User: {str(e)}")

        # Create document uuid constraint
        try:
            session.run("CREATE CONSTRAINT document_unique_uuid FOR (u:Document) REQUIRE u.uuid IS UNIQUE")
            messages.append("Created UUID constraint for Document.")
        except Neo4jError as e:
            if "EquivalentSchemaRuleAlreadyExists" in str(e):
                messages.append("UUID constraint for Document already exists.")
            else:
                messages.append(f"Error creating UUID constraint for Document: {str(e)}")
        
        # create constraint for Category
        try:
            session.run("CREATE CONSTRAINT category_unique_uuid FOR (u:Category) REQUIRE u.uuid IS UNIQUE")
            messages.append("Created UUID constraint for Category.")
        except Neo4jError as e:
            if "EquivalentSchemaRuleAlreadyExists" in str(e):
                messages.append("UUID constraint for Category already exists.")
            else:
                messages.append(f"Error creating UUID constraint for Category: {str(e)}")

        # Create _community_  constraint
        try:
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (c:Community) REQUIRE c.name IS UNIQUE;")
            messages.append("Created name constraint for Community.")
        except Neo4jError as e:
            if "EquivalentSchemaRuleAlreadyExists" in str(e):
                messages.append("Name constraint for Community already exists.")
            else:
                messages.append(f"Error creating name constraint for Community: {str(e)}")

        # Create index for name on Document
        try:
            session.run("CREATE INDEX document_name FOR (n:Document) ON (n.name)")
            messages.append("Created name index for Document.")
        except Neo4jError as e:
            if "EquivalentSchemaRuleAlreadyExists" in str(e):
                messages.append("Name index for Document already exists.")
            else:
                messages.append(f"Error creating name index for Document: {str(e)}")
    
        # Create index for name on Category
        try:
            session.run("CREATE INDEX category_name_index FOR (c:Category) ON (c.name);")
            messages.append("Created name index for Category.")
        except Neo4jError as e:
            if "EquivalentSchemaRuleAlreadyExists" in str(e):
                messages.append("Name index for Category already exists.")
            else:
                messages.append(f"Error creating name index for Category: {str(e)}")

        # Create index for wcc on Category
        try:
            session.run("CREATE INDEX category_wcc_index FOR (c:Category) ON (c.wcc);")
            messages.append("Created WCC index for Category.")
        except Neo4jError as e:
            if "EquivalentSchemaRuleAlreadyExists" in str(e):
                messages.append("WCC index for Category already exists.")
            else:
                messages.append(f"Error creating WCC index for Category: {str(e)}")

        # Create full text index for Document
        try: 
            session.run("CREATE FULLTEXT INDEX titlesAndDescriptions FOR (n:Document) ON EACH [n.name, n.summary, n.text]")
            messages.append("Created full text index for Document.")
        except Neo4jError as e:
            if "EquivalentSchemaRuleAlreadyExists" in str(e):
                messages.append("Full text index for Document already exists.")
            else:
                messages.append(f"Error creating full text index for Document: {str(e)}")

        # Create page uuid constraint
        try:
            session.run("CREATE CONSTRAINT page_unique_uuid FOR (u:Page) REQUIRE u.uuid IS UNIQUE")
            messages.append("Created UUID constraint for Page.")
        except Neo4jError as e:
            if "EquivalentSchemaRuleAlreadyExists" in str(e):
                messages.append("UUID constraint for Page already exists.")
            else:
                messages.append(f"Error creating UUID constraint for Page: {str(e)}")

        # Create full text index for Page
        try: 
            session.run("CREATE FULLTEXT INDEX pageNameAndText FOR (n:Page) ON EACH [n.name, n.summary, n.text]")
            messages.append("Created full text index for Page.")
        except Neo4jError as e:
            if "EquivalentSchemaRuleAlreadyExists" in str(e):
                messages.append("Full text index for Page already exists.")
            else:
                messages.append(f"Error creating full text index for Page: {str(e)}")
        
        # Create child uuid constraint
        try:
            session.run("CREATE CONSTRAINT child_unique_uuid FOR (u:Child) REQUIRE u.uuid IS UNIQUE")
            messages.append("Created UUID constraint for Child.")
        except Neo4jError as e:
            if "EquivalentSchemaRuleAlreadyExists" in str(e):
                messages.append("UUID constraint for Child already exists.")
            else:
                messages.append(f"Error creating UUID constraint for Child: {str(e)}")

        # Create full text index for Child
        try: 
            session.run("CREATE FULLTEXT INDEX childNameAndText FOR (n:Child) ON EACH [n.name, n.summary, n.text]")
            messages.append("Created full text index for Child.")
        except Neo4jError as e:
            if "EquivalentSchemaRuleAlreadyExists" in str(e):
                messages.append("Full text index for Child already exists.")
            else:
                messages.append(f"Error creating full text index for Child: {str(e)}")

        # Create vector indexes
        # Create vector index for child
        try:
            session.run(
                "CALL db.index.vector.createNodeIndex('parent_document', 'Child', 'embedding', $dimension, 'cosine')",
                {"dimension": embedding_dimension},
            )
            messages.append("Created vector index for parent_document.")
        except Neo4jError as e:
            if "EquivalentSchemaRuleAlreadyExists" in str(e):
                messages.append("Vector index for parent_document already exists.")
            else:
                messages.append(f"Error creating vector index for parent_document: {str(e)}")

        # Create vector index for pages
        try:
            session.run(
                "CALL db.index.vector.createNodeIndex('typical_rag', 'Page', 'embedding', $dimension, 'cosine')",
                {"dimension": embedding_dimension},
            )
            messages.append("Created vector index for typical_rag.")
        except Neo4jError as e:
            if "EquivalentSchemaRuleAlreadyExists" in str(e):
                messages.append("Vector index for typical_rag already exists.")
            else:
                messages.append(f"Error creating vector index for typical_rag: {str(e)}")

        # Create vector index for questions
        try:
            session.run(
                "CALL db.index.vector.createNodeIndex('hypothetical_questions', 'Question', 'embedding', $dimension, 'cosine')",
                {"dimension": embedding_dimension},
            )
            messages.append("Created vector index for hypothetical_questions.")
        except Neo4jError as e:
            if "EquivalentSchemaRuleAlreadyExists" in str(e):
                messages.append("Vector index for hypothetical_questions already exists.")
            else:
                messages.append(f"Error creating vector index for hypothetical_questions: {str(e)}")
        
        # Create vector index for summary
        try:
            session.run(
                "CALL db.index.vector.createNodeIndex('summary', 'Summary', 'embedding', $dimension, 'cosine')",
                {"dimension": embedding_dimension},
            )
            messages.append("Created vector index for summary.")
        except Neo4jError as e:
            if "EquivalentSchemaRuleAlreadyExists" in str(e):
                messages.append("Vector index for summary already exists.")
            else:
                messages.append(f"Error creating vector index for summary: {str(e)}")

        # Create document text index
        try: 
            session.run("CREATE FULLTEXT INDEX documentTextIndex FOR (d:Document) ON EACH [d.text]")
            messages.append("Created full text index for Document text.")
        except Neo4jError as e:
            if "EquivalentSchemaRuleAlreadyExists" in str(e):
                messages.append("Full text index for Document text already exists.")
            else:
                messages.append(f"Error creating full text index for Document text: {str(e)}")

        # Create page text index
        try: 
            session.run("CREATE FULLTEXT INDEX pageTextIndex FOR (p:Page) ON EACH [p.text]")
            messages.append("Created full text index for Page text.")
        except Neo4jError as e:
            if "EquivalentSchemaRuleAlreadyExists" in str(e):
                messages.append("Full text index for Page text already exists.")
            else:
                messages.append(f"Error creating full text index for Page text: {str(e)}")

    return messages

