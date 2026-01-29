"""
New user onboarding.

Collect display name, create account, wait for approval if needed.
"""

from nicegui import ui, app
from src.database.models import User
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@ui.page('/onboarding')
async def onboarding_page():
    """New user setup."""
    
    # Get email from middleware
    email = app.storage.user.get('user_email')
    
    if not email:
        ui.label('Error: No email found. Please try logging in again.').classes('text-negative')
        return
    
    # Check if user already exists
    existing = await User.get_or_none(email=email)
    if existing:
        if not existing.is_approved:
            # Show waiting for approval message
            with ui.column().classes('w-full max-w-md mx-auto mt-20 gap-6 p-6'):
                ui.label('⏳ Waiting for Approval').classes('text-h4 text-center')
                ui.label(f'Email: {email}').classes('text-subtitle1 text-grey-7 text-center')
                ui.separator()
                ui.label('Your account is pending administrator approval.').classes('text-center')
                ui.label('Please contact your research group admin to approve your access.').classes('text-caption text-grey-6 text-center mt-2')
            return
        
        if not existing.is_active:
            # Deactivated user - show message and allow reactivation request
            with ui.column().classes('w-full max-w-md mx-auto mt-20 gap-6 p-6'):
                ui.label('🚫 Account Deactivated').classes('text-h4 text-center text-negative')
                ui.label(f'Email: {email}').classes('text-subtitle1 text-grey-7 text-center')
                ui.separator()
                
                if existing.reactivation_requested_at:
                    # Already requested reactivation
                    ui.label('✉️ Reactivation Request Pending').classes('text-center font-bold')
                    ui.label(f'Requested on: {existing.reactivation_requested_at.strftime("%b %d, %Y %I:%M %p")}').classes('text-caption text-grey-6 text-center mt-2')
                    ui.label('Your administrator has been notified. Please wait for approval.').classes('text-caption text-grey-6 text-center mt-2')
                else:
                    # Can request reactivation
                    ui.label('Your account has been deactivated.').classes('text-center')
                    if existing.deactivation_reason:
                        ui.label(f'Reason: {existing.deactivation_reason}').classes('text-caption text-grey-6 text-center italic mt-2')
                    
                    ui.label('You can request reactivation below:').classes('text-caption text-grey-6 text-center mt-4')
                    
                    async def request_reactivation():
                        from datetime import datetime
                        existing.reactivation_requested_at = datetime.now()
                        await existing.save()
                        ui.notify('✓ Reactivation request sent to administrator', type='positive')
                        ui.navigate.reload()
                    
                    ui.button('Request Reactivation', on_click=request_reactivation).props('color=primary').classes('mt-4')
            return
        
        # User exists and is approved/active - set session and redirect
        logger.info(f"User {email} already exists and approved, setting session and redirecting")
        app.storage.user['current_user'] = {
            'id': existing.id,
            'email': existing.email,
            'display_name': existing.display_name,
            'role': existing.role,
            'is_admin': existing.is_admin
        }
        ui.navigate.to('/experiments')
        return
    
    # UI Layout
    with ui.column().classes('w-full max-w-md mx-auto mt-20 gap-6 p-6'):
        # Header
        ui.label('Welcome to RRI Orchestrator!').classes('text-h3 text-center')
        ui.label(f'Email: {email}').classes('text-subtitle1 text-grey-7 text-center')
        
        ui.separator()
        
        # Display name input
        ui.label('Enter your display name:').classes('text-subtitle2 font-bold')
        ui.label('This name will be shown when you create experiments.').classes('text-caption text-grey-6 mb-2')
        
        name_input = ui.input(
            'Display Name',
            placeholder='Justin Case',
            validation={
                'Too short': lambda value: value and len(value.strip()) >= 2,
                'Required': lambda value: value and len(value.strip()) > 0
            }
        ).props('outlined').classes('w-full')
        
        ui.space()
        
        # Submit button
        async def create_account():
            """Create user account and redirect."""
            if not name_input.value or len(name_input.value.strip()) < 2:
                ui.notify('Please enter a valid name (at least 2 characters)', type='negative')
                return
            
            # Determine role and approval: first user becomes admin and auto-approved
            user_count = await User.all().count()
            is_first_user = user_count == 0
            role = 'admin' if is_first_user else 'researcher'
            
            try:
                # Create user
                user = await User.create(
                    email=email,
                    display_name=name_input.value.strip(),
                    role=role,
                    is_approved=is_first_user,  # Auto-approve first user (admin)
                    approved_at=datetime.now() if is_first_user else None,
                    last_login=datetime.now()
                )
                
                logger.info(f"Created new user: {user.display_name} ({user.email}) with role={role}, approved={is_first_user}")
                
                if is_first_user:
                    # Update user storage for immediate access
                    app.storage.user['current_user'] = {
                        'id': user.id,
                        'email': user.email,
                        'display_name': user.display_name,
                        'role': user.role,
                        'is_admin': user.is_admin
                    }
                    
                    # Show welcome message
                    ui.notify(
                        f'Welcome, {user.display_name}! You are the first user and have been made an administrator.',
                        type='positive',
                        position='top',
                        timeout=5000
                    )
                    
                    # Redirect to experiments
                    ui.navigate.to('/experiments')
                else:
                    # Show pending approval message
                    ui.notify(
                        'Account created! Waiting for admin approval...',
                        type='info',
                        position='top',
                        timeout=3000
                    )
                    
                    # Reload page to show waiting message
                    ui.navigate.reload()
                
            except Exception as e:
                logger.error(f"Error creating user: {e}")
                ui.notify(f'Error creating account: {str(e)}', type='negative')
        
        ui.button('Continue', on_click=create_account).props('color=primary size=lg').classes('w-full')
        
        # Help text
        ui.label('Note: Your email is verified by Cloudflare Zero Trust.').classes('text-caption text-grey-6 text-center mt-4')
