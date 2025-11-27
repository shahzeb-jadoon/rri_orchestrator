"""
Token counting utilities for context window management.

Uses tiktoken to accurately count tokens for different AI models.
"""

import tiktoken
from typing import List, Dict
from src.utils.logger import logger


def get_encoding_for_model(model_name: str) -> tiktoken.Encoding:
    """Get the appropriate encoding for a model."""
    # Map model names to encodings
    encoding_map = {
        'gpt-4o': 'o200k_base',
        'gpt-4o-mini': 'o200k_base',
        'gpt-4': 'cl100k_base',
        'gpt-4-turbo': 'cl100k_base',
        'gpt-3.5-turbo': 'cl100k_base',
    }
    
    # Gemini uses similar encoding to GPT-4
    if model_name.startswith('gemini'):
        encoding_name = 'cl100k_base'
    else:
        encoding_name = encoding_map.get(model_name, 'cl100k_base')
    
    return tiktoken.get_encoding(encoding_name)


def count_tokens(messages: List[Dict[str, str]], model_name: str) -> int:
    """
    Count tokens in a conversation history.
    
    Args:
        messages: List of message dicts with 'role' and 'content'
        model_name: Model name to get appropriate encoding
        
    Returns:
        Total token count
    """
    encoding = get_encoding_for_model(model_name)
    
    total_tokens = 0
    
    for message in messages:
        # Count tokens in content
        total_tokens += len(encoding.encode(message.get('content', '')))
        
        # Add overhead for message formatting (role, etc.)
        total_tokens += 4  # Approximate overhead per message
    
    # Add overhead for conversation wrapping
    total_tokens += 3
    
    return total_tokens


def get_model_token_limit(model_name: str) -> int:
    """Get the token limit for a specific model."""
    limits = {
        'gpt-4o': 128000,
        'gpt-4o-mini': 128000,
        'gpt-4': 8192,
        'gpt-4-turbo': 128000,
        'gpt-3.5-turbo': 16385,
        'gemini-2.0-flash': 1048576,
        'gemini-1.5-pro': 2097152,
        'gemini-1.5-flash': 1048576,
    }
    
    # Default to conservative limit if unknown
    return limits.get(model_name, 128000)
