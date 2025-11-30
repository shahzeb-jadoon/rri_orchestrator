"""
Cloudflare Zero Trust authentication.
"""

from datetime import datetime
from nicegui import app
from src.database.models import User
import logging

logger = logging.getLogger(__name__)


async def get_current_user(request):
    """
    Get user from Cloudflare header.
    
    Returns User if approved/active, None if pending or new.
    """
    email = request.headers.get('Cf-Access-Authenticated-User-Email')
    
    # Fallback for local dev
    if not email and app.native.main_window is None:
        email = request.headers.get('X-Dev-Email', 'dev@rit.edu')
    
    if not email:
        logger.warning("No email found in request headers")
        return None
    
    user = await User.get_or_none(email=email)
    
    if user:
        # Check if user is approved and active
        if not user.is_approved:
            logger.warning(f"User {user.email} not approved yet")
            return None
        
        if not user.is_active:
            logger.warning(f"User {user.email} has been deactivated")
            return None
        
        user.last_login = datetime.now()
        await user.save(update_fields=['last_login'])
        logger.info(f"User {user.display_name} logged in")
        return user
    else:
        logger.info(f"New user detected: {email}")
        return None


@app.middleware('http')
async def auth_middleware(request, call_next):
    """Attach user to request state."""
    # Skip static files
    if request.url.path.startswith('/static') or request.url.path.startswith('/_nicegui'):
        return await call_next(request)
    
    user = await get_current_user(request)
    email = request.headers.get('Cf-Access-Authenticated-User-Email')
    if not email:
        email = request.headers.get('X-Dev-Email', 'dev@rit.edu')
    
    # Attach to request state (accessible in page functions)
    request.state.user = user
    request.state.user_email = email
    
    # Redirect to onboarding if user needs setup or approval
    # Skip redirect for root path (/) to allow initial landing
    if not user and email and not request.url.path.startswith('/onboarding') and request.url.path != '/':
        # User needs onboarding - send them there
        from starlette.responses import RedirectResponse
        return RedirectResponse(url='/onboarding', status_code=303)
    
    # Store in user storage (request-scoped, safe in middleware)
    if user:
        app.storage.user['current_user'] = {
            'id': user.id,
            'email': user.email,
            'display_name': user.display_name,
            'role': user.role,
            'is_admin': user.is_admin
        }
        app.storage.user['user_email'] = email
    else:
        app.storage.user['current_user'] = None
        app.storage.user['user_email'] = email
    
    response = await call_next(request)
    return response
