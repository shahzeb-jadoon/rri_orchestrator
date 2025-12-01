"""
View Models for reactive UI updates.

These ViewModels work with NiceGUI's bind_* methods to enable declarative UI updates.
When a ViewModel property changes, bound UI elements automatically update.
"""

from typing import Optional


class ExperimentViewModel:
    """Reactive view model for experiment data."""
    
    def __init__(self, experiment_id: int, experiment_name: str, max_turns: int):
        self.id = experiment_id
        self.name = experiment_name
        self.status = 'queued'
        self.msg_count = 0
        self.max_turns = max_turns
        self.error_message = None
        self.robot_a_name = ''
        self.robot_b_name = ''
    
    @property
    def expected_messages(self) -> int:
        """Calculate expected message count."""
        return self.max_turns * 2
    
    @property
    def progress_text(self) -> str:
        """Get formatted progress text."""
        return f'{self.msg_count}/{self.expected_messages} messages'
    
    @property
    def status_icon(self) -> str:
        """Get icon for current status."""
        icons = {
            'completed': '✓',
            'running': '🔄',
            'queued': '⏳',
            'failed': '⚠',
            'cancelled': '❌'
        }
        return icons.get(self.status, '?')
    
    @property
    def status_with_name(self) -> str:
        """Get status icon with experiment name."""
        return f'{self.status_icon} {self.name}'


class BatchViewModel:
    """Reactive view model for batch data."""
    
    def __init__(self, batch_id: int, batch_name: str, total_experiments: int):
        self.id = batch_id
        self.name = batch_name
        self.total = total_experiments
        
        # Status counts
        self.completed = 0
        self.running = 0
        self.queued = 0
        self.failed = 0
        
        # Control state
        self.is_paused = False
    
    @property
    def progress(self) -> float:
        """Calculate progress percentage (0.0 to 1.0)."""
        if self.total == 0:
            return 0.0
        return self.completed / self.total
    
    @property
    def progress_text(self) -> str:
        """Get formatted progress text."""
        percentage = self.progress * 100
        return f'Progress: {self.completed}/{self.total} ({percentage:.1f}%)'


class ActiveUserViewModel:
    """Reactive view model for active user tracking."""
    
    def __init__(self, user_id: int, display_name: str):
        self.id = user_id
        self.display_name = display_name
        self.email = ''  # User email for disambiguation
        self.activity = 'idle'  # idle, viewing, running
        self.experiment_count = 0
        self.current_page = '/'
    
    @property
    def activity_icon(self) -> str:
        """Get icon for current activity."""
        icons = {
            'idle': '👀',
            'viewing': '📄',
            'running': '🔄'
        }
        return icons.get(self.activity, '❓')
    
    @property
    def status_text(self) -> str:
        """Get formatted status text."""
        if self.activity == 'running' and self.experiment_count > 0:
            return f'Running {self.experiment_count} experiments'
        elif self.activity == 'viewing':
            return f'Viewing {self.current_page}'
        return 'Idle'


class ExperimentListViewModel:
    """Reactive view model for experiment list items.
    
    Tracks individual experiment state for the experiments list page.
    Enables zero-flicker updates when experiment status or messages change.
    """
    
    def __init__(self, experiment_id: int, experiment_name: str):
        self.id = experiment_id
        self.name = experiment_name
        self.msg_count = 0
        self.max_turns = 0
        self.created_at = None
        
        # Robot info
        self.robot_a_name = ''
        self.robot_a_model = ''
        self.robot_b_name = ''
        self.robot_b_model = ''
        
        # Creator info
        self.creator_name = 'Unknown'
        self.creator_id = None
        
        # Batch info
        self.batch_id = None
        self.batch_name = None
        self.batch_creator_name = None
        
        # Queue status (for batch experiments)
        self.queue_status = None  # queued, running, completed, failed
        self.error_message = None
    
    @property
    def expected_messages(self) -> int:
        """Calculate expected message count."""
        return self.max_turns * 2
    
    @property
    def robots_display(self) -> str:
        """Get formatted robot names and models."""
        return f'{self.robot_a_name} ({self.robot_a_model}) vs {self.robot_b_name} ({self.robot_b_model})'
    
    @property
    def progress_text(self) -> str:
        """Get formatted progress text."""
        if self.batch_id:
            # Batch experiment - show expected
            return f'{self.msg_count}/{self.expected_messages} messages ({self.max_turns} turns each)'
        else:
            # Standalone experiment - just show count
            return f'{self.msg_count} messages'
    
    @property
    def is_batch(self) -> bool:
        """Check if this is a batch experiment."""
        return self.batch_id is not None
    
    @property
    def status_badge_text(self) -> str:
        """Get status badge text for batch experiments."""
        if not self.batch_id or not self.queue_status:
            return ''
        
        if self.queue_status == 'completed':
            return '✓ Complete'
        elif self.queue_status == 'running':
            return f'🔄 Running ({self.msg_count}/{self.expected_messages})'
        elif self.queue_status == 'failed':
            return '⚠ Failed'
        elif self.queue_status == 'queued':
            return '⏳ Queued'
        return ''
    
    @property
    def status_badge_color(self) -> str:
        """Get status badge color for batch experiments."""
        if not self.batch_id or not self.queue_status:
            return 'grey'
        
        if self.queue_status == 'completed':
            return 'positive'
        elif self.queue_status == 'running':
            return 'blue'
        elif self.queue_status == 'failed':
            return 'negative'
        elif self.queue_status == 'queued':
            return 'grey'
        return 'grey'


