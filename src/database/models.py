"""
Database models using Tortoise ORM.

Defines users, experiments, batches, robots, messages, and queues.
"""

from datetime import datetime
from typing import Optional

from tortoise import fields
from tortoise.models import Model


class User(Model):
    """
    User accounts with Cloudflare Zero Trust auth.
    
    First user becomes admin. New users need admin approval.
    """
    
    id = fields.IntField(primary_key=True)
    email = fields.CharField(max_length=255, unique=True, db_index=True)
    display_name = fields.CharField(max_length=100)
    role = fields.CharField(max_length=20, default='researcher')  # admin or researcher
    
    # Access control
    is_active = fields.BooleanField(default=True)
    is_approved = fields.BooleanField(default=False)
    approved_by = fields.ForeignKeyField('models.User', related_name='users_approved', null=True, on_delete=fields.SET_NULL)
    approved_at = fields.DatetimeField(null=True)
    
    # Timestamps
    created_at = fields.DatetimeField(auto_now_add=True)
    last_login = fields.DatetimeField(auto_now=False, null=True)
    
    # Deactivation tracking
    deactivated_at = fields.DatetimeField(null=True)
    deactivated_by = fields.ForeignKeyField('models.User', related_name='users_deactivated', null=True, on_delete=fields.SET_NULL)
    deactivation_reason = fields.TextField(null=True)
    
    # Reactivation request tracking
    reactivation_requested_at = fields.DatetimeField(null=True)
    
    # Relationships
    experiments: fields.ReverseRelation["Experiment"]
    batches: fields.ReverseRelation["ExperimentBatch"]
    robot_profiles: fields.ReverseRelation["RobotProfile"]
    
    class Meta:
        table = "users"
    
    def __str__(self) -> str:
        return f"User({self.display_name} <{self.email}>)"
    
    @property
    def is_admin(self) -> bool:
        """Check if user has admin privileges."""
        return self.role == 'admin'


class Experiment(Model):
    """
    Research experiments tracking robot interaction sessions.
    
    Each experiment represents a research session with specific parameters
    and can contain multiple conversation threads.
    """
    
    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=200)
    description = fields.TextField(null=True)
    created_by = fields.ForeignKeyField(
        "models.User",
        related_name="experiments",
        on_delete=fields.SET_NULL,
        null=True
    )
    created_by_email = fields.CharField(max_length=255, null=True)
    created_by_name = fields.CharField(max_length=100, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    is_active = fields.BooleanField(default=True)
    
    # Deprecated fields (kept for backward compatibility)
    robot_a_persona = fields.CharField(max_length=100, null=True)
    robot_b_persona = fields.CharField(max_length=100, null=True)
    ai_provider = fields.CharField(max_length=50, default="gemini")
    temperature = fields.FloatField(default=0.7)
    max_tokens = fields.IntField(default=4096)
    
    # Robot configuration
    robot_a_profile = fields.ForeignKeyField(
        "models.RobotProfile",
        related_name="experiments_as_robot_a",
        on_delete=fields.SET_NULL,
        null=True
    )
    robot_b_profile = fields.ForeignKeyField(
        "models.RobotProfile",
        related_name="experiments_as_robot_b",
        on_delete=fields.SET_NULL,
        null=True
    )

    # Experiment settings
    initial_prompt = fields.TextField(null=True)
    robot_a_profile_name = fields.CharField(max_length=100, null=True)
    robot_b_profile_name = fields.CharField(max_length=100, null=True)
    max_turns = fields.IntField(default=10)
    
    # Batch automation
    batch = fields.ForeignKeyField(
        "models.ExperimentBatch",
        related_name="experiments",
        on_delete=fields.SET_NULL,
        null=True
    )
    batch_index = fields.IntField(null=True)
    
    # Soft delete for data preservation
    deleted_at = fields.DatetimeField(null=True, default=None)
    deleted_by = fields.ForeignKeyField(
        "models.User",
        related_name="deleted_experiments",
        on_delete=fields.SET_NULL,
        null=True
    )
    
    # Relationships
    messages: fields.ReverseRelation["ChatMessage"]
    summaries: fields.ReverseRelation["ConversationSummary"]
    
    class Meta:
        table = "experiments"
        ordering = ["-created_at"]
    
    def __str__(self) -> str:
        return f"Experiment({self.name})"


class ChatMessage(Model):
    """
    Individual messages in a conversation.
    
    Stores all messages exchanged during an experiment, including both
    user inputs and AI-generated responses.
    """
    
    id = fields.IntField(primary_key=True)
    experiment = fields.ForeignKeyField(
        "models.Experiment",
        related_name="messages",
        on_delete=fields.CASCADE
    )
    role = fields.CharField(max_length=20)  # "user", "assistant", "system"
    content = fields.TextField()
    created_at = fields.DatetimeField(auto_now_add=True)
    
    # AI metadata
    model_used = fields.CharField(max_length=100, null=True)
    
    # Token tracking (split for cost analysis)
    input_tokens = fields.IntField(default=0)  # Prompt/context tokens
    output_tokens = fields.IntField(default=0)  # Response/completion tokens
    token_count = fields.IntField(default=0)  # Total (for backward compatibility)
    
    # Cost and performance
    cost_usd = fields.DecimalField(max_digits=10, decimal_places=6, null=True)
    response_time_ms = fields.IntField(null=True)
    
    # Robot identification (for cost breakdown)
    robot_name = fields.CharField(max_length=100, null=True)  # "robot_a" or "robot_b"
    robot_provider = fields.CharField(max_length=50, null=True)  # "openai", "gemini", etc.
    
    class Meta:
        table = "chat_messages"
        ordering = ["created_at"]
    
    def __str__(self) -> str:
        preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"ChatMessage({self.role}: {preview})"


class ConversationSummary(Model):
    """
    Summarized conversation history for context window management.
    
    When conversations exceed the maximum context length, older messages
    are summarized to preserve the essential information while reducing
    token usage.
    """
    
    id = fields.IntField(primary_key=True)
    experiment = fields.ForeignKeyField(
        "models.Experiment",
        related_name="summaries",
        on_delete=fields.CASCADE
    )
    summary_text = fields.TextField()
    message_range_start = fields.IntField()  # First message ID included
    message_range_end = fields.IntField()    # Last message ID included
    created_at = fields.DatetimeField(auto_now_add=True)
    token_count = fields.IntField(null=True)
    
    class Meta:
        table = "conversation_summaries"
        ordering = ["created_at"]
    
    def __str__(self) -> str:
        return f"Summary(msgs {self.message_range_start}-{self.message_range_end})"


class RobotProfile(Model):
    """
    Predefined robot personas for experiments.
    
    Stores reusable robot personality definitions including system prompts
    and behavioral parameters.
    """
    
    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=100, unique=True)
    description = fields.TextField()
    system_prompt = fields.TextField()
    created_by = fields.ForeignKeyField(
        "models.User",
        related_name="robot_profiles",
        on_delete=fields.SET_NULL,
        null=True
    )
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    is_public = fields.BooleanField(default=False)
    
    # Behavioral parameters
    default_temperature = fields.FloatField(default=0.7)
    personality_traits = fields.JSONField(default=dict)
    
    # AI Configuration (Phase 2: Per-Robot AI Selection)
    ai_provider = fields.CharField(
        max_length=50,
        default="gemini",
        description="AI provider: openai, gemini, anthropic, etc."
    )
    model_name = fields.CharField(
        max_length=100,
        null=True,
        description="Specific model variant: gpt-4o, gemini-2.0-flash, etc."
    )
    
    class Meta:
        table = "robot_profiles"
        ordering = ["name"]
    
    def __str__(self) -> str:
        return f"RobotProfile({self.name})"


class ExperimentBatch(Model):
    """
    A collection of experiments running as a batch.
    
    Batches allow researchers to queue multiple experiments with similar
    configurations, enabling automated testing of different prompts or scenarios.
    """
    
    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=200)
    description = fields.TextField(null=True)
    created_by = fields.ForeignKeyField(
        "models.User",
        related_name="batches",
        on_delete=fields.SET_NULL,
        null=True
    )
    created_by_email = fields.CharField(max_length=255, null=True)
    created_by_name = fields.CharField(max_length=100, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    
    # Batch configuration
    total_experiments = fields.IntField(default=0)
    max_concurrent = fields.IntField(default=5)  # Max experiments running at once
    
    # Status tracking
    status = fields.CharField(max_length=20, default='pending')  # pending, running, paused, completed, failed
    started_at = fields.DatetimeField(null=True)
    completed_at = fields.DatetimeField(null=True)
    scheduled_start = fields.DatetimeField(null=True)  # Optional: schedule batch for future execution
    
    # Progress counters
    experiments_completed = fields.IntField(default=0)
    experiments_failed = fields.IntField(default=0)
    
    # Batch controls
    is_paused = fields.BooleanField(default=False)
    paused_at = fields.DatetimeField(null=True)
    paused_by = fields.ForeignKeyField(
        "models.User",
        related_name="paused_batches",
        on_delete=fields.SET_NULL,
        null=True
    )
    
    # Relationships
    experiments: fields.ReverseRelation["Experiment"]
    
    class Meta:
        table = "experiment_batches"
        ordering = ["-created_at"]
    
    def __str__(self) -> str:
        return f"Batch({self.name}, {self.experiments_completed}/{self.total_experiments})"


class ExperimentQueue(Model):
    """
    Queue for managing experiment execution order.
    
    Experiments are added to the queue and processed based on priority
    and creation time. Manual experiments can jump the queue.
    """
    
    id = fields.IntField(primary_key=True)
    experiment = fields.ForeignKeyField(
        "models.Experiment",
        related_name="queue_entries",
        on_delete=fields.CASCADE
    )
    batch = fields.ForeignKeyField(
        "models.ExperimentBatch",
        related_name="queue_entries",
        on_delete=fields.CASCADE,
        null=True
    )
    
    # Queue management
    status = fields.CharField(max_length=20, default='queued')
    priority = fields.IntField(default=0)
    added_at = fields.DatetimeField(auto_now_add=True)
    started_at = fields.DatetimeField(null=True)
    completed_at = fields.DatetimeField(null=True)
    
    # Error tracking
    error_message = fields.TextField(null=True)
    retry_count = fields.IntField(default=0)
    
    class Meta:
        table = "experiment_queue"
        ordering = ["-priority", "added_at"]  # Higher priority first, then FIFO
    
    def __str__(self) -> str:
        return f"QueueEntry({self.experiment.name}, {self.status})"
