"""
Batch progress monitoring and control page.

Real-time tracking of batch execution with pause/resume/cancel controls.
"""

from nicegui import ui
from datetime import datetime
from starlette.requests import Request
from src.database.models import ExperimentBatch, ExperimentQueue, Experiment, ChatMessage
from src.ui.components import create_navbar
from src.ui.utils import get_friendly_error_message


@ui.page('/batch/{batch_id}')
async def batch_progress_page(batch_id: int, request: Request):
    """View and manage batch progress."""
    create_navbar()
    
    # Get current user
    user = getattr(request.state, 'user', None)
    if not user:
        ui.label('Please log in to view batch progress').classes('text-negative')
        return
    
    # Load batch
    try:
        batch = await ExperimentBatch.get(id=batch_id).prefetch_related('created_by', 'paused_by')
    except:
        ui.label(f'Batch #{batch_id} not found').classes('text-negative')
        return
    
    # Permission check: only creator or admin can control batch
    can_control = user.is_admin or batch.created_by_id == user.id
    
    # Header
    with ui.row().classes('w-full justify-between items-center'):
        with ui.column():
            ui.label(batch.name).classes('text-h4')
            creator_name = batch.created_by.display_name if batch.created_by else batch.created_by_name or 'Unknown'
            ui.label(f'Created by: {creator_name} • Started: {batch.started_at.strftime("%Y-%m-%d %H:%M") if batch.started_at else "Not started"}').classes('text-caption text-grey')
        
        # Control buttons (only for authorized users)
        if can_control:
            with ui.row().classes('gap-2'):
                pause_btn = ui.button('')
                cancel_btn = ui.button('❌ Cancel Batch').props('color=negative outline')
    
    ui.space()
    
    # Refreshable components for smooth updates without scroll reset
    @ui.refreshable
    async def render_stats():
        """Render batch statistics cards."""
        # Get queue statistics
        total = await ExperimentQueue.filter(batch_id=batch_id).count()
        completed = await ExperimentQueue.filter(batch_id=batch_id, status='completed').count()
        running = await ExperimentQueue.filter(batch_id=batch_id, status='running').count()
        queued = await ExperimentQueue.filter(batch_id=batch_id, status='queued').count()
        failed = await ExperimentQueue.filter(batch_id=batch_id, status='failed').count()
        
        # Progress bar
        progress = (completed / total * 100) if total > 0 else 0
        with ui.card().classes('w-full p-4'):
            ui.label(f'Progress: {completed}/{total} ({progress:.1f}%)').classes('text-h6')
            ui.linear_progress(value=completed / total if total > 0 else 0).props('size=20px color=positive')
        
        # Status cards
        with ui.grid(columns=4).classes('gap-4 w-full'):
            # Completed
            with ui.card().classes('p-4 text-center bg-positive'):
                ui.icon('check_circle', size='lg').classes('text-white')
                ui.label(str(completed)).classes('text-h4 text-white')
                ui.label('Completed').classes('text-white')
            
            # Running
            with ui.card().classes('p-4 text-center bg-blue'):
                ui.icon('play_circle', size='lg').classes('text-white')
                ui.label(str(running)).classes('text-h4 text-white')
                ui.label('Running').classes('text-white')
            
            # Queued
            with ui.card().classes('p-4 text-center bg-grey'):
                ui.icon('schedule', size='lg').classes('text-white')
                ui.label(str(queued)).classes('text-h4 text-white')
                ui.label('Queued').classes('text-white')
            
            # Failed
            with ui.card().classes('p-4 text-center bg-negative'):
                ui.icon('error', size='lg').classes('text-white')
                ui.label(str(failed)).classes('text-h4 text-white')
                ui.label('Failed').classes('text-white')
    
    @ui.refreshable
    async def render_experiments():
        """Render experiments list."""
        ui.label('Experiments').classes('text-h6 mt-4')
        
        queue_entries = await ExperimentQueue.filter(
            batch_id=batch_id
        ).prefetch_related('experiment', 'experiment__robot_a_profile', 'experiment__robot_b_profile').order_by('id')
        
        for entry in queue_entries:
            exp = entry.experiment
            with ui.card().classes('w-full'):
                with ui.row().classes('w-full items-center justify-between'):
                    with ui.column():
                        # Status icon + name
                        status_icon = {
                            'completed': '✓',
                            'running': '🔄',
                            'queued': '⏳',
                            'failed': '⚠',
                            'cancelled': '❌'
                        }.get(entry.status, '?')
                        
                        ui.label(f'{status_icon} {exp.name}').classes('text-subtitle1 font-bold')
                        
                        # Message count
                        msg_count = await ChatMessage.filter(experiment=exp).count()
                        expected = exp.max_turns * 2
                        ui.label(f'{msg_count}/{expected} messages').classes('text-caption text-grey')
                    
                    with ui.row().classes('gap-2'):
                        ui.button('View', on_click=lambda e=exp: ui.navigate.to(f'/experiments/{e.id}')).props('flat size=sm')
                        
                        # Show intelligent error message if failed
                        if entry.status == 'failed' and entry.error_message:
                            badge_text, tooltip_msg, severity = get_friendly_error_message(entry.error_message)
                            ui.badge(badge_text, color=severity).props('outline')
                            ui.icon('help_outline', size='sm').classes(f'text-{severity}').tooltip(tooltip_msg).style('cursor: help')
    
    # Initial render
    await render_stats()
    await render_experiments()
    
    async def refresh_data():
        """Refresh batch statistics and experiments list without scroll reset."""
        # Re-query batch for control button state
        batch_data = await ExperimentBatch.get(id=batch_id)
        
        # Refresh components (preserves scroll position!)
        await render_stats.refresh()
        await render_experiments.refresh()
        
        # Update control buttons
        if can_control:
            if batch_data.is_paused:
                pause_btn.props('color=positive icon=play_arrow')
                pause_btn.text = 'Resume'
            else:
                pause_btn.props('color=warning icon=pause')
                pause_btn.text = 'Pause'
    
    # Batch control functions
    async def toggle_pause():
        """Pause or resume batch."""
        batch_data = await ExperimentBatch.get(id=batch_id)
        
        if batch_data.is_paused:
            # Resume
            batch_data.is_paused = False
            batch_data.paused_at = None
            batch_data.paused_by_id = None
            await batch_data.save()
            ui.notify('Batch resumed', type='positive')
        else:
            # Pause
            batch_data.is_paused = True
            batch_data.paused_at = datetime.now()
            batch_data.paused_by_id = user.id
            await batch_data.save()
            ui.notify('Batch paused - running experiments will continue, but no new ones will start', type='info')
        
        await refresh_data()
    
    async def cancel_batch():
        """Cancel all queued experiments in batch."""
        # Show confirmation dialog
        with ui.dialog() as dialog, ui.card():
            ui.label('❌ Cancel Batch?').classes('text-h6')
            
            # Count experiments that will be cancelled
            queued_count = await ExperimentQueue.filter(batch_id=batch_id, status='queued').count()
            running_count = await ExperimentQueue.filter(batch_id=batch_id, status='running').count()
            
            ui.label(f'{queued_count} queued experiments will be cancelled').classes('text-body1')
            if running_count > 0:
                ui.label(f'{running_count} running experiments will continue to completion').classes('text-caption text-grey')
            ui.label('This action cannot be undone!').classes('text-negative font-bold')
            
            with ui.row().classes('gap-2 mt-4'):
                ui.button('Cancel Action', on_click=dialog.close).props('flat')
                
                async def do_cancel():
                    # Mark all queued as cancelled
                    queued_entries = await ExperimentQueue.filter(batch_id=batch_id, status='queued')
                    for entry in queued_entries:
                        entry.status = 'cancelled'
                        entry.completed_at = datetime.now()
                        await entry.save()
                    
                    # Update batch status
                    batch_data = await ExperimentBatch.get(id=batch_id)
                    batch_data.status = 'cancelled'
                    await batch_data.save()
                    
                    ui.notify(f'Cancelled {len(queued_entries)} queued experiments', type='warning')
                    dialog.close()
                    await refresh_data()
                
                ui.button('Confirm Cancellation', on_click=do_cancel).props('color=negative')
        
        dialog.open()
    
    # Wire up buttons
    if can_control:
        pause_btn.on_click(toggle_pause)
        cancel_btn.on_click(cancel_batch)
    
    # Auto-refresh every 10 seconds (now smooth without scroll reset!)
    ui.timer(10.0, refresh_data)
