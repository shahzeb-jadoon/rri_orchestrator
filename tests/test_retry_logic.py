"""
Tests for retry logic and error handling
"""

import pytest
from unittest.mock import AsyncMock, patch
from litellm import RateLimitError, APIError
from src.ai.llm_service import retry_with_backoff


@pytest.mark.asyncio
async def test_retry_success_on_first_attempt():
    """Test that function succeeds on first attempt"""
    mock_func = AsyncMock(return_value="success")
    
    result = await retry_with_backoff(mock_func, max_retries=3)
    
    assert result == "success"
    assert mock_func.call_count == 1


@pytest.mark.asyncio
async def test_retry_success_after_rate_limit():
    """Test that function retries and succeeds after rate limit"""
    mock_func = AsyncMock(side_effect=[
        RateLimitError("Rate limited", llm_provider="openai", model="gpt-4"),
        "success"
    ])
    
    result = await retry_with_backoff(mock_func, max_retries=3, base_delay=0.01)
    
    assert result == "success"
    assert mock_func.call_count == 2


@pytest.mark.asyncio
async def test_retry_fails_after_max_attempts():
    """Test that function fails after max retries"""
    mock_func = AsyncMock(side_effect=RateLimitError("Always rate limited", llm_provider="openai", model="gpt-4"))
    
    with pytest.raises(RateLimitError):
        await retry_with_backoff(mock_func, max_retries=3, base_delay=0.01)
    
    assert mock_func.call_count == 3


@pytest.mark.asyncio
async def test_retry_api_error():
    """Test retry on API errors"""
    mock_func = AsyncMock(side_effect=[
        APIError(status_code=500, message="Network error", llm_provider="openai", model="gpt-4"),
        "success"
    ])
    
    result = await retry_with_backoff(mock_func, max_retries=3, base_delay=0.01)
    
    assert result == "success"
    assert mock_func.call_count == 2


@pytest.mark.asyncio
async def test_no_retry_on_validation_error():
    """Test that validation errors don't retry"""
    mock_func = AsyncMock(side_effect=ValueError("Invalid input"))
    
    with pytest.raises(ValueError):
        await retry_with_backoff(mock_func, max_retries=3)
    
    # Should fail immediately, no retries
    assert mock_func.call_count == 1
