"""
Deleted experiments page with recovery functionality.

Shows soft-deleted experiments that can be recovered or permanently deleted.
"""

from nicegui import ui
from datetime import datetime
from starlette.requests import Request
from src.database.models import Experiment, User
from src.ui.components import create_navbar


@ui.page('/experiments/deleted')
async def deleted_experiments_page(request: Request):
    """View and manage deleted experiments."""
    create_navbar()
    
    # Get current user
    user = getattr(request.state, 'user', None)
    if not user:
        ui.label('Please log in to view deleted experiments').classes('text-negative')
        return
    
    ui.label('🗑️ Deleted Experiments').classes('text-h4')
    ui.label('Recover or permanently delete experiments').classes('text-subtitle1 text-grey')
    
    ui.space()
    
    # Back button
    ui.button('← Back to Experiments', on_click=lambda: ui.navigate.to('/experiments')).props('flat')
    
    ui.space()
    
    # Load deleted experiments based on user role
    if user.is_admin:
        # Admins see all deleted experiments
        deleted_experiments = await Experiment.filter(
            deleted_at__isnull=False
        ).prefetch_related('created_by', 'deleted_by', 'robot_a_profile', 'robot_b_profile').order_by('-deleted_at')
    else:
        # Researchers see only their own deleted experiments
        deleted_experiments = await Experiment.filter(
            deleted_at__isnull=False,
            created_by=user
        ).prefetch_related('created_by', 'deleted_by', 'robot_a_profile', 'robot_b_profile').order_by('-deleted_at')
    
    async def recover_experiment(exp_id: int):
        """Recover a soft-deleted experiment."""
        exp = await Experiment.get(id=exp_id).prefetch_related('created_by')
        
        # Permission check
        if not user.is_admin and exp.created_by_id != user.id:
            ui.notify('Permission denied', type='negative')
            return
        
        # Restore
        exp.deleted_at = None
        exp.deleted_by_id = None
        await exp.save()
        
        ui.notify('Experiment recovered successfully', type='positive')
        ui.navigate.to('/experiments/deleted')
    
    async def permanently_delete(exp_id: int):
        """Permanently delete an experiment (admin only)."""
        if not user.is_admin:
            ui.notify('Admin only', type='negative')
            return
        
        exp = await Experiment.get(id=exp_id)
        
        # Show confirmation dialog
        with ui.dialog() as dialog, ui.card():
            ui.label('⚠️ Permanently Delete Experiment?').classes('text-h6')
            ui.label(f'"{exp.name}"').classes('font-bold')
            ui.label('This action CANNOT be undone! All messages and data will be lost.').classes('text-negative')
            
            with ui.row().classes('gap-2 mt-4'):
                ui.button('Cancel', on_click=dialog.close).props('flat')
                async def do_delete():
                    await Experiment.filter(id=exp_id).delete()
                    ui.notify('Experiment permanently deleted', type='warning')
                    dialog.close()
                    ui.navigate.to('/experiments/deleted')
                
                ui.button('Delete Forever', on_click=do_delete).props('color=negative')
        
        dialog.open()
    
    if not deleted_experiments:
        ui.label('No deleted experiments').classes('text-grey')
        return
    
    # Show deleted experiments
    for exp in deleted_experiments:
        with ui.card().classes('w-full'):
            with ui.row().classes('w-full items-center justify-between'):
                with ui.column().classes('gap-1'):
                    ui.label(exp.name).classes('text-h6')
                    
                    # Show who created and who deleted
                    creator_name = exp.created_by.display_name if exp.created_by else (exp.created_by_name or 'Unknown')
                    deleter_name = exp.deleted_by.display_name if exp.deleted_by else 'Unknown'
                    
                    ui.label(f'Created by: {creator_name}').classes('text-caption text-grey')
                    ui.label(f'Deleted by: {deleter_name} on {exp.deleted_at.strftime("%Y-%m-%d %H:%M")}').classes('text-caption text-orange')
                
                with ui.row().classes('gap-2'):
                    # Recover button (creator or admin)
                    if user.is_admin or exp.created_by_id == user.id:
                        ui.button('↩️ Recover', on_click=lambda e=exp: recover_experiment(e.id)).props('color=positive size=sm')
                    
                    # Permanent delete (admin only)
                    if user.is_admin:
                        ui.button('🗑️ Delete Forever', on_click=lambda e=exp: permanently_delete(e.id)).props('color=negative size=sm')
            
            # Show experiment details
            if exp.robot_a_profile and exp.robot_b_profile:
                ui.label(
                    f'{exp.robot_a_profile.name} vs {exp.robot_b_profile.name}'
                ).classes('text-caption text-grey')
