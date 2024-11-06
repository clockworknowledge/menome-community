# backend/initialization.py
from backend.services.initialize_database_services import initialize_database
from backend.config import CurrentConfig
from backend.schemas.user import UserIn
import logging

logger = logging.getLogger(__name__)

def initialize_system_if_enabled():
    if CurrentConfig.DATABASE_INITIALIZATION_ENABLED:
        admin_user = UserIn(
            uuid=CurrentConfig.ADMIN_USER_UUID,
            username=CurrentConfig.ADMIN_USER_USERNAME,
            password=CurrentConfig.ADMIN_USER_PASSWORD,
            email=CurrentConfig.ADMIN_USER_EMAIL,
            name=CurrentConfig.ADMIN_USER_NAME
        )   
        messages = []
        logger.info(f"Current config: {CurrentConfig.NEO4J_PASSWORD}")
        messages.append("Initializing database...")
        messages.extend(initialize_database(admin_user))   
 
    else:
        messages.append("Database initialization is disabled.")
    return messages
