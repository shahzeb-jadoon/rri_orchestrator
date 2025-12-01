"""
Batch executor for running queued experiments.

Automatically processes experiment queue and runs experiments
in background without UI dependency.
"""

import asyncio
import signal
from datetime import datetime
from typing import Optional

from src.database import Experiment, ExperimentBatch, ExperimentQueue, RobotProfile
from src.ai.conversation import orchestrate_conversation_turn
from src.utils.logger import logger


class BatchExecutor:
    """Background worker for executing queued experiments."""
    
    def __init__(self):
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        
    async def start(self):
        """Start the executor background worker."""
        if self._running:
            logger.warning("BatchExecutor already running")
            return
        
        self._running = True
        self._task = asyncio.create_task(self._run())
        logger.info("BatchExecutor started")
        
    async def stop(self):
        """Stop the executor gracefully."""
        if not self._running:
            return
        
        logger.info("Stopping BatchExecutor...")
        self._running = False
        self._shutdown_event.set()
        
        if self._task:
            await self._task
        
        logger.info("BatchExecutor stopped")
    
    async def _run(self):
        """Main executor loop."""
        # Reset any experiments stuck in 'running' state from previous server run
        await self._reset_stuck_experiments()
        
        while self._running:
            try:
                await self._process_queue()
                
                # Wait before next polling cycle (avoid tight loop)
                try:
                    await asyncio.wait_for(self._shutdown_event.wait(), timeout=5.0)
                    break  # Shutdown requested
                except asyncio.TimeoutError:
                    continue  # Continue polling
                    
            except Exception as e:
                logger.error(f"Error in executor loop: {e}", exc_info=True)
                await asyncio.sleep(5)  # Back off on error
    
    async def _reset_stuck_experiments(self):
        """Reset experiments that were running when server stopped."""
        stuck_count = await ExperimentQueue.filter(status='running').update(status='queued')
        if stuck_count > 0:
            logger.info(f"Reset {stuck_count} stuck experiments from 'running' to 'queued'")
    
    async def _process_queue(self):
        """Process all pending batches and their queued experiments."""
        # Get all batches that have queued work
        batches = await ExperimentBatch.filter(
            status__in=['pending', 'running'],
            is_paused=False  # Skip paused batches
        ).prefetch_related('created_by')
        
        for batch in batches:
            try:
                await self._process_batch(batch)
            except Exception as e:
                logger.error(f"Error processing batch {batch.id} ({batch.name}): {e}", exc_info=True)
    
    async def _process_batch(self, batch: ExperimentBatch):
        """Process a single batch with concurrency control."""
        # Get queued experiments for this batch
        queued = await ExperimentQueue.filter(
            batch=batch,
            status='queued'
        ).prefetch_related('experiment', 'experiment__robot_a_profile', 'experiment__robot_b_profile')
        
        if not queued:
            # Check if batch is complete
            total = await ExperimentQueue.filter(batch=batch).count()
            completed = await ExperimentQueue.filter(batch=batch, status='completed').count()
            
            if total > 0 and completed == total:
                # All experiments done
                batch.status = 'completed'
                batch.completed_at = datetime.now()
                await batch.save()
                logger.info(f"Batch {batch.id} ({batch.name}) completed: {completed}/{total} experiments")
            
            return
        
        # Update batch to running if not already
        if batch.status == 'pending':
            batch.status = 'running'
            batch.started_at = datetime.now()
            await batch.save()
            logger.info(f"Starting batch {batch.id} ({batch.name}): {len(queued)} experiments queued")
        
        # Get currently running experiments for this batch
        running = await ExperimentQueue.filter(batch=batch, status='running').count()
        
        # Calculate how many we can start
        max_concurrent = batch.max_concurrent or 5
        available_slots = max(0, max_concurrent - running)
        
        if available_slots == 0:
            # Already at max concurrency
            return
        
        # Start experiments up to available slots
        experiments_to_start = queued[:available_slots]
        
        tasks = []
        for queue_entry in experiments_to_start:
            task = asyncio.create_task(self._run_experiment(queue_entry))
            tasks.append(task)
        
        # Don't wait for completion - let them run in background
        # They'll update their own statuses when done
    
    async def _run_experiment(self, queue_entry: ExperimentQueue):
        """Run a single queued experiment to completion."""
        experiment = queue_entry.experiment
        
        try:
            # Pre-flight checks
            if not await self._preflight_check(experiment):
                queue_entry.status = 'failed'
                queue_entry.error_message = 'Pre-flight check failed'
                await queue_entry.save()
                return
            
            # Mark as running
            queue_entry.status = 'running'
            queue_entry.started_at = datetime.now()
            await queue_entry.save()
            
            logger.info(f"Starting experiment {experiment.id} ({experiment.name})")
            
            # Check if experiment already has messages (manually run or previously executed)
            from src.database import ChatMessage
            existing_messages = await ChatMessage.filter(experiment=experiment).count()
            
            # max_turns represents conversation exchanges (robot pair turns)
            # Each exchange = 2 messages (one from each robot)
            max_turns = experiment.max_turns or 10
            total_messages_needed = max_turns * 2
            
            if existing_messages >= total_messages_needed:
                logger.info(f"Experiment {experiment.id} already has {existing_messages} messages (needs {total_messages_needed}), skipping")
                queue_entry.status = 'completed'
                queue_entry.completed_at = datetime.now()
                await queue_entry.save()
                return
            
            # Calculate how many individual turns (messages) still needed
            # Each orchestrate_conversation_turn() call creates ONE message
            turns_to_run = total_messages_needed - existing_messages
            
            logger.info(f"Experiment {experiment.id} has {existing_messages}/{total_messages_needed} messages, running {turns_to_run} more turns")
            
            # Determine starting robot based on existing message count
            # If even number of messages, robot_a starts; if odd, robot_b starts
            current_turn = 0
            
            while current_turn < turns_to_run:
                # Determine which robot speaks based on total message count
                total_messages_so_far = existing_messages + current_turn
                initiating_robot = 'robot_a' if total_messages_so_far % 2 == 0 else 'robot_b'
                
                # First turn of experiment (no existing messages) gets initial prompt
                initial_prompt = experiment.initial_prompt if existing_messages == 0 and current_turn == 0 else None
                
                try:
                    await orchestrate_conversation_turn(
                        experiment=experiment,
                        initiating_robot=initiating_robot,
                        initial_prompt=initial_prompt
                    )
                    current_turn += 1
                    
                except Exception as e:
                    logger.error(f"Error in experiment {experiment.id} turn {current_turn}: {e}", exc_info=True)
                    # Mark as failed
                    queue_entry.status = 'failed'
                    queue_entry.error_message = str(e)[:500]
                    queue_entry.completed_at = datetime.now()
                    await queue_entry.save()
                    return
            
            # Success - mark as completed
            queue_entry.status = 'completed'
            queue_entry.completed_at = datetime.now()
            await queue_entry.save()
            
            total_messages = await ChatMessage.filter(experiment=experiment).count()
            logger.info(f"Completed experiment {experiment.id} ({experiment.name}): {total_messages} messages ({total_messages//2} turns)")
            
        except Exception as e:
            logger.error(f"Fatal error running experiment {experiment.id}: {e}", exc_info=True)
            queue_entry.status = 'failed'
            queue_entry.error_message = str(e)[:500]
            queue_entry.completed_at = datetime.now()
            await queue_entry.save()
    
    async def _preflight_check(self, experiment: Experiment) -> bool:
        """Verify experiment is ready to run."""
        try:
            # Ensure experiment is still active
            if not experiment.is_active:
                logger.warning(f"Experiment {experiment.id} is not active")
                return False
            
            # Verify robot profiles exist
            await experiment.fetch_related('robot_a_profile', 'robot_b_profile')
            
            if not experiment.robot_a_profile or not experiment.robot_b_profile:
                logger.error(f"Experiment {experiment.id} missing robot profiles")
                return False
            
            # Verify API keys are configured
            from src.config import Settings
            settings = Settings()
            
            # Check based on robot providers
            robot_a_provider = experiment.robot_a_profile.ai_provider
            robot_b_provider = experiment.robot_b_profile.ai_provider
            
            if robot_a_provider == 'openai' or robot_b_provider == 'openai':
                if not settings.openai_api_key:
                    logger.error(f"OpenAI API key not configured for experiment {experiment.id}")
                    return False
            
            if robot_a_provider == 'gemini' or robot_b_provider == 'gemini':
                if not settings.gemini_api_key:
                    logger.error(f"Gemini API key not configured for experiment {experiment.id}")
                    return False
            
            logger.info(f"Pre-flight check passed for experiment {experiment.id}")
            return True
            
        except Exception as e:
            logger.error(f"Pre-flight check failed for experiment {experiment.id}: {e}")
            return False


# Global executor instance
_executor: Optional[BatchExecutor] = None


async def start_executor():
    """Start the global batch executor."""
    global _executor
    if _executor is None:
        _executor = BatchExecutor()
    await _executor.start()


async def stop_executor():
    """Stop the global batch executor."""
    global _executor
    if _executor:
        await _executor.stop()


def get_executor() -> Optional[BatchExecutor]:
    """Get the global executor instance."""
    return _executor
