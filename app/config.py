from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    # Database
    DATABASE_URL: str = "postgresql://postgres:mysecretpassword@localhost:5432/postgres"
    
    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # AI
    HUGGINGFACE_API_KEY: str
    
    # Redis (Optional)
    REDIS_URL: Optional[str] = None
    CACHE_ENABLED: bool = False
    
    # App
    APP_NAME: str = "Intelligent Content API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    

settings = Settings()