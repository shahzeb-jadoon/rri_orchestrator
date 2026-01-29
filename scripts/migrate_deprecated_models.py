"""
Data Migration: Update Robot Profiles with Deprecated AI Models.

This script identifies robots using deprecated models (like gemini-pro)
and updates them to use current alternatives (like gemini-2.5-flash).

This is a DATA migration (not schema), updating existing records.

Run: uv run python scripts/migrate_deprecated_models.py
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.models import RobotProfile
from src.database.session import init_database
from src.ai.model_discovery import MODEL_MIGRATIONS
from src.utils.logger import logger


async def migrate_deprecated_models():
    """Migrate robots using deprecated models to current alternatives."""
    
    logger.info("=" * 70)
    logger.info("Robot Profile Model Migration")
    logger.info("=" * 70)
    logger.info("")
    
    # Initialize database
    await init_database()
    logger.info("✓ Database connected")
    logger.info("")
    
    # Get all robot profiles
    robots = await RobotProfile.all()
    logger.info(f"Found {len(robots)} robot profiles")
    logger.info("")
    
    # Find robots needing migration
    migrations_needed = []
    
    for robot in robots:
        if robot.model_name in MODEL_MIGRATIONS:
            new_model = MODEL_MIGRATIONS[robot.model_name]
            migrations_needed.append((robot, new_model))
    
    if not migrations_needed:
        logger.info("✓ All robots are using current models!")
        logger.info("")
        return
    
    # Display migrations
    logger.info(f"Found {len(migrations_needed)} robots needing migration:")
    logger.info("")
    
    for robot, new_model in migrations_needed:
        logger.info(f"  • {robot.name}")
        logger.info(f"    Provider: {robot.ai_provider}")
        logger.info(f"    Current:  {robot.model_name} (deprecated)")
        logger.info(f"    New:      {new_model}")
        logger.info("")
    
    # Ask for confirmation
    response = input("Proceed with migration? [y/N]: ").strip().lower()
    
    if response != 'y':
        logger.info("Migration cancelled")
        return
    
    logger.info("")
    logger.info("Migrating robots...")
    logger.info("")
    
    # Perform migrations
    for robot, new_model in migrations_needed:
        old_model = robot.model_name
        robot.model_name = new_model
        await robot.save()
        
        logger.info(f"  ✓ {robot.name}: {old_model} → {new_model}")
    
    logger.info("")
    logger.info(f"✓ Successfully migrated {len(migrations_needed)} robot profiles!")
    logger.info("")
    logger.info("Summary:")
    logger.info("  - Updated deprecated model references")
    logger.info("  - All robots now use current model versions")
    logger.info("  - Experiments can now run without 404 errors")


if __name__ == "__main__":
    try:
        asyncio.run(migrate_deprecated_models())
    except KeyboardInterrupt:
        logger.info("\nMigration cancelled by user")
    except Exception as e:
        logger.error(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
