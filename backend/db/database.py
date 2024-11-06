"""
Database module for Neo4j connection management.

This module provides a singleton database connection manager for Neo4j,
handling connection initialization, session management, and cleanup.
It uses configuration from the CurrentConfig object for database credentials
and connection settings.

Key Components:
- Neo4jDatabase: Main database connection manager class
- get_db: Factory function to get/create database instance
- db: Global database instance for backward compatibility
"""

from neo4j import GraphDatabase
from backend.config import CurrentConfig
import logging

logger = logging.getLogger(__name__)

class Neo4jDatabase:
    """
    Neo4j database connection manager implementing the singleton pattern.
    
    Handles database connection lifecycle including initialization,
    session management, and cleanup. Uses provided config or falls back
    to CurrentConfig for connection settings.
    
    Attributes:
        config: Configuration object containing Neo4j connection settings
        driver: Neo4j driver instance for database connections
    """

    def __init__(self, config=None):
        """
        Initialize database manager with optional config.

        Args:
            config: Optional configuration object. Uses CurrentConfig if not provided.
        """
        self.config = config or CurrentConfig
        self.driver = None
        self._initialize()

    def _initialize(self):
        """
        Initialize the Neo4j driver connection.
        
        Closes any existing connection before creating a new one.
        Raises any connection errors after logging them.
        """
        if self.driver:
            self.close()
        try:
            self.driver = GraphDatabase.driver(
                self.config.NEO4J_URI,
                auth=(self.config.NEO4J_USER, self.config.NEO4J_PASSWORD)
            )
            logger.info("Connected to Neo4j database.")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise e

    def reinitialize(self):
        """Public method to reinitialize the database connection."""
        self._initialize()

    def close(self):
        """
        Close the database connection and cleanup resources.
        
        Sets driver to None after closing to allow garbage collection.
        """
        if self.driver:
            self.driver.close()
            self.driver = None
            logger.info("Neo4j driver closed.")

    def get_session(self):
        """
        Get a new Neo4j session, initializing connection if needed.
        
        Returns:
            Neo4j session object for database operations
        """
        if not self.driver:
            self._initialize()
        return self.driver.session()

# Create a function to get or create the database instance
_db_instance = None

def get_db(config=None):
    """
    Factory function to get or create Neo4j database instance.
    
    Implements singleton pattern with optional config override.
    
    Args:
        config: Optional configuration object to override defaults
        
    Returns:
        Neo4jDatabase: Singleton database instance
    """
    global _db_instance
    if config:
        # If config is provided, create a new instance with that config
        if _db_instance:
            _db_instance.close()
        _db_instance = Neo4jDatabase(config)
    elif _db_instance is None:
        # If no config provided and no instance exists, create with default config
        _db_instance = Neo4jDatabase()
    return _db_instance

# For backward compatibility
db = get_db()
