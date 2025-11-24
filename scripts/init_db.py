"""
Database initialization script.

This script creates all database tables and sets up the initial schema.
Run this once when setting up the project for the first time.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path so imports work
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import close_database, init_database
from src.utils import logger


async def main() -> None:
    """
    Initialize the database and create all tables.
    """
    logger.info("Starting database initialization...")
    
    try:
        # Initialize Tortoise ORM and create tables
        await init_database()
        logger.info("Database tables created successfully")
        
        # Close connections
        await close_database()
        logger.info("Database initialization complete")
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
