"""
Shared navigation bar component.
"""

from nicegui import ui, app
from src.database.models import ExperimentQueue, User
from src.ui.viewmodels import ActiveUserViewModel


# Global state for active users (persists across page loads)
active_users_vms = {}  # {user_id: ActiveUserViewModel}


async def load_active_users():
    """Query database and update active users ViewModels."""
    global active_users_vms
    
    # Get all running experiments with user info
    running_entries = await ExperimentQueue.filter(
        status='running'
    ).prefetch_related('experiment', 'experiment__created_by')
    
    # Count experiments per user
    user_activity = {}
    for entry in running_entries:
        if entry.experiment and entry.experiment.created_by:
            user_id = entry.experiment.created_by.id
            user_name = entry.experiment.created_by.display_name
            if user_id not in user_activity:
                user_activity[user_id] = {
                    'name': user_name,
                    'count': 0
                }
            user_activity[user_id]['count'] += 1
    
    # Update ViewModels
    active_users_vms.clear()
    for user_id, data in user_activity.items():
        vm = ActiveUserViewModel(user_id, data['name'])
        vm.activity = 'running'
        vm.experiment_count = data['count']
        active_users_vms[user_id] = vm


def create_navbar():
    """Create the navigation bar with active users widget."""
    with ui.header().classes('items-center justify-between'):
        with ui.row().classes('items-center'):
            # Clickable logo that goes to home
            with ui.link(target='/'):
                ui.label('RRI Orchestrator').classes('text-h6 text-white cursor-pointer')
            ui.link('Experiments', '/experiments').classes('text-white')
            ui.link('Robots', '/robots').classes('text-white')
            ui.link('Create Batch', '/batch/create').classes('text-white')
            
            # Check if user is admin (stored in session)
            is_admin = app.storage.user.get('is_admin', False)
            if is_admin:
                ui.link('Admin', '/admin/users').classes('text-white')
        
        # Active users widget (right side)
        with ui.row().classes('items-center gap-2'):
            @ui.refreshable
            def render_active_users():
                """Render active users button with dropdown."""
                count = len(active_users_vms)
                
                if count > 0:
                    with ui.button(f'👥 {count} Active', icon='people').props('flat color=white'):
                        with ui.menu():
                            ui.label('Active Users').classes('text-subtitle2 font-bold px-4 py-2')
                            ui.separator()
                            
                            for vm in active_users_vms.values():
                                with ui.item():
                                    with ui.item_section():
                                        ui.item_label(vm.display_name).classes('font-bold')
                                        ui.item_label(f'Running {vm.experiment_count} experiment{"s" if vm.experiment_count != 1 else ""}').classes('text-caption')
                else:
                    ui.badge('👥 0 Active', color='grey').props('outline').classes('opacity-60')
            
            # Initial render
            async def initial_load():
                await load_active_users()
                render_active_users.refresh()
            
            ui.timer(0.1, initial_load, once=True)  # Load immediately
            
            # Auto-refresh every 30 seconds
            async def refresh_users():
                await load_active_users()
                render_active_users.refresh()
            
            ui.timer(30.0, refresh_users)
            
            # Render widget
            render_active_users()
            
            # Logout button
            def logout():
                app.storage.user.clear()
                ui.navigate.to('/onboarding')
            
            ui.button('Logout', on_click=logout).props('flat color=white')
