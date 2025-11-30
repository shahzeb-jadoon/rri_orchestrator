"""
Onboarding page for first-time users.

Collects display name and creates user account with appropriate role.
"""

from nicegui import ui, app
from src.database.models import User
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@ui.page('/onboarding')
async def onboarding_page():
    """First-time user setup page."""
    
    # Get email from browser storage (set by middleware)
    email = app.storage.browser.get('user_email')
    
    if not email:
        ui.label('Error: No email found. Please try logging in again.').classes('text-negative')
        return
    
    # Check if user already exists (shouldn't happen, but just in case)
    existing = await User.get_or_none(email=email)
    if existing:
        logger.info(f"User {email} already exists, redirecting to experiments")
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
        
        display_name_input = ui.input(
            placeholder='e.g., Shahzeb Jadoon',
            validation={
                'Too short': lambda value: value and len(value.strip()) >= 2,
                'Required': lambda value: value and len(value.strip()) > 0
            }
        ).props('outlined').classes('w-full')
        
        ui.space()
        
        # Submit button
        async def create_account():
            """Create user account and redirect."""
            if not display_name_input.value or len(display_name_input.value.strip()) < 2:
                ui.notify('Please enter a valid name (at least 2 characters)', type='negative')
                return
            
            # Determine role: first user becomes admin
            user_count = await User.all().count()
            role = 'admin' if user_count == 0 else 'researcher'
            
            try:
                # Create user
                user = await User.create(
                    email=email,
                    display_name=display_name_input.value.strip(),
                    role=role,
                    last_login=datetime.now()
                )
                
                logger.info(f"Created new user: {user.display_name} ({user.email}) with role={role}")
                
                # Update browser storage
                app.storage.browser['current_user'] = {
                    'id': user.id,
                    'email': user.email,
                    'display_name': user.display_name,
                    'role': user.role,
                    'is_admin': user.is_admin
                }
                
                # Show welcome message
                if role == 'admin':
                    ui.notify(
                        f'Welcome, {user.display_name}! You are the first user and have been made an administrator.',
                        type='positive',
                        position='top',
                        timeout=5000
                    )
                else:
                    ui.notify(
                        f'Welcome, {user.display_name}!',
                        type='positive',
                        position='top'
                    )
                
                # Redirect to experiments
                ui.navigate.to('/experiments')
                
            except Exception as e:
                logger.error(f"Error creating user: {e}")
                ui.notify(f'Error creating account: {str(e)}', type='negative')
        
        ui.button('Continue', on_click=create_account).props('color=primary size=lg').classes('w-full')
        
        # Help text
        ui.label('Note: Your email is verified by Cloudflare Zero Trust.').classes('text-caption text-grey-6 text-center mt-4')
