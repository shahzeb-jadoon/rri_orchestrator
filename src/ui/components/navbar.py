"""
Shared navigation bar component.
"""

from nicegui import ui, app
from datetime import datetime, timedelta
from src.database.models import ExperimentQueue, User, Experiment, ChatMessage
from src.ui.viewmodels import ActiveUserViewModel


# Global state for active users (persists across page loads)
active_users_vms = {}  # {user_id: ActiveUserViewModel}


async def load_active_users():
    """Query database and update active users ViewModels.
    
    Detects active users by finding experiments with recent activity (messages within last 60 seconds).
    This works for BOTH batch experiments and manual standalone experiments.
    """
    global active_users_vms
    
    # Define "active" as having a message in the last 60 seconds
    activity_threshold = datetime.now() - timedelta(seconds=60)
    
    # Find experiments with recent messages
    recent_messages = await ChatMessage.filter(
        created_at__gte=activity_threshold
    ).prefetch_related('experiment', 'experiment__created_by').distinct()
    
    # Track which experiments are active
    active_experiment_ids = set()
    for msg in recent_messages:
        if msg.experiment:
            active_experiment_ids.add(msg.experiment.id)
    
    # Get the active experiments with user info
    if active_experiment_ids:
        active_experiments = await Experiment.filter(
            id__in=list(active_experiment_ids),
            deleted_at__isnull=True
        ).prefetch_related('created_by')
    else:
        active_experiments = []
    
    # Count experiments per user
    user_activity = {}
    for exp in active_experiments:
        if exp.created_by:
            user_id = exp.created_by.id
            user_name = exp.created_by.display_name
            user_email = exp.created_by.email
            
            if user_id not in user_activity:
                user_activity[user_id] = {
                    'name': user_name,
                    'email': user_email,
                    'count': 0
                }
            user_activity[user_id]['count'] += 1
    
    # Update ViewModels
    active_users_vms.clear()
    for user_id, data in user_activity.items():
        vm = ActiveUserViewModel(user_id, data['name'])
        vm.activity = 'running'
        vm.experiment_count = data['count']
        vm.email = data['email']  # Store email for display
        active_users_vms[user_id] = vm


def create_navbar():
    """Create the navigation bar with active users widget."""
    with ui.header().classes('items-center justify-between'):
        with ui.row().classes('items-center gap-1'):
            # Clickable logo that goes to home
            with ui.link(target='/'):
                ui.label('RRI Orchestrator').classes('text-h6 text-white cursor-pointer font-bold')
            
            # Navigation buttons with icons
            with ui.link(target='/'):
                with ui.row().classes('items-center gap-1 px-3 py-1 rounded hover:bg-opacity-20 hover:bg-blue-500 transition-all'):
                    ui.icon('home', size='sm').classes('text-white')
                    ui.label('Home').classes('text-white')
            
            with ui.link(target='/experiments'):
                with ui.row().classes('items-center gap-1 px-3 py-1 rounded hover:bg-opacity-20 hover:bg-blue-500 transition-all'):
                    ui.icon('science', size='sm').classes('text-white')
                    ui.label('Experiments').classes('text-white')
            
            with ui.link(target='/robots'):
                with ui.row().classes('items-center gap-1 px-3 py-1 rounded hover:bg-opacity-20 hover:bg-blue-500 transition-all'):
                    ui.icon('smart_toy', size='sm').classes('text-white')
                    ui.label('Robots').classes('text-white')
            
            with ui.link(target='/batch/create'):
                with ui.row().classes('items-center gap-1 px-3 py-1 rounded hover:bg-opacity-20 hover:bg-blue-500 transition-all'):
                    ui.icon('add_box', size='sm').classes('text-white')
                    ui.label('Create Batch').classes('text-white')
            
            # Check if user is admin (stored in session)
            current_user = app.storage.user.get('current_user', {})
            if current_user.get('is_admin', False):
                with ui.link(target='/experiments/deleted'):
                    with ui.row().classes('items-center gap-1 px-3 py-1 rounded hover:bg-opacity-20 hover:bg-orange-600 transition-all bg-orange-500'):
                        ui.icon('delete', size='sm').classes('text-white')
                        ui.label('Deleted').classes('text-white')
                
                with ui.link(target='/admin/users'):
                    with ui.row().classes('items-center gap-1 px-3 py-1 rounded bg-red-600 hover:bg-red-700 transition-all'):
                        ui.icon('admin_panel_settings', size='sm').classes('text-white')
                        ui.label('Admin').classes('text-white font-bold')
        
        # Active users widget (right side)
        with ui.row().classes('items-center gap-2'):
            @ui.refreshable
            def render_active_users():
                """Render active users button with dropdown."""
                count = len(active_users_vms)
                
                # Always show button with menu
                with ui.button(f'👥 {count} Active').props('flat color=white icon=people'):
                    with ui.menu():
                        if count > 0:
                            ui.label('Active Users').classes('text-subtitle2 font-bold px-4 py-2')
                            ui.separator()
                            
                            for vm in active_users_vms.values():
                                with ui.item():
                                    with ui.item_section():
                                        ui.item_label(vm.display_name).classes('font-bold')
                                        ui.item_label(vm.email).classes('text-caption text-grey')
                                        ui.item_label(f'Running {vm.experiment_count} experiment{"s" if vm.experiment_count != 1 else ""}').classes('text-caption')
                        else:
                            ui.label('No active experiments').classes('text-grey px-4 py-2')
            
            # Initial render
            async def initial_load():
                await load_active_users()
                render_active_users.refresh()
            
            ui.timer(0.1, initial_load, once=True)  # Load immediately
            
            # Auto-refresh every 1 second for real-time updates
            async def refresh_users():
                await load_active_users()
                render_active_users.refresh()
            
            ui.timer(1.0, refresh_users)
            
            # Render widget
            render_active_users()
            
            # Logout button - clear session properly
            async def logout():
                """Clear user session and redirect to onboarding."""
                app.storage.user.clear()
                ui.navigate.to('/onboarding')
            
            ui.button('Logout', on_click=logout).props('flat color=white').classes('text-white')
