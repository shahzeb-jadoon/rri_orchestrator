"""
AI integration module for RRI Orchestrator.

This module handles all AI provider interactions through LiteLLM.
Includes dynamic model discovery that automatically fetches available models.
"""

from src.ai.llm_service import generate_robot_response, test_api_connection
from src.ai.model_config import get_available_models, get_default_model
from src.ai.model_discovery import (
    initialize_model_cache,
    refresh_model_cache,
    get_cache_status,
    get_model_suggestion,
)

__all__ = [
    "generate_robot_response",
    "test_api_connection",
    "get_available_models",
    "get_default_model",
    "initialize_model_cache",
    "refresh_model_cache",
    "get_cache_status",
    "get_model_suggestion",
]
