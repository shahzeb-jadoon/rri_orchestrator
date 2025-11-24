"""
Script to create an admin user account.

This script allows you to create the first admin user for accessing
the RRI Orchestrator interface.
"""

import asyncio
import getpass
import sys
from pathlib import Path

# Add src to path so imports work
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import User, init_database, close_database
from src.utils import logger


def hash_password(password: str) -> str:
    """
    Hash a password using a simple method.
    
    Note: In production, use proper password hashing like bcrypt or argon2.
    This is a placeholder for the initial setup.
    """
    import hashlib
    return hashlib.sha256(password.encode()).hexdigest()


async def create_admin_user(
    username: str,
    email: str,
    password: str,
    full_name: str = None
) -> None:
    """
    Create a new admin user in the database.
    
    Args:
        username: Unique username for login
        email: User email address
        password: Plain text password (will be hashed)
        full_name: Optional full name
    """
    try:
        # Check if user already exists
        existing_user = await User.filter(username=username).first()
        if existing_user:
            logger.error(f"User '{username}' already exists")
            return
        
        # Create the user
        user = await User.create(
            username=username,
            email=email,
            hashed_password=hash_password(password),
            full_name=full_name,
            is_admin=True,
            is_active=True
        )
        
        logger.info(f"Admin user '{username}' created successfully (ID: {user.id})")
        
    except Exception as e:
        logger.error(f"Failed to create user: {e}")
        raise


async def main() -> None:
    """
    Interactive script to create an admin user.
    """
    logger.info("Admin User Creation")
    logger.info("=" * 50)
    
    try:
        # Initialize database
        await init_database()
        
        # Get user input
        print("\nEnter admin user details:")
        username = input("Username: ").strip()
        email = input("Email: ").strip()
        full_name = input("Full Name (optional): ").strip() or None
        
        # Get password securely
        password = getpass.getpass("Password: ")
        password_confirm = getpass.getpass("Confirm Password: ")
        
        if password != password_confirm:
            logger.error("Passwords do not match")
            sys.exit(1)
        
        if len(password) < 8:
            logger.error("Password must be at least 8 characters")
            sys.exit(1)
        
        # Create the user
        await create_admin_user(username, email, password, full_name)
        
        # Close database
        await close_database()
        
    except KeyboardInterrupt:
        logger.info("\nUser creation cancelled")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
