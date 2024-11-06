#!/usr/bin/env python

import logging
import sys
import time
import typer
from pathlib import Path
from backend.initialization import initialize_system_if_enabled
from backend.config import CurrentConfig
import os

# Add the project root to Python path if needed
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root))

# Set the config file path to the root .env file before importing CurrentConfig
config_path = project_root / ".env"
os.environ["CONFIG_FILE_PATH"] = str(config_path.resolve())
os.environ["ENV_MODE"] = "local"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Now import CurrentConfig after setting the env var
from backend.config import CurrentConfig

# Determine which configuration to load
env_mode = os.getenv("ENV_MODE", "local")
logger.info(f"Environment Mode: {env_mode}")
logger.info(f"Current Config: {CurrentConfig}")

def main(
    force: bool = typer.Option(False, "--force", "-f", help="Force initialization by enabling it in config"),
    wait: int = typer.Option(30, "--wait", "-w", help="Seconds to wait for services to be ready"),
    neo4j_url: str = typer.Option(None, "--neo4j-url", help="Override Neo4j URL (e.g., bolt://localhost:7687)"),
    neo4j_user: str = typer.Option(None, "--neo4j-user", help="Override Neo4j user"),
    neo4j_password: str = typer.Option(None, "--neo4j-password", help="Override Neo4j password")
):
    """Initialize the stack including database and MinIO"""
    logger.info("Starting stack initialization...")
    
    if force:
        CurrentConfig.DATABASE_INITIALIZATION_ENABLED = True
    
    if neo4j_url:
        logger.info(f"Overriding Neo4j URL to: {neo4j_url}")
        CurrentConfig.NEO4J_URI = neo4j_url
    
    if neo4j_user:
        logger.info(f"Overriding Neo4j user to: {neo4j_user}")
        CurrentConfig.NEO4J_USER = neo4j_user

    if neo4j_password:
        logger.info(f"Overriding Neo4j password")
        CurrentConfig.NEO4J_PASSWORD = neo4j_password
        
    if neo4j_url or neo4j_user or neo4j_password:
        # Update the database instance with the new config
        from backend.db.database import get_db
        get_db(CurrentConfig)  # This will reinitialize the database with the new config
        
    try:
        # Wait for services if specified
        if wait > 0:
            logger.info(f"Waiting up to {wait} seconds for services to be ready...")
            for i in range(wait):
                try:
                    # Simple connection test to services could go here
                    break
                except Exception:
                    if i == wait - 1:
                        logger.error("Services failed to become ready in time")
                        sys.exit(1)
                    time.sleep(1)

        # Run initialization
        messages = initialize_system_if_enabled()
        
        # Log all messages
        for message in messages:
            logger.info(message)

        if "Database initialization is disabled." in messages:
            logger.warning("Initialization was skipped because it is disabled in config")
            logger.info("Use --force to override this setting")
            sys.exit(1)
            
        logger.info("Stack initialization completed successfully")

    except Exception as e:
        logger.error(f"Stack initialization failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    typer.run(main)