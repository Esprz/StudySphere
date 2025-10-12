# Environment Configuration

The recommender system now uses environment variables for configuration instead of hardcoded values.

## Required Environment Variables

Create a `.env` file in the `recommender_system` directory with the following variables:

```bash
# Database Configuration
DATABASE_URL=postgresql://postgres:password@db:5432/studysphere

# Qdrant Vector Database Configuration
QDRANT_HOST=qdrant
QDRANT_PORT=6333
QDRANT_DIM_POST=384
QDRANT_DIM_USER=384

# Kafka Configuration
KAFKA_BROKERS=kafka:9092

# Application Configuration
PYTHONUNBUFFERED=1
LOG_LEVEL=INFO

# CORS Configuration
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
CORS_CREDENTIALS=true
CORS_METHODS=*
CORS_HEADERS=*

# Vector Database Configuration (Qdrant only)
VECTOR_DIM_POST=384
VECTOR_DIM_USER=384

# Recommendation Configuration
DEFAULT_RECOMMENDATION_LIMIT=20
MAX_RECOMMENDATION_LIMIT=100
```

## Configuration Details

### Database Configuration
- `DATABASE_URL`: PostgreSQL connection string

### Qdrant Vector Database
- `QDRANT_HOST`: Qdrant server hostname (default: qdrant)
- `QDRANT_PORT`: Qdrant server port (default: 6333)
- `QDRANT_DIM_POST`: Post embedding dimension (default: 384)
- `QDRANT_DIM_USER`: User embedding dimension (default: 384)

### Kafka Configuration
- `KAFKA_BROKERS`: Kafka broker addresses (default: kafka:9092)

### Application Configuration
- `PYTHONUNBUFFERED`: Python output buffering (default: 1)
- `LOG_LEVEL`: Logging level (default: INFO)

### CORS Configuration
- `CORS_ORIGINS`: Allowed origins (comma-separated, default: http://localhost:5173)
- `CORS_CREDENTIALS`: Allow credentials (default: true)
- `CORS_METHODS`: Allowed HTTP methods (comma-separated, default: *)
- `CORS_HEADERS`: Allowed headers (comma-separated, default: *)

### Vector Database Configuration
- `VECTOR_DIM_POST`: Post embedding dimension (default: 384)
- `VECTOR_DIM_USER`: User embedding dimension (default: 384)

### Recommendation Configuration
- `DEFAULT_RECOMMENDATION_LIMIT`: Default number of recommendations (default: 20)
- `MAX_RECOMMENDATION_LIMIT`: Maximum number of recommendations (default: 100)

## Docker Compose Integration

The docker-compose.yml file has been updated to use the `.env` file:

```yaml
recommender:
  # ... other configuration
  env_file:
    - ./recommender_system/.env
  environment:
    - PYTHONUNBUFFERED=1
    - DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}
    - KAFKA_BROKERS=kafka:9092
```

## Usage

1. Copy the environment variables above into a `.env` file in the `recommender_system` directory
2. Adjust the values according to your environment
3. The application will automatically load these variables on startup
