from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import recommendations
from .utils.env_config import EnvConfig

app = FastAPI(title="StudySphere Recommender System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=EnvConfig.CORS_ORIGINS,
    allow_credentials=EnvConfig.CORS_CREDENTIALS,
    allow_methods=EnvConfig.CORS_METHODS,
    allow_headers=EnvConfig.CORS_HEADERS,
)

app.include_router(recommendations.router)


@app.get("/")
async def root():
    return {"message": "StudySphere Recommender System API"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
