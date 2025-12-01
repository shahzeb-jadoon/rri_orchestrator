"""
Database migration script for Sprint 2 Task 2.1: Overnight Scheduling.

This script adds scheduled_start field to ExperimentBatch table.
"""

import asyncio
import asyncpg
from src.config import settings


async def migrate_database():
    """
    Apply Sprint 2.1 schema changes: Add scheduled_start to experiment_batch.
    """
    print("Starting Sprint 2.1 database migration (Overnight Scheduling)...")
    
    # Extract connection details from DATABASE_URL
    db_url = settings.database_url.replace("postgresql+asyncpg://", "postgres://")
    
    # Connect directly to PostgreSQL
    conn = await asyncpg.connect(db_url)
    
    try:
        # Check current table structure
        print("  → Checking experiment_batches table structure...")
        columns = await conn.fetch("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'experiment_batches'
        """)
        
        existing_columns = [col['column_name'] for col in columns]
        print(f"    Found {len(existing_columns)} existing columns")
        
        # Add scheduled_start column if it doesn't exist
        if 'scheduled_start' not in existing_columns:
            print("  → Adding scheduled_start column to experiment_batches...")
            await conn.execute("""
                ALTER TABLE experiment_batches 
                ADD COLUMN scheduled_start TIMESTAMP WITH TIME ZONE NULL
            """)
            print("    ✓ scheduled_start column added")
        else:
            print("    ℹ scheduled_start column already exists, checking type...")
            # Check if it's the wrong type and fix it
            col_type = await conn.fetchval("""
                SELECT data_type 
                FROM information_schema.columns 
                WHERE table_name = 'experiment_batches' 
                AND column_name = 'scheduled_start'
            """)
            if col_type == 'timestamp without time zone':
                print("    → Converting scheduled_start to TIMESTAMP WITH TIME ZONE...")
                await conn.execute("""
                    ALTER TABLE experiment_batches 
                    ALTER COLUMN scheduled_start TYPE TIMESTAMP WITH TIME ZONE
                """)
                print("    ✓ scheduled_start column type updated")
        
        print("\n✓ Sprint 2.1 migration completed successfully!")
        
    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        raise
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(migrate_database())
