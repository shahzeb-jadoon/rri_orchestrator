"""
Tests for batch experiment models.

This test file covers the ExperimentBatch and ExperimentQueue models,
ensuring database operations work correctly for batch automation features.
"""

import pytest
from datetime import datetime

from src.database import User, Experiment, ExperimentBatch, ExperimentQueue, RobotProfile


@pytest.mark.asyncio
async def test_create_experiment_batch(init_test_db):
    """Test creating a batch of experiments."""
    # Create user who will own the batch
    user = await User.create(
        email="researcher@rit.edu",
        display_name="Test Researcher",
        role="researcher"
    )
    
    # Create a batch
    batch = await ExperimentBatch.create(
        name="Test Batch",
        description="Testing batch creation",
        created_by=user,
        total_experiments=10,
        max_concurrent=5
    )
    
    assert batch.id is not None
    assert batch.name == "Test Batch"
    assert batch.status == "pending"
    assert batch.total_experiments == 10
    assert batch.experiments_completed == 0
    assert batch.created_by_id == user.id


@pytest.mark.asyncio
async def test_batch_with_experiments(init_test_db):
    """Test creating experiments linked to a batch."""
    # Setup
    user = await User.create(
        email="researcher@rit.edu",
        display_name="Test Researcher",
        role="researcher"
    )
    
    batch = await ExperimentBatch.create(
        name="Multi-Experiment Batch",
        created_by=user,
        total_experiments=3
    )
    
    # Create experiments in batch
    experiments = []
    for i in range(3):
        exp = await Experiment.create(
            name=f"Experiment {i+1}",
            created_by=user,
            batch=batch,
            batch_index=i
        )
        experiments.append(exp)
    
    # Verify relationships
    batch_with_experiments = await ExperimentBatch.get(id=batch.id).prefetch_related("experiments")
    linked_experiments = await batch_with_experiments.experiments.all()
    
    assert len(linked_experiments) == 3
    assert all(exp.batch_id == batch.id for exp in linked_experiments)
    
    # Sort by batch_index for assertion
    sorted_experiments = sorted(linked_experiments, key=lambda e: e.batch_index)
    assert [exp.batch_index for exp in sorted_experiments] == [0, 1, 2]


@pytest.mark.asyncio
async def test_create_queue_entry(init_test_db):
    """Test adding an experiment to the queue."""
    # Setup
    user = await User.create(
        email="researcher@rit.edu",
        display_name="Test Researcher",
        role="researcher"
    )
    
    experiment = await Experiment.create(
        name="Queued Experiment",
        created_by=user
    )
    
    # Add to queue
    queue_entry = await ExperimentQueue.create(
        experiment=experiment,
        priority=0,
        status="queued"
    )
    
    assert queue_entry.id is not None
    assert queue_entry.status == "queued"
    assert queue_entry.priority == 0
    assert queue_entry.experiment_id == experiment.id
    assert queue_entry.batch_id is None  # Manual experiment


@pytest.mark.asyncio
async def test_queue_priority_ordering(init_test_db):
    """Test that queue entries respect priority ordering."""
    # Setup
    user = await User.create(
        email="researcher@rit.edu",
        display_name="Test Researcher",
        role="researcher"
    )
    
    # Create experiments with different priorities
    exp_low = await Experiment.create(name="Low Priority", created_by=user)
    exp_high = await Experiment.create(name="High Priority", created_by=user)
    exp_normal = await Experiment.create(name="Normal Priority", created_by=user)
    
    # Add to queue with different priorities
    await ExperimentQueue.create(experiment=exp_low, priority=0)
    await ExperimentQueue.create(experiment=exp_high, priority=10)  # Should be first
    await ExperimentQueue.create(experiment=exp_normal, priority=5)
    
    # Fetch queue in order
    queue = await ExperimentQueue.all().prefetch_related("experiment")
    
    # Verify ordering (highest priority first)
    assert len(queue) == 3
    assert queue[0].experiment.name == "High Priority"
    assert queue[1].experiment.name == "Normal Priority"
    assert queue[2].experiment.name == "Low Priority"


@pytest.mark.asyncio
async def test_batch_status_tracking(init_test_db):
    """Test updating batch status and progress counters."""
    # Create batch
    user = await User.create(
        email="researcher@rit.edu",
        display_name="Test Researcher",
        role="researcher"
    )
    
    batch = await ExperimentBatch.create(
        name="Status Test Batch",
        created_by=user,
        total_experiments=5
    )
    
    # Update status to running
    batch.status = "running"
    batch.started_at = datetime.now()
    await batch.save()
    
    # Simulate completing experiments
    batch.experiments_completed = 3
    batch.experiments_failed = 1
    await batch.save(update_fields=["experiments_completed", "experiments_failed"])
    
    # Verify updates
    updated_batch = await ExperimentBatch.get(id=batch.id)
    assert updated_batch.status == "running"
    assert updated_batch.experiments_completed == 3
    assert updated_batch.experiments_failed == 1
    assert updated_batch.started_at is not None


@pytest.mark.asyncio
async def test_queue_with_batch(init_test_db):
    """Test queue entries linked to a batch."""
    # Setup
    user = await User.create(
        email="researcher@rit.edu",
        display_name="Test Researcher",
        role="researcher"
    )
    
    batch = await ExperimentBatch.create(
        name="Batch Queue Test",
        created_by=user,
        total_experiments=2
    )
    
    # Create experiments in batch
    exp1 = await Experiment.create(name="Batch Exp 1", created_by=user, batch=batch)
    exp2 = await Experiment.create(name="Batch Exp 2", created_by=user, batch=batch)
    
    # Add to queue
    queue1 = await ExperimentQueue.create(experiment=exp1, batch=batch)
    queue2 = await ExperimentQueue.create(experiment=exp2, batch=batch)
    
    # Verify batch relationship
    assert queue1.batch_id == batch.id
    assert queue2.batch_id == batch.id
    
    # Fetch queue entries for this batch
    batch_queue = await ExperimentQueue.filter(batch=batch).all()
    assert len(batch_queue) == 2
