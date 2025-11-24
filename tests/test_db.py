"""
Database layer tests.

These tests verify that database models and operations work correctly.
"""

import pytest
from tortoise.exceptions import IntegrityError

from src.database import User, Experiment, ChatMessage


@pytest.mark.asyncio
async def test_create_user(init_test_db):
    """
    Test creating a new user in the database.
    """
    user = await User.create(
        username="testuser",
        email="test@example.com",
        hashed_password="hashed_password_here",
        full_name="Test User"
    )
    
    assert user.id is not None
    assert user.username == "testuser"
    assert user.email == "test@example.com"
    assert user.is_active is True
    assert user.is_admin is False


@pytest.mark.asyncio
async def test_unique_username_constraint(init_test_db):
    """
    Test that duplicate usernames are not allowed.
    """
    await User.create(
        username="duplicate",
        email="user1@example.com",
        hashed_password="password1"
    )
    
    # Attempting to create another user with same username should fail
    with pytest.raises(IntegrityError):
        await User.create(
            username="duplicate",
            email="user2@example.com",
            hashed_password="password2"
        )


@pytest.mark.asyncio
async def test_create_experiment_with_user(init_test_db):
    """
    Test creating an experiment linked to a user.
    """
    user = await User.create(
        username="researcher",
        email="researcher@example.com",
        hashed_password="password"
    )
    
    experiment = await Experiment.create(
        name="Test Experiment",
        description="Testing robot interactions",
        created_by=user,
        robot_a_persona="friendly",
        robot_b_persona="analytical"
    )
    
    assert experiment.id is not None
    assert experiment.name == "Test Experiment"
    assert experiment.created_by_id == user.id
    assert experiment.is_active is True


@pytest.mark.asyncio
async def test_create_chat_message(init_test_db):
    """
    Test creating a chat message in an experiment.
    """
    user = await User.create(
        username="tester",
        email="tester@example.com",
        hashed_password="password"
    )
    
    experiment = await Experiment.create(
        name="Chat Test",
        created_by=user
    )
    
    message = await ChatMessage.create(
        experiment=experiment,
        role="user",
        content="Hello, robot!"
    )
    
    assert message.id is not None
    assert message.role == "user"
    assert message.content == "Hello, robot!"
    assert message.experiment_id == experiment.id


@pytest.mark.asyncio
async def test_experiment_message_relationship(init_test_db):
    """
    Test that we can query messages through experiment relationship.
    """
    user = await User.create(
        username="tester",
        email="tester@example.com",
        hashed_password="password"
    )
    
    experiment = await Experiment.create(
        name="Relationship Test",
        created_by=user
    )
    
    # Create multiple messages
    await ChatMessage.create(
        experiment=experiment,
        role="user",
        content="Message 1"
    )
    await ChatMessage.create(
        experiment=experiment,
        role="assistant",
        content="Response 1"
    )
    
    # Fetch experiment with messages
    exp = await Experiment.get(id=experiment.id).prefetch_related("messages")
    messages = await exp.messages.all()
    
    assert len(messages) == 2
    assert messages[0].content == "Message 1"
    assert messages[1].content == "Response 1"
