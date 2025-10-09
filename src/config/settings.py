"""Application settings"""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения"""
    
    # API Keys
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    
    # Database
    database_url: str = "sqlite:///./productradar.db"
    redis_url: str = "redis://localhost:6379/0"
    
    # Application
    debug: bool = False
    log_level: str = "INFO"
    api_port: int = 8000
    
    # Agent Configuration
    agent_model: str = "gpt-4-turbo-preview"
    agent_temperature: float = 0.7
    agent_max_tokens: int = 2000
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )


# Singleton instance
settings = Settings()

