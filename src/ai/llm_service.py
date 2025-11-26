"""
LiteLLM Service Wrapper.

This module provides a universal interface for calling different AI providers
through LiteLLM, with support for OpenAI, Google Gemini, Anthropic, and more.
"""

import time
from typing import Dict, List, Optional

from litellm import acompletion
from src.config import settings
from src.database.models import RobotProfile
from src.ai.model_config import calculate_cost
from src.utils.logger import logger


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
    
    # Call LiteLLM
    start_time = time.time()
    try:
        response = await acompletion(
            model=model,
            messages=messages,
            temperature=robot_profile.default_temperature,
            max_tokens=max_tokens or settings.max_tokens,
            api_key=api_key
        )
    except Exception as e:
        logger.error(f"AI API call failed for {model}: {e}")
        raise
    
    elapsed_ms = int((time.time() - start_time) * 1000)
    
    # Extract response data
    content = response.choices[0].message.content
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
