"""Environment configuration for the recommender system."""

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

    # CORS Configuration
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    CORS_CREDENTIALS = os.getenv("CORS_CREDENTIALS", "true").lower() == "true"
    CORS_METHODS = os.getenv("CORS_METHODS", "*").split(",")
    CORS_HEADERS = os.getenv("CORS_HEADERS", "*").split(",")

    # Vector Database Configuration (Qdrant only)
    VECTOR_DIM_POST = int(os.getenv("VECTOR_DIM_POST", "384"))
    VECTOR_DIM_USER = int(os.getenv("VECTOR_DIM_USER", "384"))

    # Recommendation Configuration
    DEFAULT_RECOMMENDATION_LIMIT = int(os.getenv("DEFAULT_RECOMMENDATION_LIMIT", "20"))
    MAX_RECOMMENDATION_LIMIT = int(os.getenv("MAX_RECOMMENDATION_LIMIT", "100"))
