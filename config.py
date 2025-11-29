from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://postgres:mysecretpassword@localhost:5432/postgres"
    
    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # OpenAI
    # OPENAI_API_KEY: str
    
    # Redis (Optional)
    REDIS_URL: Optional[str] = None
    CACHE_ENABLED: bool = False
    
    # App
    APP_NAME: str = "Intelligent Content API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    class Config:
        env_file = ".env"


settings = Settings()