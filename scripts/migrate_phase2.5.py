"""
Phase 2.5 Database Migration: Add detailed token tracking to ChatMessage.

This adds input_tokens, output_tokens, cost_usd, robot_name, and robot_provider fields.
"""

import asyncio
import asyncpg
from src.config import settings


async def migrate_chat_messages():
    """
    Add new tracking fields to chat_messages table.
    """
    print("Starting Phase 2.5 database migration (chat message tracking)...")
    
    db_url = settings.database_url.replace("postgresql+asyncpg://", "postgres://")
    conn = await asyncpg.connect(db_url)
    
    try:
        print("  → Adding input_tokens column to chat_messages...")
        await conn.execute(
            "ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS input_tokens INT DEFAULT 0"
        )
        
        print("  → Adding output_tokens column to chat_messages...")
        await conn.execute(
            "ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS output_tokens INT DEFAULT 0"
        )
        
        print("  → Adding cost_usd column to chat_messages...")
        await conn.execute(
            "ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS cost_usd DECIMAL(10, 6)"
        )
        
        print("  → Adding robot_name column to chat_messages...")
        await conn.execute(
            "ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS robot_name VARCHAR(100)"
        )
        
        print("  → Adding robot_provider column to chat_messages...")
        await conn.execute(
            "ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS robot_provider VARCHAR(50)"
        )
        
        print("✓ Migration completed successfully!")
        print("\nCost tracking enhancements are now active.")
        
    except Exception as e:
        print(f"✗ Migration failed: {e}")
        raise
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(migrate_chat_messages())
