from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="StudySphere Recommender System")

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "StudySphere Recommender System API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from app.routers import recommendations
    
    app = FastAPI(title="StudySphere Recommender System")
    
    # Set up CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.include_router(recommendations.router)
    
    @app.get("/")
    async def root():
        return {"message": "StudySphere Recommender System API"}
    
    @app.get("/health")
    async def health_check():
        return {"status": "healthy"}