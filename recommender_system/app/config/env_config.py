import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class EnvConfig:
    """Environment configuration class."""

    # Database Configuration
    DATABASE_URL = os.getenv(
        "DATABASE_URL", "postgresql://postgres:password@db:5432/studysphere"
    )

    # Qdrant Vector Database Configuration
    QDRANT_HOST = os.getenv("QDRANT_HOST", "qdrant")
    QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
    QDRANT_DIM_POST = int(os.getenv("QDRANT_DIM_POST", "384"))
    QDRANT_DIM_USER = int(os.getenv("QDRANT_DIM_USER", "384"))

    # Kafka Configuration
    KAFKA_BROKERS = os.getenv("KAFKA_BROKERS", "kafka:9092")

    # Application Configuration
    PYTHONUNBUFFERED = os.getenv("PYTHONUNBUFFERED", "1")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    # FAISS Configuration
    FAISS_PERSIST_DIR = os.getenv("FAISS_PERSIST_DIR", "./app/faiss_data")
    FAISS_DIM_POST = int(os.getenv("FAISS_DIM_POST", "384"))
    FAISS_DIM_USER = int(os.getenv("FAISS_DIM_USER", "384"))

    # Recommendation Configuration
    DEFAULT_RECOMMENDATION_LIMIT = int(os.getenv("DEFAULT_RECOMMENDATION_LIMIT", "20"))
    MAX_RECOMMENDATION_LIMIT = int(os.getenv("MAX_RECOMMENDATION_LIMIT", "100"))
