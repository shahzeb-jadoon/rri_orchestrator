"""
Live integration tests with real AI APIs

Run with: pytest -v -m live tests/test_live_integration.py

These tests make actual API calls and incur costs.
Only run before releases or when validating API integration.
"""

import pytest
import os
from src.database.models import RobotProfile
from src.ai.llm_service import generate_robot_response


@pytest.mark.live
@pytest.mark.asyncio
async def test_openai_integration():
    """Test actual OpenAI API call"""
    if not os.getenv('OPENAI_API_KEY'):
        pytest.skip("OPENAI_API_KEY not set")
    
    # Create mock robot profile
    robot = RobotProfile(
        name="Test GPT",
        ai_provider="openai",
        model_name="gpt-4o-mini",
        system_prompt="You are a helpful assistant. Respond in one sentence.",
        default_temperature=0.7
    )
    
    conversation_history = [
        {"role": "user", "content": "Say 'test successful' in exactly two words."}
    ]
    
    response = await generate_robot_response(robot, conversation_history)
    
    assert response is not None
    assert isinstance(response, str)
    assert len(response) > 0
    print(f"OpenAI response: {response}")


@pytest.mark.live
@pytest.mark.asyncio
async def test_gemini_integration():
    """Test actual Gemini API call"""
    if not os.getenv('GEMINI_API_KEY'):
        pytest.skip("GEMINI_API_KEY not set")
    
    # Create mock robot profile
    robot = RobotProfile(
        name="Test Gemini",
        ai_provider="gemini",
        model_name="gemini/gemini-2.0-flash-exp",
        system_prompt="You are a helpful assistant. Respond in one sentence.",
        default_temperature=0.7
    )
    
    conversation_history = [
        {"role": "user", "content": "Say 'test successful' in exactly two words."}
    ]
    
    response = await generate_robot_response(robot, conversation_history)
    
    assert response is not None
    assert isinstance(response, str)
    assert len(response) > 0
    print(f"Gemini response: {response}")


@pytest.mark.live
@pytest.mark.asyncio
async def test_conversation_with_context():
    """Test multi-turn conversation with context"""
    if not os.getenv('OPENAI_API_KEY'):
        pytest.skip("OPENAI_API_KEY not set")
    
    robot = RobotProfile(
        name="Test Contextual",
        ai_provider="openai",
        model_name="gpt-4o-mini",
        system_prompt="You are a helpful assistant.",
        default_temperature=0.7
    )
    
    # Multi-turn conversation
    history = [
        {"role": "user", "content": "My favorite color is blue."},
        {"role": "assistant", "content": "That's nice! Blue is a calming color."},
        {"role": "user", "content": "What's my favorite color?"}
    ]
    
    response = await generate_robot_response(robot, history)
    
    assert response is not None
    assert "blue" in response.lower()
    print(f"Context test response: {response}")
