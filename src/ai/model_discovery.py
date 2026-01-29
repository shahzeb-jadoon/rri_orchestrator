"""
Dynamic AI Model Discovery System.

This module automatically discovers available models from AI provider APIs,
caches results, and provides fallback mechanisms. Eliminates the need for
manual model list maintenance.
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlencode

from src.config import settings
from src.utils.logger import logger

# Cache configuration
CACHE_FILE = Path(".nicegui/model_cache.json")
CACHE_TTL_HOURS = 24  # Refresh cache every 24 hours
DISCOVERY_TIMEOUT = 10  # Timeout for API calls in seconds

# Fallback static models (used if API discovery fails)
FALLBACK_MODELS: Dict[str, List[str]] = {
    "openai": [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "gpt-3.5-turbo",
    ],
    "gemini": [
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-flash-latest",
        "gemini-pro-latest",
    ],
    "anthropic": [
        "claude-3-5-sonnet-20241022",
        "claude-3-opus-20240229",
        "claude-3-haiku-20240307",
    ],
}

# Model aliases and deprecation mappings
MODEL_MIGRATIONS: Dict[str, str] = {
    "gemini-pro": "gemini-2.5-flash",
    "gemini-1.5-pro": "gemini-2.5-pro",
    "gemini-1.5-flash": "gemini-2.5-flash",
    "gpt-4": "gpt-4o",
}


class ModelCache:
    """Manages model cache with TTL."""
    
    def __init__(self):
        self.cache: Dict[str, List[str]] = {}
        self.last_updated: Optional[datetime] = None
        self.discovery_errors: Dict[str, str] = {}
        
    def is_expired(self) -> bool:
        """Check if cache has expired."""
        if not self.last_updated:
            return True
        return datetime.now() - self.last_updated > timedelta(hours=CACHE_TTL_HOURS)
    
    def load_from_disk(self) -> bool:
        """Load cache from disk if available and not expired."""
        try:
            if not CACHE_FILE.exists():
                return False
                
            with open(CACHE_FILE, 'r') as f:
                data = json.load(f)
            
            self.cache = data.get('models', {})
            timestamp = data.get('timestamp')
            
            if timestamp:
                self.last_updated = datetime.fromisoformat(timestamp)
                if not self.is_expired():
                    logger.info(f"Loaded model cache from disk (age: {datetime.now() - self.last_updated})")
                    return True
            
            return False
            
        except Exception as e:
            logger.warning(f"Failed to load model cache from disk: {e}")
            return False
    
    def save_to_disk(self):
        """Save cache to disk."""
        try:
            CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                'models': self.cache,
                'timestamp': self.last_updated.isoformat() if self.last_updated else None,
                'errors': self.discovery_errors
            }
            
            with open(CACHE_FILE, 'w') as f:
                json.dump(data, f, indent=2)
                
            logger.debug("Saved model cache to disk")
            
        except Exception as e:
            logger.warning(f"Failed to save model cache to disk: {e}")
    
    def update(self, provider: str, models: List[str]):
        """Update cache for a provider."""
        self.cache[provider] = models
        self.last_updated = datetime.now()
        self.discovery_errors.pop(provider, None)  # Clear any previous errors
        self.save_to_disk()
    
    def set_error(self, provider: str, error: str):
        """Record discovery error for a provider."""
        self.discovery_errors[provider] = error
        logger.warning(f"Model discovery failed for {provider}: {error}")
    
    def get(self, provider: str) -> List[str]:
        """Get models for a provider, with fallback."""
        if provider in self.cache and self.cache[provider]:
            return self.cache[provider]
        
        # Use fallback if discovery failed or cache is empty
        logger.info(f"Using fallback models for {provider}")
        return FALLBACK_MODELS.get(provider, [])


# Global cache instance
_cache = ModelCache()


async def discover_gemini_models() -> List[str]:
    """
    Discover available Gemini models via API.
    
    Returns:
        List of model names
    """
    if not settings.gemini_api_key:
        raise ValueError("Gemini API key not configured")
    
    try:
        # Import httpx dynamically (it's available via litellm)
        import httpx
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={settings.gemini_api_key}"
        
        async with httpx.AsyncClient(timeout=DISCOVERY_TIMEOUT) as client:
            response = await client.get(url)
            response.raise_for_status()
            
            data = response.json()
            models = []
            
            for model in data.get('models', []):
                # Only include models that support text generation
                if 'generateContent' in model.get('supportedGenerationMethods', []):
                    name = model['name'].replace('models/', '')
                    models.append(name)
            
            logger.info(f"Discovered {len(models)} Gemini models")
            return sorted(models)
            
    except Exception as e:
        logger.error(f"Failed to discover Gemini models: {e}")
        raise


async def discover_openai_models() -> List[str]:
    """
    Discover available OpenAI models via API.
    
    Returns:
        List of model names
    """
    if not settings.openai_api_key:
        raise ValueError("OpenAI API key not configured")
    
    try:
        import httpx
        
        url = "https://api.openai.com/v1/models"
        headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
        
        async with httpx.AsyncClient(timeout=DISCOVERY_TIMEOUT) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            
            # Filter for chat models (gpt-* models)
            models = [
                model['id'] 
                for model in data.get('data', [])
                if model['id'].startswith(('gpt-', 'o1-'))
            ]
            
            logger.info(f"Discovered {len(models)} OpenAI models")
            return sorted(models)
            
    except Exception as e:
        logger.error(f"Failed to discover OpenAI models: {e}")
        raise


async def discover_anthropic_models() -> List[str]:
    """
    Discover available Anthropic models.
    
    Note: Anthropic doesn't have a public models API endpoint,
    so we use a curated list based on their documentation.
    
    Returns:
        List of model names
    """
    # Anthropic doesn't expose a models API, use documented models
    models = [
        "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku-20241022",
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229",
        "claude-3-haiku-20240307",
    ]
    
    logger.info(f"Using documented Anthropic models ({len(models)} models)")
    return models


async def discover_models_for_provider(provider: str) -> List[str]:
    """
    Discover available models for a specific provider.
    
    Args:
        provider: Provider name (openai, gemini, anthropic)
        
    Returns:
        List of model names
        
    Raises:
        ValueError: If provider is unknown or API key not configured
    """
    try:
        if provider == "gemini":
            return await discover_gemini_models()
        elif provider == "openai":
            return await discover_openai_models()
        elif provider == "anthropic":
            return await discover_anthropic_models()
        else:
            raise ValueError(f"Unknown provider: {provider}")
            
    except Exception as e:
        _cache.set_error(provider, str(e))
        raise


async def refresh_model_cache(force: bool = False) -> Dict[str, List[str]]:
    """
    Refresh the model cache by discovering models from all providers.
    
    Args:
        force: Force refresh even if cache is not expired
        
    Returns:
        Dictionary of provider -> models
    """
    if not force and not _cache.is_expired():
        logger.debug("Model cache is still fresh, skipping refresh")
        return _cache.cache
    
    logger.info("Refreshing model cache from provider APIs...")
    
    providers = ["gemini", "openai", "anthropic"]
    results = {}
    
    # Discover models for each provider concurrently
    tasks = []
    for provider in providers:
        # Skip if API key not configured
        if provider == "gemini" and not settings.gemini_api_key:
            logger.debug(f"Skipping {provider} - no API key")
            continue
        if provider == "openai" and not settings.openai_api_key:
            logger.debug(f"Skipping {provider} - no API key")
            continue
        
        tasks.append((provider, discover_models_for_provider(provider)))
    
    # Gather results with timeout
    for provider, task in tasks:
        try:
            models = await asyncio.wait_for(task, timeout=DISCOVERY_TIMEOUT)
            _cache.update(provider, models)
            results[provider] = models
            
        except asyncio.TimeoutError:
            error = f"Discovery timeout after {DISCOVERY_TIMEOUT}s"
            _cache.set_error(provider, error)
            results[provider] = FALLBACK_MODELS.get(provider, [])
            
        except Exception as e:
            _cache.set_error(provider, str(e))
            results[provider] = FALLBACK_MODELS.get(provider, [])
    
    logger.info(f"Model cache refresh complete: {sum(len(m) for m in results.values())} models from {len(results)} providers")
    return results


async def initialize_model_cache():
    """
    Initialize model cache on application startup.
    
    Loads from disk if available, otherwise performs discovery.
    """
    logger.info("Initializing model cache...")
    
    # Try to load from disk first
    if _cache.load_from_disk() and not _cache.is_expired():
        logger.info("Using cached models from disk")
        return
    
    # Otherwise, refresh from APIs
    try:
        await refresh_model_cache(force=True)
    except Exception as e:
        logger.error(f"Failed to initialize model cache: {e}")
        logger.info("Using fallback static model lists")


def get_available_models(provider: str) -> List[str]:
    """
    Get available models for a provider from cache.
    
    Args:
        provider: Provider name
        
    Returns:
        List of model names
    """
    return _cache.get(provider)


def get_model_suggestion(provider: str, deprecated_model: str) -> Optional[str]:
    """
    Get suggested replacement for a deprecated model.
    
    Args:
        provider: Provider name
        deprecated_model: Deprecated model name
        
    Returns:
        Suggested model name or None
    """
    # Check migration mappings first
    if deprecated_model in MODEL_MIGRATIONS:
        suggestion = MODEL_MIGRATIONS[deprecated_model]
        logger.info(f"Suggesting migration: {deprecated_model} -> {suggestion}")
        return suggestion
    
    # Otherwise suggest first available model
    available = get_available_models(provider)
    if available:
        return available[0]
    
    return None


async def handle_model_not_found(
    provider: str, 
    model: str, 
    error: Exception
) -> Tuple[bool, Optional[str]]:
    """
    Handle 404 model not found errors by refreshing cache and suggesting alternatives.
    
    Args:
        provider: Provider name
        model: Model that wasn't found
        error: The exception that was raised
        
    Returns:
        Tuple of (should_retry, suggested_model)
    """
    logger.warning(f"Model not found: {provider}/{model}")
    
    # Refresh cache for this provider
    try:
        models = await discover_models_for_provider(provider)
        _cache.update(provider, models)
        
        # Check if model is now available
        if model in models:
            logger.info(f"Model {model} found after cache refresh, retrying...")
            return (True, model)
        
        # Otherwise suggest alternative
        suggestion = get_model_suggestion(provider, model)
        if suggestion:
            logger.warning(f"Model {model} is deprecated, suggesting: {suggestion}")
            return (False, suggestion)
        
    except Exception as e:
        logger.error(f"Failed to refresh cache after model not found: {e}")
    
    return (False, None)


def get_cache_status() -> Dict:
    """
    Get current cache status for debugging/monitoring.
    
    Returns:
        Dictionary with cache information
    """
    return {
        "last_updated": _cache.last_updated.isoformat() if _cache.last_updated else None,
        "is_expired": _cache.is_expired(),
        "providers": list(_cache.cache.keys()),
        "total_models": sum(len(models) for models in _cache.cache.values()),
        "errors": _cache.discovery_errors,
        "cache_file": str(CACHE_FILE),
    }
