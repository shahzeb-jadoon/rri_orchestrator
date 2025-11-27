"""
RRI Orchestrator - Main application entry point.

This module initializes the NiceGUI web application and sets up the
database connection lifecycle.
"""

from contextlib import asynccontextmanager

from nicegui import app, ui

from src.config import settings
from src.database import close_database, get_database_status, init_database
from src.utils import logger

# Import UI pages to register routes
from src.ui.pages import robots  # noqa: F401
from src.ui.pages import experiments  # noqa: F401


@asynccontextmanager
async def lifespan():
    """
    Application lifecycle manager.
    
    This handles startup and shutdown tasks like database initialization
    and cleanup.
    """
    # Startup
    logger.info("Starting RRI Orchestrator...")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Host: {settings.host}:{settings.port}")
    
    try:
        await init_database()
        db_status = await get_database_status()
        
        if db_status["connected"]:
            logger.info("Database connected successfully")
        else:
            logger.error(f"Database connection failed: {db_status.get('error')}")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down RRI Orchestrator...")
    await close_database()
    logger.info("Database connections closed")


# Configure NiceGUI app
app.on_startup(lifespan().__aenter__)
app.on_shutdown(lifespan().__aexit__)


@ui.page("/")
async def index_page():
    """
    Main landing page of the application.
    """
    from src.ui.components import create_navbar
    
    create_navbar()
    
    ui.label("RRI Orchestrator").classes("text-h3")
    ui.label("Robot-Robot Interaction Research Platform").classes("text-subtitle1 text-grey")
    
    ui.separator()
    
    # Quick actions
    with ui.row().classes('gap-4 mt-4'):
        with ui.card().classes('p-4'):
            ui.label('🤖 Robot Profiles').classes('text-h6')
            ui.label('Create and manage AI robot configurations').classes('text-caption text-grey')
            ui.button('Manage Robots', on_click=lambda: ui.navigate.to('/robots')).props('color=primary flat')
        
        with ui.card().classes('p-4'):
            ui.label('🧪 Experiments').classes('text-h6')
            ui.label('Set up robot-robot conversations').classes('text-caption text-grey')
            ui.button('View Experiments', on_click=lambda: ui.navigate.to('/experiments')).props('color=primary flat')
    
    ui.separator()
    
    # System status
    db_status = await get_database_status()
    
    with ui.card():
        ui.label("System Status").classes("text-h6")
        
        if db_status["connected"]:
            ui.label("✓ Database Connected").classes("text-green")
        else:
            ui.label("✗ Database Disconnected").classes("text-red")
        
        ui.label(f"Environment: {settings.environment}")
        ui.label(f"Default AI Provider: {settings.default_ai_provider}")


def main():
    """
    Launch the web application.
    """
    logger.info("Initializing web server...")
    
    ui.run(
        host=settings.host,
        port=settings.port,
        title="RRI Orchestrator",
        reload=settings.is_development,
        show=False  # Don't auto-open browser
    )


if __name__ in {"__main__", "__mp_main__"}:
    main()
