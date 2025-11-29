"""
AI Model Configuration.

This module defines available AI models for each provider and their
default configurations. Used for UI dropdowns and validation.
"""

from typing import Dict, List

# Available models per provider
AVAILABLE_MODELS: Dict[str, List[str]] = {
    "openai": [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "gpt-4",
        "gpt-3.5-turbo",
    ],
    "gemini": [
        "gemini-2.0-flash",
        "gemini-1.5-pro",
        "gemini-1.5-flash",
        "gemini-pro",
    ],
    "anthropic": [
        "claude-3-5-sonnet-20241022",
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229",
        "claude-3-haiku-20240307",
    ],
}

# Provider display names
PROVIDER_NAMES: Dict[str, str] = {
    "openai": "OpenAI",
    "gemini": "Google Gemini",
    "anthropic": "Anthropic",
}

# Default models for each provider (recommended)
DEFAULT_MODELS: Dict[str, str] = {
    "openai": "gpt-4o",
    "gemini": "gemini-2.0-flash",
    "anthropic": "claude-3-5-sonnet-20241022",
}

# Cost per 1K tokens (USD) - approximate as of Nov 2024
# Format: {provider/model: {"input": price, "output": price}}
TOKEN_PRICING: Dict[str, Dict[str, float]] = {
    # OpenAI
    "openai/gpt-4o": {"input": 0.0025, "output": 0.01},
    "openai/gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "openai/gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "openai/gpt-4": {"input": 0.03, "output": 0.06},
    "openai/gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    
    # Google Gemini (Free tier exists, but paid pricing shown)
    "gemini/gemini-2.0-flash": {"input": 0.0, "output": 0.0},  # Free tier
    "gemini/gemini-1.5-pro": {"input": 0.00125, "output": 0.005},
    "gemini/gemini-1.5-flash": {"input": 0.000075, "output": 0.0003},
    "gemini/gemini-pro": {"input": 0.0005, "output": 0.0015},
    
    # Anthropic
    "anthropic/claude-3-5-sonnet-20241022": {"input": 0.003, "output": 0.015},
    "anthropic/claude-3-opus-20240229": {"input": 0.015, "output": 0.075},
    "anthropic/claude-3-sonnet-20240229": {"input": 0.003, "output": 0.015},
    "anthropic/claude-3-haiku-20240307": {"input": 0.00025, "output": 0.00125},
}


def get_available_models(provider: str) -> List[str]:
    """
    Get list of available models for a provider.
    
    Args:
        provider: Provider name (openai, gemini, anthropic)
        
    Returns:
        List of model names
    """
    return AVAILABLE_MODELS.get(provider, [])


def get_default_model(provider: str) -> str:
    """
    Get recommended default model for a provider.
    
    Args:
        provider: Provider name
        
    Returns:
        Default model name
    """
    return DEFAULT_MODELS.get(provider, "")


def calculate_cost(provider: str, model: str, input_tokens: int, output_tokens: int) -> float:
    """
    Calculate cost for API call.
    
    Args:
        provider: Provider name
        model: Model name
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        
    Returns:
        Cost in USD
    """
    model_key = f"{provider}/{model}"
    pricing = TOKEN_PRICING.get(model_key)
    
    if not pricing:
        return 0.0
    
    input_cost = (input_tokens / 1000) * pricing["input"]
    output_cost = (output_tokens / 1000) * pricing["output"]
    
    return round(input_cost + output_cost, 6)


def validate_provider_model(provider: str, model: str) -> bool:
    """
    Check if a provider/model combination is valid.
    
    Args:
        provider: Provider name
        model: Model name
        
    Returns:
        True if valid combination
    """
    return model in AVAILABLE_MODELS.get(provider, [])
