"""
UI utility functions for consistent user experience.

Shared helper functions used across multiple UI pages.
"""


def get_friendly_error_message(error_text: str) -> tuple[str, str, str]:
    """
    Parse technical error message and return user-friendly version.
    
    Returns:
        tuple: (badge_text, tooltip_message, severity_color)
               severity_color: 'red' (critical), 'orange' (retryable), 'yellow' (warning)
    """
    if not error_text:
        return ('⚠ Failed', 'Experiment failed for unknown reason. Contact administrator.', 'red')
    
    error_lower = error_text.lower()
    
    # Rate limit errors (most common, retryable)
    if 'rate' in error_lower and 'limit' in error_lower:
        if 'gemini' in error_lower:
            return (
                '⏸ Rate Limited',
                '🔄 Gemini API rate limit reached. The batch will automatically retry later. '
                'No action needed - just wait a few minutes.',
                'orange'
            )
        elif 'openai' in error_lower:
            return (
                '⏸ Rate Limited',
                '🔄 OpenAI API rate limit reached. The batch will automatically retry later. '
                'No action needed - just wait a few minutes.',
                'orange'
            )
        else:
            return (
                '⏸ Rate Limited',
                '🔄 API rate limit reached. The experiment will retry automatically. '
                'No action needed - just wait a bit.',
                'orange'
            )
    
    # Authentication/API key errors (admin action needed)
    if 'auth' in error_lower or 'api key' in error_lower or 'unauthorized' in error_lower or '401' in error_text:
        if 'gemini' in error_lower:
            return (
                '🔑 Auth Error',
                '❌ Gemini API key is invalid or missing. Contact admin to update API credentials in settings.',
                'red'
            )
        elif 'openai' in error_lower:
            return (
                '🔑 Auth Error',
                '❌ OpenAI API key is invalid or missing. Contact admin to update API credentials in settings.',
                'red'
            )
        else:
            return (
                '🔑 Auth Error',
                '❌ API authentication failed. Contact admin to check API key configuration.',
                'red'
            )
    
    # Quota/billing errors (admin action needed)
    if 'quota' in error_lower or 'billing' in error_lower or 'exceeded' in error_lower:
        return (
            '💳 Quota Exceeded',
            '❌ API quota or billing limit reached. Contact admin to upgrade API plan or check billing.',
            'red'
        )
    
    # Model not found errors
    if 'model' in error_lower and ('not found' in error_lower or 'does not exist' in error_lower):
        return (
            '🤖 Model Error',
            '❌ AI model not found or unavailable. Contact admin to check robot profile configuration.',
            'red'
        )
    
    # Network/timeout errors (retryable)
    if 'timeout' in error_lower or 'connection' in error_lower or 'network' in error_lower:
        return (
            '🌐 Network Error',
            '🔄 Network connection issue. The batch will retry automatically. '
            'If this persists, contact administrator.',
            'orange'
        )
    
    # Content policy violations
    if 'content' in error_lower and ('policy' in error_lower or 'safety' in error_lower or 'filter' in error_lower):
        return (
            '⚠️ Content Filtered',
            '⚠️ Response blocked by content safety filter. Try rephrasing the prompt or contact admin.',
            'yellow'
        )
    
    # Generic failure - show first 150 chars of error
    preview = error_text[:150] + ('...' if len(error_text) > 150 else '')
    return (
        '⚠ Failed',
        f'Error: {preview}',
        'red'
    )
