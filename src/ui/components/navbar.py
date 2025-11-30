"""
Navigation bar component for RRI Orchestrator.
"""

from nicegui import ui, app
from src.database import get_database_status


def create_navbar():
    """Create navigation bar with links and DB status."""
    with ui.header().classes('items-center justify-between'):
        with ui.row().classes('items-center'):
            ui.label('🤖 RRI Orchestrator').classes('text-h5 text-white')
        
        with ui.row().classes('items-center gap-4'):
            ui.link('Home', '/').classes('text-white')
            ui.link('Robots', '/robots').classes('text-white')
            ui.link('Experiments', '/experiments').classes('text-white')
            ui.link('Create Batch', '/batch/create').classes('text-white font-bold')
            
            # Admin link - only show to admins
            current_user = app.storage.user.get('current_user')
            if current_user and current_user.get('is_admin'):
                ui.link('👑 Admin', '/admin/users').classes('text-white bg-red-600 px-2 py-1 rounded')
            
            # Database status indicator
            async def show_status():
                status = await get_database_status()
                icon = '✓' if status['connected'] else '✗'
                color = 'green' if status['connected'] else 'red'
                ui.label(f'{icon} DB').classes(f'text-{color}')
            
            ui.timer(5.0, show_status, once=True)
