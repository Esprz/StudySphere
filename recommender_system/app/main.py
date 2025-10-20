from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import recommendations
from .config import redis_config
from .utils.env_config import EnvConfig
from loguru import logger

app = FastAPI(title="StudySphere Recommender System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=EnvConfig.CORS_ORIGINS,
    allow_credentials=EnvConfig.CORS_CREDENTIALS,
    allow_methods=EnvConfig.CORS_METHODS,
    allow_headers=EnvConfig.CORS_HEADERS,
)

app.include_router(recommendations.router)


@app.on_event("startup")
async def startup_event():
    """Initialize Redis connection on startup"""
    try:
        is_connected = await redis_config.ping()
        if is_connected:
            logger.info("Redis connection established successfully")
        else:
            logger.warning("Redis connection failed - continuing without cache")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Close Redis connection on shutdown"""
    try:
        await redis_config.close()
        logger.info("Redis connection closed")
    except Exception as e:
        logger.error(f"Error closing Redis connection: {e}")


@app.get("/")
async def root():
    return {"message": "StudySphere Recommender System API"}


@app.get("/health")
async def health_check():
    """Health check endpoint including Redis status"""
    try:
        redis_healthy = await redis_config.ping()
        return {
            "status": "healthy",
            "redis": "connected" if redis_healthy else "disconnected",
            "services": {
                "recommender": "running",
                "redis": "connected" if redis_healthy else "disconnected"
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "redis": "error",
            "error": str(e)
        }


@app.get("/cache/stats")
async def cache_stats():
    """Get Redis cache statistics"""
    try:
        stats = await redis_config.get_cache_stats()
        return {"cache_stats": stats}
    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}")
        return {"error": str(e)}
