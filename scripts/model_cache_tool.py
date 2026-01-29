"""
Model Cache Management Tool.

Allows viewing, refreshing, and managing the AI model discovery cache.

Run: uv run python scripts/model_cache_tool.py [command]

Commands:
  status       Show current cache status and available models
  refresh      Force refresh cache from provider APIs
  migrations   Show model migration mappings
  help         Show help message
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ai.model_discovery import (
    refresh_model_cache,
    get_cache_status,
    get_available_models,
    MODEL_MIGRATIONS,
)
from src.utils.logger import logger


async def show_status():
    """Display current cache status."""
    logger.info("=" * 70)
    logger.info("Model Cache Status")
    logger.info("=" * 70)
    logger.info("")
    
    status = get_cache_status()
    
    logger.info(f"Last Updated: {status['last_updated'] or 'Never'}")
    logger.info(f"Is Expired:   {status['is_expired']}")
    logger.info(f"Cache File:   {status['cache_file']}")
    logger.info(f"Total Models: {status['total_models']}")
    logger.info("")
    
    if status['errors']:
        logger.info("Discovery Errors:")
        for provider, error in status['errors'].items():
            logger.info(f"  • {provider}: {error}")
        logger.info("")
    
    logger.info("Available Models by Provider:")
    logger.info("")
    
    for provider in ['openai', 'gemini', 'anthropic']:
        models = get_available_models(provider)
        logger.info(f"  {provider.upper()} ({len(models)} models):")
        for model in models[:10]:  # Show first 10
            logger.info(f"    - {model}")
        if len(models) > 10:
            logger.info(f"    ... and {len(models) - 10} more")
        logger.info("")


async def refresh_cache():
    """Force refresh the model cache."""
    logger.info("=" * 70)
    logger.info("Refreshing Model Cache")
    logger.info("=" * 70)
    logger.info("")
    
    logger.info("Discovering models from provider APIs...")
    logger.info("This may take a few seconds...")
    logger.info("")
    
    try:
        results = await refresh_model_cache(force=True)
        
        logger.info("✓ Cache refresh complete!")
        logger.info("")
        
        for provider, models in results.items():
            logger.info(f"  {provider.upper()}: {len(models)} models discovered")
        
        logger.info("")
        
    except Exception as e:
        logger.error(f"✗ Error refreshing cache: {e}")
        import traceback
        traceback.print_exc()


def show_migrations():
    """Display model migration mappings."""
    logger.info("=" * 70)
    logger.info("Model Migration Mappings")
    logger.info("=" * 70)
    logger.info("")
    
    if not MODEL_MIGRATIONS:
        logger.info("No migration mappings defined")
        return
    
    logger.info("Deprecated models and their replacements:")
    logger.info("")
    
    for old_model, new_model in MODEL_MIGRATIONS.items():
        logger.info(f"  {old_model:30s} → {new_model}")
    
    logger.info("")


def show_help():
    """Display usage information."""
    logger.info("=" * 70)
    logger.info("Model Cache Management Tool")
    logger.info("=" * 70)
    logger.info("")
    logger.info("Usage: uv run python scripts/model_cache_tool.py [command]")
    logger.info("")
    logger.info("Commands:")
    logger.info("  status       Show current cache status and available models")
    logger.info("  refresh      Force refresh cache from provider APIs")
    logger.info("  migrations   Show model migration mappings")
    logger.info("  help         Show this help message")
    logger.info("")


async def main():
    """Main CLI entry point."""
    command = sys.argv[1] if len(sys.argv) > 1 else "status"
    
    if command == "status":
        await show_status()
    elif command == "refresh":
        await refresh_cache()
    elif command == "migrations":
        show_migrations()
    elif command == "help":
        show_help()
    else:
        print(f"Unknown command: {command}")
        print()
        show_help()
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\nCancelled by user")
    except Exception as e:
        logger.error(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
