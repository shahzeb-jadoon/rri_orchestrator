"""
Test configuration and shared fixtures.

This module provides common test utilities and fixtures that can be used
across all test files.
"""

import asyncio
from typing import Generator

import pytest
from tortoise import Tortoise

from src.config import settings


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """
    Create an event loop for the entire test session.
    
    This is needed for async tests to work properly.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def init_test_db():
    """
    Initialize a test database for each test function.
    
    This creates a fresh database for each test to ensure isolation.
    """
    # Use test database with postgres:// scheme for Tortoise ORM
    test_db_url = settings.database_url.replace(
        "postgresql+asyncpg://", "postgres://"
    ).replace(
        "rri_orchestrator", 
        "rri_orchestrator_test"
    )
    
    await Tortoise.init(
        db_url=test_db_url,
        modules={"models": ["src.database.models"]}
    )
    await Tortoise.generate_schemas()
    
    yield
    
    # Clean up after test - drop all tables to get fresh state for next test
    conn = Tortoise.get_connection("default")
    await conn.execute_script("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
    await Tortoise.close_connections()
