"""
Configuration management for the RRI Orchestrator.

This module handles all application settings using Pydantic Settings,
which automatically loads values from environment variables and .env files.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application configuration loaded from environment variables.
    
    All settings can be overridden by creating a .env file in the project root.
    See .env.example for the template.
    """
    
    # Database Configuration
    database_url: str = Field(
        default="postgresql+asyncpg://rri_user:rri_password@localhost:5432/rri_orchestrator",
        description="PostgreSQL connection string for async operations"
    )
    
    # AI Service API Keys
    gemini_api_key: str = Field(
        default="",
        description="Google Gemini API key for AI interactions"
    )
    openai_api_key: str = Field(
        default="",
        description="OpenAI API key as fallback provider"
    )
    
    # Application Configuration
    environment: str = Field(
        default="development",
        description="Runtime environment: development, staging, or production"
    )
    secret_key: str = Field(
        default="dev-secret-key-change-in-production",
        description="Secret key for session management and encryption"
    )
    
    # Server Configuration
    host: str = Field(
        default="0.0.0.0",
        description="Host address to bind the server"
    )
    port: int = Field(
        default=8080,
        description="Port number for the web server"
    )
    
    # AI Provider Settings
    default_ai_provider: str = Field(
        default="gemini",
        description="Default LLM provider: gemini or openai"
    )
    max_tokens: int = Field(
        default=4096,
        description="Maximum tokens per AI response"
    )
    temperature: float = Field(
        default=0.7,
        description="Temperature for AI response generation (0.0-2.0)"
    )
    
    # Context Management
    max_conversation_history: int = Field(
        default=50,
        description="Maximum number of messages to keep in active context"
    )
    enable_auto_summary: bool = Field(
        default=True,
        description="Automatically summarize old conversations to manage context window"
    )
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment.lower() == "development"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment.lower() == "production"


# Global settings instance
# This is loaded once when the module is imported
settings = Settings()
