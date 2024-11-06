import os
from decouple import Config, Csv, RepositoryEnv
from enum import Enum
import logging

logger = logging.getLogger(__name__)

# Determine which configuration to load
env_mode = os.getenv("ENV_MODE", "development").lower()
# Add ability to override config file location
DOTENV_FILE = os.getenv("CONFIG_FILE_PATH")

if not DOTENV_FILE:
    if env_mode == "test":
        DOTENV_FILE = './config/.env.test'
        logging.basicConfig(level=logging.DEBUG)
    elif env_mode == "development":
        DOTENV_FILE = './config/.env.dev'
        logging.basicConfig(level=logging.DEBUG)
    else:  # Production mode
        DOTENV_FILE = './config/.env'
        logging.basicConfig(level=logging.INFO)

logger.debug(f"Environment Mode: {env_mode}")

# Convert relative path to absolute path
absolute_path = os.path.abspath(DOTENV_FILE)
print(f"Loading configuration from: {absolute_path}")

# Now use the absolute path in your Config
config = Config(RepositoryEnv(absolute_path))
# Output environment and path to debug log

# Log the environment and path
logger.debug(f"Environment Mode: {env_mode}")
logger.debug(f"Configuration File Path: {absolute_path}")


# "User Contributed", "Document", "Generated Research", "Agent Contributed", "Generated Article", "Note", "Research"
class ValidTypes(Enum):
    All="All"
    Document = "Document"
    UserContributed = "User Contributed"
    GeneratedResearch = "Generated Research"
    AgentContributed = "Agent Contributed"
    GeneratedArticle = "Generated Article"
    Note = "Note"
    Research = "Research"
    Memory = "Memory"
    # Add more types as needed

class UserRole(str, Enum):
    ADMIN = "Admin"
    EDITOR = "Editor"
    CONTRIBUTOR = "Contributor"
    SEARCHER = "Searcher"
    VIEWER = "Viewer"

class BaseConfig:
    CONFIG_VERSION=config('CONFIG_VERSION')
    CONFIG_MODE=config('CONFIG_MODE')
    
    # Common configuration
    OPENAI_API_KEY = config('OPENAI_API_KEYS')
    EMBEDDING_DIMENSION = config('EMBEDDING_DIMENSION', cast=int, default=1536)
    OPENAI_CHAT_MODEL = config('OPENAI_CHAT_MODEL', default='gpt-4o')
    OPENAI_EXTRACTION_MODEL = config('OPENAI_EXTRACTION_MODEL', default='gpt-4o-mini')
    OPENAI_EMBEDDING_MODEL = config('OPENAI_EMBEDDING_MODEL', default='text-embedding-3-small')
    TAVILY_API_KEY = config('TAVILY_API_KEY')

    # API Configuration
    API_PORT = config('API_PORT', cast=int, default=8000)
    API_ACCESS_TOKEN_EXPIRE_MINUTES = config('API_ACCESS_TOKEN_EXPIRE_MINUTES', cast=int, default=30)
    SECRET_KEY=config('SECRET_KEY')
    ALGORITHM=config('ALGORITHM')
    DOCUMENT_ACCESS_TOKEN_EXPIRE_MINUTES = config('DOCUMENT_ACCESS_TOKEN_EXPIRE_MINUTES', cast=int, default=30)
    INVALIDATE_TOKEN_AFTER_USE = config('INVALIDATE_TOKEN_AFTER_USE', cast=bool, default=True)
    LOG_LEVEL = config('LOG_LEVEL', default='DEBUG')
    BLOCKER_JSON_PATH = config('BLOCKER_JSON_PATH', default='./backend/config_blockers.json')

    # NEO4J configuration
    NEO4J_URI = config.get('NEO4J_URI', default='bolt://localhost:7687')
    NEO4J_USER = config.get('NEO4J_USER', default='neo4j')
    NEO4J_PASSWORD = config('NEO4J_PASSWORD')
    NEO4J_INDEX_NAME = config('NEO4J_INDEX_NAME', default='typical_rag')
    NEO4J_CHUNK_LABEL = config('NEO4J_CHUNK_LABEL', default='Child')
    NEO4J_CHUNK_TEXT_PROPERTY = config('NEO4J_CHUNK_TEXT_PROPERTY', default='text')
    NEO4J_CHUNK_EMBEDDING_PROPERTY = config('NEO4J_CHUNK_EMBEDDING_PROPERTY', default='embedding')
    PAGE_TEXT_INDEX = config('PAGE_TEXT_INDEX', default='pageTextIndex')
    DOCUMENT_TEXT_INDEX=config('DOCUMENT_TEXT_INDEX', default='documentTextIndex')
    FULL_TEXT_SCORE_THRESHOLD=config('FULL_TEXT_SCORE_THRESHOLD', cast=float, default=0.7)

    # RabbitMQ configuration  
    RABBITMQ_HOST = config('RABBMITMQ_HOST', default='localhost')
    RABBITMQ_PORT = config('RABBMITMQ_PORT', cast=int, default=5672)
    RABBITMQ_USER = config('RABBITMQ_USER', default='admin')
    RABBITMQ_PASSWORD = config('RABBITMQ_PASSWORD')

    # MinIO configuration
    MINIO_ENDPOINT = config('MINIO_ENDPOINT', default='localhost:9000')
    MINIO_ACCESS_KEY = config('MINIO_ACCESS_KEY')
    MINIO_SECRET_KEY = config('MINIO_SECRET_KEY')
    MINIO_SECURE_UPLOAD = config('MINIO_SECURE_UPLOAD', cast=bool, default=False)
    MINIO_SECURE_DOWNLOAD = config('MINIO_SECURE_DOWNLOAD', cast=bool, default=True)
    MINIO_NOTES_BUCKET = config('MINIO_NOTES_BUCKET', default='notes')
    MINIO_FILES_BUCKET = config('MINIO_FILES_BUCKET', default='files')
    MINIO_ENDPOINT_EXTERNAL = config('MINIO_ENDPOINT_EXTERNAL', default='minio.menome.com')
    MINIO_SECURE = config('MINIO_SECURE', cast=bool, default=True)
    MINIO_ROOT_USER = config('MINIO_ROOT_USER')
    MINIO_ROOT_PASSWORD = config('MINIO_ROOT_PASSWORD')
    
    # Celery configuration
    CELERY_BROKER_URL = config.get('CELERY_BROKER_URL', default='amqp://guest:guest@localhost:5672//')
    CELERY_RESULT_BACKEND_URL = config.get('CELERY_RESULT_BACKEND_URL', default='rpc://')
    CELERY_NEO4_URL = config.get('CELERY_NEO4J_URL', default='bolt://localhost:7687')
    MAX_QUESTIONS_PER_PAGE = config('MAX_QUESTIONS_PER_PAGE', cast=int, default=2)
    TEST_DOCUMENT_URL = "https://en.wikipedia.org/wiki/As_We_May_Think"
    MAX_CONCURRENT_TASKS = config('MAX_CONCURRENT_TASKS', cast=int, default=2)

    # State processing messages:
    # Task states and celery configuration 
    PROCESSING_DOCUMENT = 'PROCESSING_DOCUMENT'
    PROCESSING_QUESTIONS = 'PROCESSING_QUESTIONS'
    PROCESSING_SUMMARY = 'PROCESSING_SUMMARY'
    PROCESSING_DONE = 'PROCESSING_DONE'
    PROCESSING_FAILED = 'PROCESSING_FAILED'
    PROCESSING_PAGES = 'PROCESSING_PAGES'

    # Context Generation:
    SIMILARITY_THRESHOLD = config('SIMILARITY_THRESHOLD', cast=float, default=0.8)
    NODE_LIST = config('NODE_LIST', default='Person, Organization, Location, Event, Date')
    RELATIONSHIP_LIST = config('RELATIONSHIP_LIST', default='MENTIONS')

    # Database Initialization
    DATABASE_INITIALIZATION_ENABLED = config('DATABASE_INITIALIZATION_ENABLED', cast=bool, default=True)
    ADMIN_USER_UUID = config('ADMIN_USER_UUID')
    ADMIN_USER_USERNAME = config('ADMIN_USER_USERNAME')
    ADMIN_USER_PASSWORD = config('ADMIN_USER_PASSWORD')
    ADMIN_USER_EMAIL = config('ADMIN_USER_EMAIL')
    ADMIN_USER_NAME = config('ADMIN_USER_NAME')

     # Enum for valid types
    VALID_TYPES = ValidTypes

    @classmethod
    def initialize_environment_variables(cls):
        os.environ["OPENAI_API_KEY"] = cls.OPENAI_API_KEY
        os.environ["NEO4J_URI"] = cls.NEO4J_URI
        os.environ["NEO4J_USERNAME"] = cls.NEO4J_USER
        os.environ["NEO4J_PASSWORD"] = cls.NEO4J_PASSWORD
        os.environ['TAVILY_API_KEY'] = cls.TAVILY_API_KEY

class DevelopmentConfig(BaseConfig):
    ROOT_PATH = ""
    SITE_URL=config('FRONTEND_ORIGIN_DEV')

class ProductionConfig(BaseConfig):
    ROOT_PATH = "/"
    SITE_URL=config('FRONTEND_ORIGIN_PROD')

class TestConfig(BaseConfig):
    SITE_URL=config('FRONTEND_ORIGIN_TEST')
    ROOT_PATH = ""


# Determine which configuration to load
if env_mode == "production":
    CurrentConfig = ProductionConfig
elif env_mode == "test":
    CurrentConfig = TestConfig  
else:
    CurrentConfig = DevelopmentConfig

# Initialize environment variables
CurrentConfig.initialize_environment_variables()

