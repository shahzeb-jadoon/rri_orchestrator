"""
Conversation summarization for context window management.

Uses GPT-4o-mini to create concise summaries of older messages.
"""

from typing import List
from litellm import acompletion
from src.database.models import ChatMessage
from src.utils.logger import logger


async def summarize_messages(
    messages: List[ChatMessage],
    count: int = 5
) -> str:
    """
    Summarize oldest N messages into a concise summary.
    
    Args:
        messages: List of ChatMessage objects to summarize
        count: Number of oldest messages to summarize
        
    Returns:
        Summary text (100-200 words)
    """
    if not messages or count <= 0:
        return ""
    
    # Take only the specified count
    messages_to_summarize = messages[:min(count, len(messages))]
    
    # Build prompt
    prompt = f"Summarize the following {len(messages_to_summarize)} messages from a conversation between two AI agents. Be concise (100-200 words) and capture key points:\n\n"
    
    for msg in messages_to_summarize:
        prompt += f"{msg.robot_name}: {msg.content}\n\n"
    
    try:
        # Use GPT-4o-mini for cost-effective summarization
        response = await acompletion(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": prompt
            }],
            max_tokens=250,
            temperature=0.3  # Lower temperature for consistent summaries
        )
        
        summary = response.choices[0].message.content
        logger.info(f"Summarized {len(messages_to_summarize)} messages into {len(summary)} characters")
        
        return summary
        
    except Exception as e:
        logger.error(f"Failed to summarize messages: {e}")
        # Fallback: simple concatenation
        return f"[Summary of {len(messages_to_summarize)} earlier messages]"
