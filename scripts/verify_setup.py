"""
Setup Verification Script

Run this to verify that the RRI Orchestrator infrastructure is properly configured.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def verify_setup():
    """
    Check that all components are properly configured.
    """
    from src.config import settings
    from src.database import get_database_status
    from src.utils import logger
    
    logger.info("=" * 60)
    logger.info("RRI Orchestrator - Setup Verification")
    logger.info("=" * 60)
    
    checks_passed = 0
    checks_failed = 0
    
    # Check 1: Environment variables
    logger.info("\n1. Checking environment configuration...")
    if settings.database_url:
        logger.info("   ✓ DATABASE_URL is set")
        checks_passed += 1
    else:
        logger.error("   ✗ DATABASE_URL is not set")
        checks_failed += 1
    
    if settings.secret_key != "dev-secret-key-change-in-production":
        logger.info("   ✓ SECRET_KEY is configured")
        checks_passed += 1
    else:
        logger.warning("   ⚠ SECRET_KEY is using default value")
        checks_failed += 1
    
    # Check 2: Database connection
    logger.info("\n2. Checking database connection...")
    try:
        from src.database import init_database, close_database
        await init_database()
        db_status = await get_database_status()
        
        if db_status["connected"]:
            logger.info("   ✓ Database connection successful")
            logger.info(f"   Database: {db_status.get('database', 'unknown')}")
            checks_passed += 1
        else:
            logger.error(f"   ✗ Database connection failed: {db_status.get('error')}")
            checks_failed += 1
        
        await close_database()
    except Exception as e:
        logger.error(f"   ✗ Database check failed: {e}")
        checks_failed += 1
    
    # Check 3: AI API keys
    logger.info("\n3. Checking AI provider configuration...")
    if settings.gemini_api_key and settings.gemini_api_key != "your_gemini_api_key_here":
        logger.info("   ✓ Gemini API key is configured")
        checks_passed += 1
    else:
        logger.warning("   ⚠ Gemini API key not configured")
        checks_failed += 1
    
    if settings.openai_api_key and settings.openai_api_key != "your_openai_api_key_here":
        logger.info("   ✓ OpenAI API key is configured")
        checks_passed += 1
    else:
        logger.warning("   ⚠ OpenAI API key not configured")
        checks_failed += 1
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info(f"Verification Complete: {checks_passed} passed, {checks_failed} issues")
    logger.info("=" * 60)
    
    if checks_failed == 0:
        logger.info("✓ All checks passed! Ready to proceed.")
        return True
    else:
        logger.warning("⚠ Some checks failed. Review the issues above.")
        return False


if __name__ == "__main__":
    result = asyncio.run(verify_setup())
    sys.exit(0 if result else 1)
