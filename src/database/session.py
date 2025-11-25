"""
Database connection and session management.

This module handles the initialization and lifecycle of the database connection
using Tortoise ORM with PostgreSQL.
"""

from typing import List, Optional

from tortoise import Tortoise, connections

from src.config import settings


# Database configuration for Tortoise ORM
TORTOISE_ORM = {
    "connections": {
        # Tortoise ORM uses postgres:// scheme, not postgresql+asyncpg://
        "default": settings.database_url.replace("postgresql+asyncpg://", "postgres://"),
    },
    "apps": {
        "models": {
            "models": ["src.database.models"],
            "default_connection": "default",
        },
    },
}


async def init_database() -> None:
    """
    Initialize the database connection and create tables if needed.
    
    This should be called once when the application starts.
    In production, use Aerich for migrations instead of generate_schemas.
    """
    await Tortoise.init(config=TORTOISE_ORM)
    
    # Only generate schemas in development
    # In production, use proper migrations
    if settings.is_development:
        await Tortoise.generate_schemas()


async def close_database() -> None:
    """
    Close all database connections gracefully.
    
    This should be called when the application shuts down.
    """
    await connections.close_all()


async def get_database_status() -> dict:
    """
    Check database connectivity and return status information.
    
    Returns:
        Dictionary containing connection status and basic info
    """
    try:
        conn = connections.get("default")
        
        # Simple query to test connection
        result = await conn.execute_query_dict("SELECT version();")
        
        return {
            "connected": True,
            "database": "rri_orchestrator",
            "version": result[0]["version"] if result else "unknown",
        }
    except Exception as e:
        return {
            "connected": False,
            "error": str(e),
        }
