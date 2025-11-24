"""
Database models for the RRI Orchestrator.

This module defines all data structures using Tortoise ORM, which provides
async database operations with PostgreSQL.
"""

from datetime import datetime
from typing import Optional

from tortoise import fields
from tortoise.models import Model


class User(Model):
    """
    User accounts for accessing the orchestrator.
    
    Stores authentication information and user preferences.
    """
    
    id = fields.IntField(pk=True)
    username = fields.CharField(max_length=50, unique=True, index=True)
    email = fields.CharField(max_length=255, unique=True, index=True)
    hashed_password = fields.CharField(max_length=255)
    full_name = fields.CharField(max_length=100, null=True)
    is_active = fields.BooleanField(default=True)
    is_admin = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)
    last_login = fields.DatetimeField(null=True)
    
    # Relationships
    experiments: fields.ReverseRelation["Experiment"]
    
    class Meta:
        table = "users"
    
    def __str__(self) -> str:
        return f"User({self.username})"


class Experiment(Model):
    """
    Research experiments tracking robot interaction sessions.
    
    Each experiment represents a research session with specific parameters
    and can contain multiple conversation threads.
    """
    
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=200)
    description = fields.TextField(null=True)
    created_by = fields.ForeignKeyField(
        "models.User",
        related_name="experiments",
        on_delete=fields.CASCADE
    )
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    is_active = fields.BooleanField(default=True)
    
    # Experiment parameters
    robot_a_persona = fields.CharField(max_length=100, null=True)
    robot_b_persona = fields.CharField(max_length=100, null=True)
    ai_provider = fields.CharField(max_length=50, default="gemini")
    temperature = fields.FloatField(default=0.7)
    max_tokens = fields.IntField(default=4096)
    
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
    
    id = fields.IntField(pk=True)
    experiment = fields.ForeignKeyField(
        "models.Experiment",
        related_name="messages",
        on_delete=fields.CASCADE
    )
    role = fields.CharField(max_length=20)  # "user", "assistant", "system"
    content = fields.TextField()
    created_at = fields.DatetimeField(auto_now_add=True)
    
    # Metadata
    token_count = fields.IntField(null=True)
    model_used = fields.CharField(max_length=100, null=True)
    response_time_ms = fields.IntField(null=True)
    
    class Meta:
        table = "chat_messages"
        ordering = ["created_at"]
    
    def __str__(self) -> str:
        content_preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"Message({self.role}: {content_preview})"


class ConversationSummary(Model):
    """
    Summarized conversation history for context window management.
    
    When conversations exceed the maximum context length, older messages
    are summarized to preserve the essential information while reducing
    token usage.
    """
    
    id = fields.IntField(pk=True)
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
    
    id = fields.IntField(pk=True)
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
    
    class Meta:
        table = "robot_profiles"
        ordering = ["name"]
    
    def __str__(self) -> str:
        return f"RobotProfile({self.name})"
