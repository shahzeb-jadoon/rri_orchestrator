"""
Authentication middleware for Cloudflare Zero Trust integration.
"""

from datetime import datetime
from nicegui import app
from src.database.models import User
import logging

logger = logging.getLogger(__name__)


async def get_current_user(request):
    """
    Extract user from Cloudflare header and get/create user record.
    
    Returns:
        User object if authenticated, None if new user needs onboarding
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
        user.last_login = datetime.now()
        await user.save(update_fields=['last_login'])
        logger.info(f"User {user.display_name} logged in")
        return user
    else:
        logger.info(f"New user detected: {email}")
        return None


@app.middleware('http')
async def auth_middleware(request, call_next):
    """
    Attach user information to request and browser storage.
    """
    # Skip static files
    if request.url.path.startswith('/static') or request.url.path.startswith('/_nicegui'):
        return await call_next(request)
    
    user = await get_current_user(request)
    email = request.headers.get('Cf-Access-Authenticated-User-Email')
    if not email:
        email = request.headers.get('X-Dev-Email', 'dev@rit.edu')
    
    # Attach to request state
    request.state.user = user
    request.state.user_email = email
    
    # Store in browser storage
    if user:
        app.storage.browser['current_user'] = {
            'id': user.id,
            'email': user.email,
            'display_name': user.display_name,
            'role': user.role,
            'is_admin': user.is_admin
        }
    else:
        app.storage.browser['current_user'] = None
        app.storage.browser['user_email'] = email
    
    response = await call_next(request)
    return response
