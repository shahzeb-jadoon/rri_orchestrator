#!/usr/bin/env python3
"""
Migration script for Sprint 2.5, Task 2.5.3: Message Impersonation System
Adds fields to support researcher-written messages that appear as robot messages
with optional visibility control for counterfactual research.
"""
import asyncio
import asyncpg
from src.config import settings


async def main():
    # Connect to database using settings
    db_url = settings.database_url.replace("postgresql+asyncpg://", "postgres://")
    conn = await asyncpg.connect(db_url)
    
    try:
        # Add is_researcher_written column (messages written by researcher AS robot)
        print("Adding is_researcher_written column...")
        await conn.execute("""
            ALTER TABLE chat_messages 
            ADD COLUMN IF NOT EXISTS is_researcher_written BOOLEAN DEFAULT FALSE;
        """)
        
        # Add visible_to_other_robot column (for A/B testing and counterfactuals)
        print("Adding visible_to_other_robot column...")
        await conn.execute("""
            ALTER TABLE chat_messages 
            ADD COLUMN IF NOT EXISTS visible_to_other_robot BOOLEAN DEFAULT TRUE;
        """)
        
        print("\n✅ Migration completed successfully!")
        print("   • Added is_researcher_written (tracks impersonated messages)")
        print("   • Added visible_to_other_robot (controls visibility for counterfactuals)")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        raise
    finally:
        await conn.close()


if __name__ == '__main__':
    asyncio.run(main())
