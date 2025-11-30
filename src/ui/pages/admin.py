"""
Admin panel for user management.

View, approve, and deactivate users. Change roles.
"""

from nicegui import ui
from starlette.requests import Request
from datetime import datetime

from src.database import User, Experiment, ExperimentBatch
from src.ui.components import create_navbar


@ui.page('/admin/users')
async def admin_users_page(request: Request):
    """Admin-only user management."""
    
    create_navbar()
    
    # Verify admin access
    user = getattr(request.state, 'user', None)
    
    if not user or not user.is_admin:
        ui.label('🚫 Access Denied').classes('text-h4 text-negative')
        ui.label('Only administrators can access this page.').classes('text-subtitle1')
        return
    
    # Page header
    ui.label('User Management').classes('text-h4')
    ui.label('Approve new users and manage team access').classes('text-subtitle1 text-grey-7')
    
    ui.space()
    
    # Fetch all users
    all_users = await User.all().order_by('-created_at')
    
    # Separate into categories
    pending_users = [u for u in all_users if not u.is_approved]
    active_users = [u for u in all_users if u.is_approved and u.is_active]
    deactivated_users = [u for u in all_users if not u.is_active]
    
    # Stats cards
    with ui.row().classes('w-full gap-4 mb-6'):
        with ui.card().classes('p-4'):
            ui.label('Active Users').classes('text-caption text-grey-7')
            ui.label(str(len(active_users))).classes('text-h4 font-bold text-positive')
        
        with ui.card().classes('p-4 bg-orange-100'):
            ui.label('Pending Approval').classes('text-caption text-grey-7')
            ui.label(str(len(pending_users))).classes('text-h4 font-bold text-orange')
        
        with ui.card().classes('p-4'):
            ui.label('Deactivated').classes('text-caption text-grey-7')
            ui.label(str(len(deactivated_users))).classes('text-h4 font-bold text-grey')
    
    # Pending approvals (priority)
    if pending_users:
        ui.label('⏳ Pending Approval').classes('text-h5 font-bold mt-6 mb-2')
        
        for pending_user in pending_users:
            with ui.card().classes('w-full p-4 bg-orange-50'):
                with ui.row().classes('w-full items-center justify-between'):
                    with ui.column().classes('gap-1'):
                        ui.label(pending_user.display_name).classes('text-h6 font-bold')
                        ui.label(pending_user.email).classes('text-caption text-grey-7')
                        ui.label(f'Requested: {pending_user.created_at.strftime("%b %d, %Y %I:%M %p")}').classes('text-caption text-grey-6')
                    
                    with ui.row().classes('gap-2'):
                        async def approve_user(u=pending_user):
                            u.is_approved = True
                            u.approved_by = user
                            u.approved_at = datetime.now()
                            await u.save()
                            ui.notify(f'✓ Approved {u.display_name}', type='positive')
                            ui.navigate.reload()
                        
                        async def reject_user(u=pending_user):
                            await u.delete()
                            ui.notify(f'✗ Rejected {u.display_name}', type='warning')
                            ui.navigate.reload()
                        
                        ui.button('✓ Approve', on_click=approve_user).props('color=positive')
                        ui.button('✗ Reject', on_click=reject_user).props('flat color=negative')
    
    # Active users
    ui.label('✓ Active Users').classes('text-h5 font-bold mt-6 mb-2')
    
    for active_user in active_users:
        # Count their contributions
        exp_count = await Experiment.filter(created_by=active_user).count()
        batch_count = await ExperimentBatch.filter(created_by=active_user).count()
        
        with ui.card().classes('w-full p-4'):
            with ui.row().classes('w-full items-center justify-between'):
                with ui.column().classes('gap-1 flex-grow'):
                    with ui.row().classes('items-center gap-2'):
                        ui.label(active_user.display_name).classes('text-h6 font-bold')
                        role_color = 'red' if active_user.role == 'admin' else 'blue'
                        ui.badge(active_user.role.upper(), color=role_color).classes('text-xs')
                    
                    ui.label(active_user.email).classes('text-caption text-grey-7')
                    
                    with ui.row().classes('gap-4 mt-2'):
                        ui.label(f'📊 {exp_count} experiments').classes('text-caption')
                        ui.label(f'📦 {batch_count} batches').classes('text-caption')
                        if active_user.last_login:
                            ui.label(f'Last login: {active_user.last_login.strftime("%b %d, %Y")}').classes('text-caption text-grey-6')
                
                with ui.row().classes('gap-2'):
                    # Role toggle
                    if active_user.id != user.id:  # Can't change own role
                        async def toggle_role(u=active_user):
                            u.role = 'researcher' if u.role == 'admin' else 'admin'
                            await u.save()
                            ui.notify(f'Changed {u.display_name} to {u.role}', type='info')
                            ui.navigate.reload()
                        
                        ui.button(
                            '👑 Make Admin' if active_user.role == 'researcher' else '📝 Make Researcher',
                            on_click=toggle_role
                        ).props('flat size=sm')
                    
                    # Deactivate
                    if active_user.id != user.id:  # Can't deactivate yourself
                        async def deactivate(u=active_user):
                            with ui.dialog() as dialog, ui.card():
                                ui.label(f'Deactivate {u.display_name}?').classes('text-h6')
                                ui.label('User will lose access but their data will be preserved.').classes('text-caption')
                                
                                reason_input = ui.textarea('Reason (optional)').classes('w-full').props('outlined')
                                
                                async def confirm_deactivate():
                                    u.is_active = False
                                    u.deactivated_at = datetime.now()
                                    u.deactivated_by = user
                                    u.deactivation_reason = reason_input.value
                                    await u.save()
                                    dialog.close()
                                    ui.notify(f'Deactivated {u.display_name}', type='warning')
                                    ui.navigate.reload()
                                
                                with ui.row().classes('w-full justify-end gap-2 mt-4'):
                                    ui.button('Cancel', on_click=dialog.close).props('flat')
                                    ui.button('Deactivate', on_click=confirm_deactivate).props('color=negative')
                            
                            dialog.open()
                        
                        ui.button('🚫 Deactivate', on_click=deactivate).props('flat size=sm color=negative')
    
    # Deactivated users
    if deactivated_users:
        ui.label('🚫 Deactivated Users').classes('text-h5 font-bold mt-6 mb-2')
        
        for deact_user in deactivated_users:
            exp_count = await Experiment.filter(created_by=deact_user).count()
            
            with ui.card().classes('w-full p-4 bg-grey-100'):
                with ui.row().classes('w-full items-center justify-between'):
                    with ui.column().classes('gap-1'):
                        ui.label(deact_user.display_name).classes('text-h6 font-bold text-grey-7')
                        ui.label(deact_user.email).classes('text-caption text-grey-6')
                        ui.label(f'{exp_count} experiments preserved').classes('text-caption')
                        if deact_user.deactivation_reason:
                            ui.label(f'Reason: {deact_user.deactivation_reason}').classes('text-caption text-grey-6 italic')
                    
                    with ui.row().classes('gap-2'):
                        async def reactivate(u=deact_user):
                            u.is_active = True
                            u.deactivated_at = None
                            u.deactivated_by = None
                            u.deactivation_reason = None
                            await u.save()
                            ui.notify(f'Reactivated {u.display_name}', type='positive')
                            ui.navigate.reload()
                        
                        ui.button('✓ Reactivate', on_click=reactivate).props('color=positive size=sm')
