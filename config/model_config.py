"""
Model configurations for all supported LLM providers.
This file defines the available models for each provider.
"""

import os
from typing import Optional

# Google Gemini Models
# Based on the output from check_models.py (November 2025)
GEMINI_MODELS = {
    # Recommended Production Models
    "gemini-2.5-pro": {
        "display_name": "Gemini 2.5 Pro (Latest)",
        "model_id": "models/gemini-2.5-pro",
        "description": "Most capable model, best for complex reasoning"
    },
    "gemini-2.5-flash": {
        "display_name": "Gemini 2.5 Flash (Fast)",
        "model_id": "models/gemini-2.5-flash",
        "description": "Fast and efficient, good for most tasks"
    },
    "gemini-2.0-flash": {
        "display_name": "Gemini 2.0 Flash",
        "model_id": "models/gemini-2.0-flash",
        "description": "Stable 2.0 flash model"
    },
    "gemini-pro-latest": {
        "display_name": "Gemini Pro (Auto-updated)",
        "model_id": "models/gemini-pro-latest",
        "description": "Always uses latest pro model"
    },
    "gemini-flash-latest": {
        "display_name": "Gemini Flash (Auto-updated)",
        "model_id": "models/gemini-flash-latest",
        "description": "Always uses latest flash model"
    },
    
    # Experimental/Preview Models
    "gemini-2.0-pro-exp": {
        "display_name": "Gemini 2.0 Pro Experimental",
        "model_id": "models/gemini-2.0-pro-exp",
        "description": "Experimental pro model with latest features"
    },
    "gemini-2.0-flash-thinking": {
        "display_name": "Gemini 2.0 Flash Thinking",
        "model_id": "models/gemini-2.0-flash-thinking-exp",
        "description": "Includes chain-of-thought reasoning"
    },
    
    # Lightweight Models
    "gemini-2.5-flash-lite": {
        "display_name": "Gemini 2.5 Flash Lite",
        "model_id": "models/gemini-2.5-flash-lite",
        "description": "Lightweight, cost-effective option"
    },
    "gemini-2.0-flash-lite": {
        "display_name": "Gemini 2.0 Flash Lite",
        "model_id": "models/gemini-2.0-flash-lite",
        "description": "Lightweight 2.0 model"
    },
}

# OpenAI Models
OPENAI_MODELS = {
    # GPT-4 Models
    "gpt-4o": {
        "display_name": "GPT-4o (Omni)",
        "model_id": "gpt-4o",
        "description": "Multimodal flagship model, most capable"
    },
    "gpt-4o-mini": {
        "display_name": "GPT-4o Mini",
        "model_id": "gpt-4o-mini",
        "description": "Affordable and intelligent small model"
    },
    "gpt-4-turbo": {
        "display_name": "GPT-4 Turbo",
        "model_id": "gpt-4-turbo",
        "description": "Previous generation flagship"
    },
    "gpt-4": {
        "display_name": "GPT-4",
        "model_id": "gpt-4",
        "description": "Original GPT-4"
    },
    
    # GPT-3.5 Models
    "gpt-3.5-turbo": {
        "display_name": "GPT-3.5 Turbo",
        "model_id": "gpt-3.5-turbo",
        "description": "Fast and cost-effective"
    },
}

# Provider display names
PROVIDERS = {
    "gemini": "Google Gemini",
    "openai": "OpenAI"
}

def get_model_display_name(provider: str, model_key: str) -> str:
    """
    Get the display name for a model.
    
    Args:
        provider: Provider key ("gemini" or "openai")
        model_key: Model key from the config
        
    Returns:
        Display name for the model
    """
    if provider == "gemini":
        return GEMINI_MODELS.get(model_key, {}).get("display_name", model_key)
    elif provider == "openai":
        return OPENAI_MODELS.get(model_key, {}).get("display_name", model_key)
    return model_key

def get_model_id(provider: str, model_key: str) -> str:
    """
    Get the actual model ID to send to the API.
    
    Args:
        provider: Provider key ("gemini" or "openai")
        model_key: Model key from the config
        
    Returns:
        Model ID for API calls
    """
    if provider == "gemini":
        return GEMINI_MODELS.get(model_key, {}).get("model_id", model_key)
    elif provider == "openai":
        return OPENAI_MODELS.get(model_key, {}).get("model_id", model_key)
    return model_key

def get_client(provider: str, variant: str, api_key: Optional[str] = None):
    """
    Factory function to create an LLM client based on provider and variant.
    
    Args:
        provider: Provider key ("gemini" or "openai")
        variant: Model variant key from the config
        api_key: Optional API key (if None, will read from environment)
        
    Returns:
        Instance of the appropriate LLM client
        
    Raises:
        ValueError: If provider is unsupported or API key is missing
    """
    # Import clients here to avoid circular imports
    from clients import GoogleGeminiClient, OpenAIClient
    
    if provider == "gemini":
        # Get API key from parameter or environment
        key = api_key or os.getenv("GOOGLE_API_KEY")
        if not key:
            raise ValueError("GOOGLE_API_KEY environment variable not set")
        
        # Get the actual model ID from config
        model_id = get_model_id(provider, variant)
        return GoogleGeminiClient(api_key=key, model_id=model_id)
        
    elif provider == "openai":
        # Get API key from parameter or environment
        key = api_key or os.getenv("OPENAI_API_KEY")
        if not key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        # Get the actual model ID from config
        model_id = get_model_id(provider, variant)
        return OpenAIClient(api_key=key, model_id=model_id)
        
    else:
        raise ValueError(f"Unsupported provider: {provider}")
