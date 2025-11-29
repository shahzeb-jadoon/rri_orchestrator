"""
AI integration module for RRI Orchestrator.

This module handles all AI provider interactions through LiteLLM.
"""

from src.ai.llm_service import generate_robot_response, test_api_connection
from src.ai.model_config import get_available_models, get_default_model

__all__ = [
    "generate_robot_response",
    "test_api_connection",
    "get_available_models",
    "get_default_model",
]
