"""
LLM Service for AI Model Integration

This module uses LiteLLM to interact with AI providers (OpenAI, Gemini, etc.).
LiteLLM provides a unified interface, allowing easy switching between providers
including local models via Ollama in the future.
"""

import asyncio
import time
from typing import Dict, List, Optional

from litellm import acompletion, RateLimitError, APIError, Timeout, NotFoundError
from src.config import settings
from src.database.models import RobotProfile
from src.ai.model_config import calculate_cost
from src.ai.model_discovery import handle_model_not_found, get_model_suggestion
from src.utils.logger import logger


# Retry configuration
MAX_RETRIES = 3
BASE_DELAY = 1  # seconds


async def retry_with_backoff(func, *args, max_retries=MAX_RETRIES, robot_profile=None, **kwargs):
    """
    Retry a function with exponential backoff.
    
    Args:
        func: Async function to retry
        max_retries: Maximum number of retry attempts
        robot_profile: Optional robot profile for model migration suggestions
        *args, **kwargs: Arguments to pass to func
        
    Returns:
        Result from func
        
    Raises:
        Last exception if all retries fail
    """
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            return await func(*args, **kwargs)
            
        except NotFoundError as e:
            # Model not found (404) - try to refresh cache and suggest alternative
            last_exception = e
            
            if robot_profile and attempt == 0:  # Only try once
                try:
                    should_retry, suggested_model = await handle_model_not_found(
                        robot_profile.ai_provider,
                        robot_profile.model_name,
                        e
                    )
                    
                    if suggested_model and suggested_model != robot_profile.model_name:
                        error_msg = (
                            f"Model '{robot_profile.model_name}' is not available. "
                            f"Suggested alternative: '{suggested_model}'. "
                            f"Please update your robot profile to use the new model."
                        )
                        logger.error(error_msg)
                        # Re-raise with helpful message
                        raise ValueError(error_msg) from e
                        
                except ValueError:
                    raise  # Re-raise the helpful error message
                except Exception as refresh_error:
                    logger.error(f"Failed to handle model not found: {refresh_error}")
            
            # If we can't recover, raise the original error
            logger.error(f"Model not found and no alternative available: {e}")
            raise
            
        except RateLimitError as e:
            last_exception = e
            if attempt == max_retries - 1:
                logger.error(f"Rate limit after {max_retries} attempts: {e}")
                raise
            
            # Exponential backoff: 1s, 2s, 4s
            wait_time = BASE_DELAY * (2 ** attempt)
            logger.warning(f"Rate limit hit, retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})")
            await asyncio.sleep(wait_time)
            
        except (APIError, Timeout) as e:
            last_exception = e
            if attempt == max_retries - 1:
                logger.error(f"API error after {max_retries} attempts: {e}")
                raise
            
            # Quick retry for network/API errors
            wait_time = 1
            logger.warning(f"API error, retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries}): {e}")
            await asyncio.sleep(wait_time)
            
        except Exception as e:
            # Don't retry on other exceptions (validation errors, etc.)
            logger.error(f"Non-retryable error: {e}")
            raise
    
    # Should never reach here, but just in case
    raise last_exception


def get_api_key_for_provider(provider: str) -> str:
    """
    Get the API key for a specific AI provider.
    
    Args:
        provider: Provider name (openai, gemini, anthropic)
        
    Returns:
        API key string
        
    Raises:
        ValueError: If provider is unknown or API key not configured
    """
    provider = provider.lower()
    
    if provider == "openai":
        if not settings.openai_api_key:
            raise ValueError("OpenAI API key not configured in .env")
        return settings.openai_api_key
    
    elif provider == "gemini":
        if not settings.gemini_api_key:
            raise ValueError("Gemini API key not configured in .env")
        return settings.gemini_api_key
    
    # Future providers
    elif provider == "anthropic":
        # anthropic_api_key would need to be added to settings
        raise ValueError("Anthropic support not yet implemented")
    
    else:
        raise ValueError(f"Unknown AI provider: {provider}")


async def generate_robot_response(
    robot_profile: RobotProfile,
    conversation_history: List[Dict[str, str]],
    max_tokens: Optional[int] = None
) -> Dict:
    """
    Generate a response from a robot using its configured AI provider.
    
    Args:
        robot_profile: The robot profile with AI configuration
        conversation_history: List of messages in OpenAI format
            [{"role": "user", "content": "Hello"}, ...]
        max_tokens: Override max tokens if needed
        
    Returns:
        dict with:
            - content: The AI's response text
            - model_used: Model that generated the response
            - tokens_used: Total tokens consumed
            - input_tokens: Input token count (prompt/context)
            - output_tokens: Output token count (completion)
            - cost_usd: Estimated cost in USD
            - response_time_ms: Time taken to generate response
            - robot_provider: Provider used (for cost breakdown)
            
    Raises:
        ValueError: If robot profile is invalid
        Exception: If API call fails
    """
    if not robot_profile.model_name:
        raise ValueError(
            f"Robot profile '{robot_profile.name}' has no model_name configured"
        )
    
    # Build model string for LiteLLM
    # Format: "provider/model" e.g. "openai/gpt-4o" or "gemini/gemini-2.0-flash"
    model = f"{robot_profile.ai_provider}/{robot_profile.model_name}"
    
    # Get API key
    try:
        api_key = get_api_key_for_provider(robot_profile.ai_provider)
    except ValueError as e:
        logger.error(f"API key error for {robot_profile.ai_provider}: {e}")
        raise
    
    # Prepare messages with system prompt
    messages = [
        {"role": "system", "content": robot_profile.system_prompt}
    ] + conversation_history
    
    logger.info(
        f"Generating response for robot '{robot_profile.name}' "
        f"using {model} (temp={robot_profile.default_temperature})"
    )
    
    # Define the actual API call to be retried
    async def make_llm_call():
        return await acompletion(
            model=model,
            messages=messages,
            temperature=robot_profile.default_temperature,
            max_tokens=max_tokens or settings.max_tokens,
            api_key=api_key
        )

    # Call LiteLLM with retry logic
    start_time = time.time()
    try:
        response = await retry_with_backoff(make_llm_call, robot_profile=robot_profile)
    except Exception as e:
        logger.error(f"LLM call failed after retries for {model}: {e}")
        raise
    
    elapsed_ms = int((time.time() - start_time) * 1000)
    
    # Extract response data with error handling
    if not response.choices or len(response.choices) == 0:
        logger.error(f"Empty response from {model}: {response}")
        raise Exception(f"AI model {model} returned empty response. This may be due to content filtering or API issues.")
    
    content = response.choices[0].message.content
    
    if not content:
        logger.error(f"Empty content from {model}")
        raise Exception(f"AI model {model} returned empty message content.")
    
    input_tokens = response.usage.prompt_tokens
    output_tokens = response.usage.completion_tokens
    total_tokens = response.usage.total_tokens
    
    # Calculate cost using our fallback method
    # TODO: Switch to litellm.completion_cost() for automatic pricing updates
    cost = calculate_cost(
        robot_profile.ai_provider,
        robot_profile.model_name,
        input_tokens,
        output_tokens
    )
    
    logger.info(
        f"Response generated: {total_tokens} tokens "
        f"(in: {input_tokens}, out: {output_tokens}), "
        f"${cost:.4f}, {elapsed_ms}ms"
    )
    
    return {
        "content": content,
        "model_used": robot_profile.model_name,
        "tokens_used": total_tokens,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": cost,
        "response_time_ms": elapsed_ms,
        "robot_provider": robot_profile.ai_provider
    }


async def test_api_connection(provider: str, model: str) -> Dict:
    """
    Test API connection for a provider/model combination.
    
    Args:
        provider: Provider name
        model: Model name
        
    Returns:
        dict with test results
    """
    try:
        api_key = get_api_key_for_provider(provider)
        
        response = await acompletion(
            model=f"{provider}/{model}",
            messages=[{"role": "user", "content": "Test"}],
            max_tokens=5,
            api_key=api_key
        )
        
        return {
            "success": True,
            "message": "Connection successful",
            "model": model
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e),
            "model": model
        }
