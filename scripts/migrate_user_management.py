"""
Add soft delete and admin approval to users.

Changes CASCADE DELETE to SET NULL, adds approval fields,
preserves creator attribution when users are deactivated.

Run: uv run python scripts/migrate_user_management.py
"""

import asyncio
from datetime import datetime

from tortoise import Tortoise, connections

from src.config import settings
from src.utils.logger import logger


async def migrate():
    """Run migration."""
    
    # Initialize database
    db_url = settings.database_url.replace("postgresql+asyncpg://", "postgres://")
    await Tortoise.init(
        db_url=db_url,
        modules={"models": ["src.database.models"]}
    )
    
    conn = connections.get("default")
    logger.info("Starting user management migration...")
    
    try:
        # Step 1: Add new columns to users table
        logger.info("Adding approval system fields to users table...")
        
        await conn.execute_query(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_approved BOOLEAN DEFAULT FALSE"
        )
        await conn.execute_query(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS approved_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL"
        )
        await conn.execute_query(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS approved_at TIMESTAMP WITH TIME ZONE"
        )
        await conn.execute_query(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS deactivated_at TIMESTAMP WITH TIME ZONE"
        )
        await conn.execute_query(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS deactivated_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL"
        )
        await conn.execute_query(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS deactivation_reason TEXT"
        )
        
        # Step 2: Auto-approve existing users (they're already in the system)
        logger.info("Auto-approving existing users...")
        await conn.execute_query(
            "UPDATE users SET is_approved = TRUE WHERE is_approved = FALSE"
        )
        
        # Step 3: Add backup attribution fields to experiments
        logger.info("Adding backup attribution to experiments table...")
        
        await conn.execute_query(
            "ALTER TABLE experiments ADD COLUMN IF NOT EXISTS created_by_email VARCHAR(255)"
        )
        await conn.execute_query(
            "ALTER TABLE experiments ADD COLUMN IF NOT EXISTS created_by_name VARCHAR(100)"
        )
        
        # Populate backup fields from existing data
        await conn.execute_query("""
            UPDATE experiments e
            SET created_by_email = u.email,
                created_by_name = u.display_name
            FROM users u
            WHERE e.created_by_id = u.id
              AND e.created_by_email IS NULL
        """)
        
        # Step 4: Add backup attribution fields to experiment_batches
        logger.info("Adding backup attribution to experiment_batches table...")
        
        await conn.execute_query(
            "ALTER TABLE experiment_batches ADD COLUMN IF NOT EXISTS created_by_email VARCHAR(255)"
        )
        await conn.execute_query(
            "ALTER TABLE experiment_batches ADD COLUMN IF NOT EXISTS created_by_name VARCHAR(100)"
        )
        
        # Populate backup fields from existing data
        await conn.execute_query("""
            UPDATE experiment_batches eb
            SET created_by_email = u.email,
                created_by_name = u.display_name
            FROM users u
            WHERE eb.created_by_id = u.id
              AND eb.created_by_email IS NULL
        """)
        
        # Step 5: Change foreign key constraints to SET NULL
        logger.info("Updating foreign key constraints to preserve data...")
        
        # Drop old constraint on experiments
        await conn.execute_query(
            "ALTER TABLE experiments DROP CONSTRAINT IF EXISTS experiments_created_by_id_fkey"
        )
        # Add new constraint with SET NULL
        await conn.execute_query("""
            ALTER TABLE experiments 
            ADD CONSTRAINT experiments_created_by_id_fkey 
            FOREIGN KEY (created_by_id) REFERENCES users(id) ON DELETE SET NULL
        """)
        
        # Drop old constraint on experiment_batches
        await conn.execute_query(
            "ALTER TABLE experiment_batches DROP CONSTRAINT IF EXISTS experiment_batches_created_by_id_fkey"
        )
        # Add new constraint with SET NULL
        await conn.execute_query("""
            ALTER TABLE experiment_batches 
            ADD CONSTRAINT experiment_batches_created_by_id_fkey 
            FOREIGN KEY (created_by_id) REFERENCES users(id) ON DELETE SET NULL
        """)
        
        # Step 6: Also update robot_profiles for consistency
        await conn.execute_query(
            "ALTER TABLE robot_profiles DROP CONSTRAINT IF EXISTS robot_profiles_created_by_id_fkey"
        )
        await conn.execute_query("""
            ALTER TABLE robot_profiles 
            ADD CONSTRAINT robot_profiles_created_by_id_fkey 
            FOREIGN KEY (created_by_id) REFERENCES users(id) ON DELETE SET NULL
        """)
        
        logger.info("✅ Migration completed successfully!")
        logger.info("Summary:")
        logger.info("  - Added approval system fields to users")
        logger.info("  - Auto-approved existing users")
        logger.info("  - Added backup attribution fields")
        logger.info("  - Changed CASCADE DELETE to SET NULL")
        logger.info("  - Data will now be preserved when users are deactivated")
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        raise
    finally:
        await connections.close_all()


if __name__ == "__main__":
    asyncio.run(migrate())
