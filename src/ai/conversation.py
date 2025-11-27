"""
Conversation Orchestration.

This module manages multi-turn conversations between two robots,
coordinating message generation and database storage.
"""

from typing import List, Dict, Optional
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
    initiating_robot: str = "robot_a",
    initial_prompt: Optional[str] = None
) -> ChatMessage:
    """
    Execute one conversation turn.
    
    Args:
        experiment: Experiment to run
        initiating_robot: "robot_a" or "robot_b"
        initial_prompt: Optional prompt for first turn only
        
    Returns:
        Created ChatMessage
    """
    await experiment.fetch_related("robot_a_profile", "robot_b_profile")
    
    active_robot = (
        experiment.robot_a_profile if initiating_robot == "robot_a"
        else experiment.robot_b_profile
    )
    
    logger.info(
        f"Orchestrating turn for {initiating_robot} ({active_robot.name}) "
        f"in experiment '{experiment.name}'"
    )
    
    # Build conversation history
    messages = await ChatMessage.filter(experiment=experiment).order_by("created_at")
    
    conversation_history = []
    
    if not messages and initial_prompt:
        conversation_history.append({
            "role": "user",
            "content": initial_prompt
        })
    else:
        # Transform roles: each robot sees itself as assistant, other as user
        for msg in messages:
            if msg.robot_name == initiating_robot:
                conversation_history.append({
                    "role": "assistant",
                    "content": msg.content
                })
            else:
                conversation_history.append({
                    "role": "user",
                    "content": msg.content
                })
    
    # Generate response
    try:
        response = await generate_robot_response(
            robot_profile=active_robot,
            conversation_history=conversation_history
        )
    except Exception as e:
        logger.error(f"Failed to generate response for {active_robot.name}: {e}")
        raise
    
    # Determine which robot this is
    robot_identifier = initiating_robot  # "robot_a" or "robot_b"
    
    # Save to database with detailed tracking
    message = await ChatMessage.create(
        experiment=experiment,
        role="assistant",
        content=response["content"],
        model_used=response["model_used"],
        token_count=response["tokens_used"],
        input_tokens=response["input_tokens"],
        output_tokens=response["output_tokens"],
        cost_usd=response["cost_usd"],
        response_time_ms=response["response_time_ms"],
        robot_name=robot_identifier,
        robot_provider=response["robot_provider"]
    )
    
    logger.info(
        f"Turn complete: {message.token_count} tokens "
        f"(in: {message.input_tokens}, out: {message.output_tokens}), "
        f"${message.cost_usd:.4f}, {message.response_time_ms}ms"
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
