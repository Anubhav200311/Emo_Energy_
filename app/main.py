from fastapi import FastAPI
from app.routers import auth, content
from app.config import settings
from app.database import create_tables
import logging

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="An intelligent API that processes content using AI",
)


@app.on_event("startup")
async def startup_event():
    """Create database tables on startup."""
    create_tables()
    logging.info("Database tables created successfully")

# Include Routers
app.include_router(auth.router)
app.include_router(content.router)
