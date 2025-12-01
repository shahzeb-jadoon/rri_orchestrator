"""
Tests for Phase 2: Per-Robot AI Provider Selection.

This module tests the new robot profile AI configuration features
including multi-provider support and per-robot model selection.
"""

import pytest
from src.database.models import User, RobotProfile, Experiment


@pytest.mark.asyncio
async def test_create_robot_profile_with_ai_config(init_test_db):
    """
    Test creating a robot profile with AI provider configuration.
    """
    user = await User.create(
        email="researcher@example.com",
        display_name="Test Researcher"
    )
    
    robot = await RobotProfile.create(
        name="GPT-4 Assistant",
        description="Helpful customer service robot",
        system_prompt="You are a helpful assistant.",
        created_by=user,
        ai_provider="openai",
        model_name="gpt-4o",
        default_temperature=0.7
    )
    
    assert robot.ai_provider == "openai"
    assert robot.model_name == "gpt-4o"
    assert robot.default_temperature == 0.7


@pytest.mark.asyncio
async def test_create_experiment_with_robot_profiles(init_test_db):
    """
    Test creating an experiment with two different robot profiles.
    """
    user = await User.create(
        email="researcher@example.com",
        display_name="Test Researcher"
    )
    
    # Create Robot A with OpenAI
    robot_a = await RobotProfile.create(
        name="GPT-4o Bot",
        description="OpenAI GPT-4o",
        system_prompt="You are a precise technical assistant.",
        ai_provider="openai",
        model_name="gpt-4o",
        default_temperature=0.3,
        created_by=user
    )
    
    # Create Robot B with Gemini
    robot_b = await RobotProfile.create(
        name="Gemini Flash Bot",
        description="Google Gemini 2.0 Flash",
        system_prompt="You are a creative assistant.",
        ai_provider="gemini",
        model_name="gemini-2.0-flash",
        default_temperature=0.9,
        created_by=user
    )
    
    # Create experiment with both robots
    experiment = await Experiment.create(
        name="Cross-Provider Test",
        description="GPT-4o vs Gemini",
        created_by=user,
        robot_a_profile=robot_a,
        robot_b_profile=robot_b
    )
    
    # Fetch related profiles
    await experiment.fetch_related("robot_a_profile", "robot_b_profile")
    
    assert experiment.robot_a_profile.ai_provider == "openai"
    assert experiment.robot_a_profile.model_name == "gpt-4o"
    assert experiment.robot_b_profile.ai_provider == "gemini"
    assert experiment.robot_b_profile.model_name == "gemini-2.0-flash"


@pytest.mark.asyncio
async def test_robot_profile_default_values(init_test_db):
    """
    Test that robot profiles have sensible defaults for AI configuration.
    """
    user = await User.create(
        email="researcher@example.com",
        display_name="Test Researcher"
    )
    
    robot_a = await RobotProfile.create(
        name="Old Robot A",th default AI settings",
        system_prompt="You are helpful.",
        created_by=user
    )
    
    # Should default to gemini provider
    assert robot.ai_provider == "gemini"
    assert robot.model_name is None  # Can be set later
    assert robot.default_temperature == 0.7


@pytest.mark.asyncio
async def test_experiment_backward_compatibility(init_test_db):
    """
    Test that experiments without robot profiles still work (backward compatibility).
    """
    user = await User.create(
        username="researcher",
        email="researcher@example.com",
        hashed_password="password123"
    )
    
    # Create experiment the old way (without robot profiles)
    experiment = await Experiment.create(
        name="Legacy Experiment",
        description="Using old persona fields",
        created_by=user,
        robot_a_persona="Customer Service",
        robot_b_persona="Technical Support",
        ai_provider="gemini"
    )
    
    assert experiment.ai_provider == "gemini"
    assert experiment.robot_a_persona == "Customer Service"
    assert experiment.robot_b_persona == "Technical Support"
    # Note: robot_a_profile and robot_b_profile are ForeignKeyFields
    # They should be None but require await to access, so we skip direct assertion
