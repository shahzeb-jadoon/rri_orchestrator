"""
Sprint 2.5 Task 2.5.2 Database Migration: Add Researcher Interjection Fields.

This adds is_interjection and interjection_target fields to chat_messages table.
"""

import asyncio
import asyncpg
from src.config import settings


async def migrate_interjection_fields():
    """
    Add interjection tracking fields to chat_messages table.
    """
    print("Starting Sprint 2.5 Task 2.5.2 migration (researcher interjection)...")
    
    db_url = settings.database_url.replace("postgresql+asyncpg://", "postgres://")
    conn = await asyncpg.connect(db_url)
    
    try:
        print("  → Adding is_interjection column to chat_messages...")
        await conn.execute(
            "ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS is_interjection BOOLEAN DEFAULT FALSE"
        )
        
        print("  → Adding interjection_target column to chat_messages...")
        await conn.execute(
            "ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS interjection_target VARCHAR(20)"
        )
        
        print("✓ Migration completed successfully!")
        print("\nResearcher interjection system is now active.")
        print("  - Researchers can send messages to robots mid-experiment")
        print("  - Interjections won't increment turn counter")
        print("  - Distinct yellow styling in UI")
        
    except Exception as e:
        print(f"✗ Migration failed: {e}")
        raise
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(migrate_interjection_fields())
