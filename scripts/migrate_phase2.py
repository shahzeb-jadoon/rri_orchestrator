"""
Database migration script for Phase 2: Per-Robot AI Selection.

This script adds new fields to existing tables:
- RobotProfile: ai_provider, model_name
- Experiment: robot_a_profile_id, robot_b_profile_id

Run this before using Phase 2 features.
"""

import asyncio
import asyncpg
from src.config import settings


async def migrate_database():
    """
    Apply Phase 2 schema changes to existing database.
    """
    print("Starting Phase 2 database migration...")
    
    # Extract connection details from DATABASE_URL
    db_url = settings.database_url.replace("postgresql+asyncpg://", "postgres://")
    
    # Connect directly to PostgreSQL
    conn = await asyncpg.connect(db_url)
    
    try:
        # Add AI provider fields to robot_profiles table
        print("  → Adding ai_provider column to robot_profiles...")
        await conn.execute(
            "ALTER TABLE robot_profiles ADD COLUMN IF NOT EXISTS ai_provider VARCHAR(50) DEFAULT 'gemini'"
        )
        
        print("  → Adding model_name column to robot_profiles...")
        await conn.execute(
            "ALTER TABLE robot_profiles ADD COLUMN IF NOT EXISTS model_name VARCHAR(100)"
        )
        
        # Add robot profile foreign keys to experiments table
        print("  → Adding robot_a_profile_id column to experiments...")
        await conn.execute(
            "ALTER TABLE experiments ADD COLUMN IF NOT EXISTS robot_a_profile_id INT"
        )
        
        print("  → Adding robot_b_profile_id column to experiments...")
        await conn.execute(
            "ALTER TABLE experiments ADD COLUMN IF NOT EXISTS robot_b_profile_id INT"
        )
        
        # Add foreign key constraints
        print("  → Adding foreign key constraints...")
        await conn.execute(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint 
                    WHERE conname = 'experiments_robot_a_profile_fkey'
                ) THEN
                    ALTER TABLE experiments 
                    ADD CONSTRAINT experiments_robot_a_profile_fkey 
                    FOREIGN KEY (robot_a_profile_id) 
                    REFERENCES robot_profiles(id) 
                    ON DELETE SET NULL;
                END IF;
            END$$;
            """
        )
        
        await conn.execute(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint 
                    WHERE conname = 'experiments_robot_b_profile_fkey'
                ) THEN
                    ALTER TABLE experiments 
                    ADD CONSTRAINT experiments_robot_b_profile_fkey 
                    FOREIGN KEY (robot_b_profile_id) 
                    REFERENCES robot_profiles(id) 
                    ON DELETE SET NULL;
                END IF;
            END$$;
            """
        )
        
        print("✓ Migration completed successfully!")
        print("\nPhase 2 database schema is now active.")
        print("You can now use per-robot AI provider selection.")
        
    except Exception as e:
        print(f"✗ Migration failed: {e}")
        raise
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(migrate_database())
