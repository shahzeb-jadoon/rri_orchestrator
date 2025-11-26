"""
Conversation Orchestration.

This module manages multi-turn conversations between two robots,
coordinating message generation and database storage.
"""

from typing import List, Dict
from src.database.models import Experiment, ChatMessage, RobotProfile
from src.ai.llm_service import generate_robot_response
from src.utils.logger import logger


async def get_conversation_history(
    experiment: Experiment,
    max_messages: int = None
) -> List[Dict[str, str]]:
    """
    Get conversation history for an experiment in OpenAI format.
    
    Args:
        experiment: The experiment to get history for
        max_messages: Maximum number of messages to retrieve
        
    Returns:
        List of messages in format [{"role": "user"/"assistant", "content": "..."}]
    """
    max_messages = max_messages or 50  # Default from settings
    
    # Get recent messages
    messages = await ChatMessage.filter(
        experiment=experiment
    ).order_by("-created_at").limit(max_messages)
    
    # Reverse to get chronological order
    messages = list(reversed(messages))
    
    # Convert to OpenAI format
    history = []
    for msg in messages:
        history.append({
            "role": msg.role,
            "content": msg.content
        })
    
    return history


async def orchestrate_conversation_turn(
    experiment: Experiment,
    initiating_robot: str,
    initial_prompt: str = None
) -> ChatMessage:
    """
    Execute one turn of conversation where the specified robot responds.
    
    Args:
        experiment: The experiment containing robot profiles
        initiating_robot: Which robot should speak ("robot_a" or "robot_b")
        initial_prompt: Optional prompt to start the conversation
        
    Returns:
        The created ChatMessage
        
    Raises:
        ValueError: If robot profiles not configured or invalid robot specified
    """
    # Load robot profiles
    await experiment.fetch_related("robot_a_profile", "robot_b_profile")
    
    if not experiment.robot_a_profile or not experiment.robot_b_profile:
        raise ValueError(
            f"Experiment '{experiment.name}' does not have robot profiles configured"
        )
    
    # Select active robot
    if initiating_robot == "robot_a":
        active_robot = experiment.robot_a_profile
    elif initiating_robot == "robot_b":
        active_robot = experiment.robot_b_profile
    else:
        raise ValueError(
            f"Invalid robot specifier: {initiating_robot}. "
            f"Must be 'robot_a' or 'robot_b'"
        )
    
    logger.info(
        f"Orchestrating turn for {initiating_robot} ({active_robot.name}) "
        f"in experiment '{experiment.name}'"
    )
    
    # Get conversation history
    history = await get_conversation_history(experiment)
    
    # Add initial prompt if this is the first message
    if initial_prompt and not history:
        history.append({
            "role": "user",
            "content": initial_prompt
        })
    
    # Generate response using robot's AI provider
    try:
        response = await generate_robot_response(
            robot_profile=active_robot,
            conversation_history=history
        )
    except Exception as e:
        logger.error(f"Failed to generate response for {active_robot.name}: {e}")
        raise
    
    # Save to database
    message = await ChatMessage.create(
        experiment=experiment,
        role="assistant",
        content=response["content"],
        model_used=response["model_used"],
        token_count=response["tokens_used"],
        response_time_ms=response["response_time_ms"]
    )
    
    logger.info(
        f"Turn complete: {message.token_count} tokens, "
        f"{message.response_time_ms}ms"
    )
    
    return message


async def run_multi_turn_conversation(
    experiment: Experiment,
    num_turns: int,
    initial_prompt: str,
    start_with: str = "robot_a"
) -> List[ChatMessage]:
    """
    Run a multi-turn conversation between two robots.
    
    Args:
        experiment: The experiment to run
        num_turns: Number of conversation turns
        initial_prompt: Starting prompt for the conversation
        start_with: Which robot starts ("robot_a" or "robot_b")
        
    Returns:
        List of created ChatMessages
    """
    messages = []
    current_robot = start_with
    
    logger.info(
        f"Starting {num_turns}-turn conversation in experiment '{experiment.name}'"
    )
    
    for turn in range(num_turns):
        logger.info(f"Turn {turn + 1}/{num_turns}: {current_robot}")
        
        # Generate message
        message = await orchestrate_conversation_turn(
            experiment=experiment,
            initiating_robot=current_robot,
            initial_prompt=initial_prompt if turn == 0 else None
        )
        
        messages.append(message)
        
        # Alternate robots
        current_robot = "robot_b" if current_robot == "robot_a" else "robot_a"
    
    logger.info(
        f"Conversation complete: {len(messages)} messages generated"
    )
    
    return messages
