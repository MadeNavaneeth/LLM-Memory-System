"""
FastAPI Main Application
LLM Memory Management System
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from app.api.routes import users, sessions, conversations, memory, settings
from app.config import API_PREFIX
import logging
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown"""
    logger.info("Starting up LLM Memory System...")
    
    # Verify connections on startup
    from app.database.nosql_connection import get_mongo_db
    mongo = get_mongo_db()
    if mongo.is_connected:
        logger.info("✅ MongoDB connected successfully")
    else:
        logger.warning("❌ MongoDB not connected at startup (will retry on demand)")
    
    yield
    logger.info("Shutting down LLM Memory System...")

# Create FastAPI app
app = FastAPI(
    title="LLM Memory Management System",
    description="AI-Driven Memory Management System for LLMs using SQL + NoSQL databases",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(users.router, prefix=API_PREFIX)
app.include_router(sessions.router, prefix=API_PREFIX)
app.include_router(conversations.router, prefix=API_PREFIX)
app.include_router(memory.router, prefix=API_PREFIX)
app.include_router(settings.router, prefix=API_PREFIX)

# Static files
static_path = Path(__file__).parent.parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")


@app.get("/")
async def root():
    """Serve the frontend application"""
    index_path = static_path / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {
        "message": "LLM Memory Management System API",
        "docs": "/docs",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    from app.database.sql_connection import get_db
    from app.database.nosql_connection import get_mongo_db
    
    db = get_db()
    mongo = get_mongo_db()
    
    return {
        "status": "healthy",
        "sqlite": "connected",
        "mongodb": "connected" if mongo.is_connected else "disconnected"
    }


@app.get("/api")
async def api_info():
    """API information"""
    return {
        "name": "LLM Memory Management System",
        "version": "1.0.0",
        "endpoints": {
            "users": f"{API_PREFIX}/users",
            "sessions": f"{API_PREFIX}/sessions",
            "conversations": f"{API_PREFIX}/conversations",
            "memory": f"{API_PREFIX}/memory"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
