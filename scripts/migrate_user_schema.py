"""
Migrate user schema from username/password auth to Cloudflare email-based auth.

Backup first: docker exec rri_postgres pg_dump -U rri_user rri_orchestrator > backup.sql
Usage: uv run python scripts/migrate_user_schema.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tortoise import Tortoise, connections
from src.config import settings
from src.utils.logger import logger


async def migrate():
    """Migrate user table to Cloudflare auth schema."""
    
    logger.info("Starting user schema migration...")
    logger.info("Connecting to database...")
    
    # Initialize Tortoise
    db_url = settings.database_url.replace("postgresql+asyncpg://", "postgres://")
    await Tortoise.init(
        db_url=db_url,
        modules={"models": ["src.database.models"]}
    )
    
    conn = connections.get("default")
    
    try:
        # Check current schema
        logger.info("Checking current schema...")
        result = await conn.execute_query_dict("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'users'
        """)
        current_columns = [row['column_name'] for row in result]
        logger.info(f"Current columns: {', '.join(current_columns)}")
        
        # Add new columns
        if 'display_name' not in current_columns:
            logger.info("Adding display_name column...")
            await conn.execute_query(
                "ALTER TABLE users ADD COLUMN display_name VARCHAR(100)"
            )
        
        if 'role' not in current_columns:
            logger.info("Adding role column...")
            await conn.execute_query(
                "ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'researcher'"
            )
        
        # Migrate data
        logger.info("Migrating existing data...")
        
        if 'full_name' in current_columns:
            await conn.execute_query("""
                UPDATE users 
                SET display_name = COALESCE(full_name, username, email)
                WHERE display_name IS NULL
            """)
        elif 'username' in current_columns:
            await conn.execute_query("""
                UPDATE users 
                SET display_name = COALESCE(username, email)
                WHERE display_name IS NULL
            """)
        
        if 'is_admin' in current_columns:
            await conn.execute_query("""
                UPDATE users 
                SET role = CASE 
                    WHEN is_admin = true THEN 'admin' 
                    ELSE 'researcher' 
                END
            """)
        
        await conn.execute_query(
            "ALTER TABLE users ALTER COLUMN display_name SET NOT NULL"
        )
        
        # Drop old columns (irreversible)
        logger.warning("Dropping old columns...")
        
        # Confirm before proceeding
        if 'username' in current_columns:
            logger.info("Dropping 'username' column...")
            await conn.execute_query("ALTER TABLE users DROP COLUMN username")
        
        if 'hashed_password' in current_columns:
            logger.info("Dropping 'hashed_password' column...")
            await conn.execute_query("ALTER TABLE users DROP COLUMN hashed_password")
        
        if 'full_name' in current_columns:
            logger.info("Dropping 'full_name' column...")
            await conn.execute_query("ALTER TABLE users DROP COLUMN full_name")
        
        if 'is_admin' in current_columns:
            logger.info("Dropping 'is_admin' column...")
            await conn.execute_query("ALTER TABLE users DROP COLUMN is_admin")
        
        # Verify migration
        logger.info("Verifying migration...")
        result = await conn.execute_query_dict("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'users'
            ORDER BY ordinal_position
        """)
        
        logger.info("Final schema:")
        for row in result:
            nullable = "NULL" if row['is_nullable'] == 'YES' else "NOT NULL"
            logger.info(f"  {row['column_name']}: {row['data_type']} {nullable}")
        
        users = await conn.execute_query_dict(
            "SELECT id, email, display_name, role FROM users"
        )
        logger.info(f"Migrated {len(users)} users")
        for user in users:
            logger.info(f"  {user['email']} ({user['display_name']}) - {user['role']}")
        
        logger.info("Migration completed successfully")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        logger.error("Restore from backup if needed")
        raise
    
    finally:
        await connections.close_all()


async def main():
    """Run migration with safety check."""
    
    logger.info("=" * 60)
    logger.info("USER SCHEMA MIGRATION")
    logger.info("username/password → Cloudflare email auth")
    logger.info("=" * 60)
    
    print("\n⚠️  WARNING: Irreversible migration")
    print("Drops: username, hashed_password, full_name, is_admin")
    print("Backup created? (yes/no): ", end="")
    
    try:
        if input().strip().lower() != 'yes':
            logger.info("Migration cancelled")
            return
    except KeyboardInterrupt:
        logger.info("\nCancelled")
        return
    
    await migrate()


if __name__ == "__main__":
    asyncio.run(main())
