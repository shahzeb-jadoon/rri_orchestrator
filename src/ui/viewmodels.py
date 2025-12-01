"""
ViewModels for reactive UI updates.
"""

from typing import Optional


class ExperimentViewModel:
    """Batch experiment view model."""
    
    def __init__(self, experiment_id: int, experiment_name: str, max_turns: int):
        self.id = experiment_id
        self.name = experiment_name
        self.status = 'queued'
        self.msg_count = 0
        self.max_turns = max_turns
        self.error_message = None
        self.robot_a_name = ''
        self.robot_b_name = ''
        
        # Badge display properties (pre-computed to avoid glitching)
        self.badge_text = None
        self.badge_tooltip = None
        self.badge_severity = None
    
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
    """Batch progress view model."""
    
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
    """Active user tracking view model."""
    
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
    """Experiment list item view model."""
    
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
        
        # Badge display properties for errors (pre-computed to avoid glitching)
        self.error_badge_text = None
        self.error_badge_tooltip = None
        self.error_badge_severity = None
    
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


class MessageViewModel:
    """Chat message view model for smooth rendering."""
    
    def __init__(
        self,
        msg_id: int,
        content: str,
        robot_name: str,
        model_used: str,
        token_count: int,
        input_tokens: Optional[int],
        output_tokens: Optional[int],
        cost_usd: Optional[float],
        response_time_ms: Optional[int],
        created_at: str
    ):
        self.id = msg_id
        self.content = content
        self.robot_name = robot_name
        self.model_used = model_used
        self.token_count = token_count
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.cost_usd = cost_usd
        self.response_time_ms = response_time_ms
        self.created_at = created_at
    
    @property
    def metadata_text(self) -> str:
        """Get formatted metadata string."""
        metadata = f'Model: {self.model_used} | Tokens: {self.token_count}'
        if self.input_tokens and self.output_tokens:
            metadata += f' (in: {self.input_tokens}, out: {self.output_tokens})'
        if self.cost_usd:
            metadata += f' | Cost: ${self.cost_usd:.4f}'
        if self.response_time_ms:
            metadata += f' | Time: {self.response_time_ms}ms'
        return metadata


class RobotStatsViewModel:
    """Per-robot statistics view model."""
    
    def __init__(self, robot_key: str, name: str, provider: str, model: str):
        self.robot_key = robot_key
        self.name = name
        self.provider = provider
        self.model = model
        self.tokens = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.cost = 0.0
        self.count = 0
    
    @property
    def avg_tokens(self) -> float:
        """Calculate average tokens per message."""
        return self.tokens / self.count if self.count > 0 else 0
    
    @property
    def cost_display(self) -> str:
        """Get formatted cost display."""
        cost_text = f'${self.cost:.4f}'
        if self.cost == 0:
            cost_text += ' (free tier)'
        return cost_text


class ExperimentStatsViewModel:
    """Experiment statistics view model for chat page."""
    
    def __init__(self):
        self.total_tokens = 0
        self.total_input = 0
        self.total_output = 0
        self.total_cost = 0.0
        self.robot_stats = {}  # {robot_key: RobotStatsViewModel}
    
    @property
    def total_summary(self) -> str:
        """Get formatted total summary."""
        return f'Total: {self.total_tokens:,} tokens (in: {self.total_input:,}, out: {self.total_output:,}), ${self.total_cost:.4f}'


class BatchGroupViewModel:
    """Batch group view model for experiments list page."""
    
    def __init__(self, batch_id: int, batch_name: str, creator_name: str, created_at):
        self.batch_id = batch_id
        self.batch_name = batch_name
        self.creator_name = creator_name
        self.created_at = created_at
        self.experiment_vms = []  # List of ExperimentListViewModel
        
        # Pre-computed summary stats
        self.completed = 0
        self.running = 0
        self.queued = 0
        self.failed = 0
        self.total = 0
        
        # Pre-computed status display
        self.status_icon = '📊'
        self.status_color = 'grey'
        self.status_text = '0/0'
    
    def update_summary(self):
        """Update summary statistics and status display."""
        self.total = len(self.experiment_vms)
        self.completed = sum(1 for vm in self.experiment_vms if vm.queue_status == 'completed')
        self.running = sum(1 for vm in self.experiment_vms if vm.queue_status == 'running')
        self.queued = sum(1 for vm in self.experiment_vms if vm.queue_status == 'queued')
        self.failed = sum(1 for vm in self.experiment_vms if vm.queue_status == 'failed')
        
        # Determine overall batch status
        if self.failed > 0:
            self.status_icon, self.status_color, self.status_text = '⚠', 'negative', f'{self.completed}/{self.total} done, {self.failed} failed'
        elif self.completed == self.total:
            self.status_icon, self.status_color, self.status_text = '✓', 'positive', f'{self.completed}/{self.total} complete'
        elif self.running > 0:
            self.status_icon, self.status_color, self.status_text = '🔄', 'blue', f'{self.completed}/{self.total}, {self.running} running'
        elif self.queued > 0:
            self.status_icon, self.status_color, self.status_text = '⏳', 'grey', f'{self.completed}/{self.total}, {self.queued} queued'
        else:
            self.status_icon, self.status_color, self.status_text = '📊', 'grey', f'{self.completed}/{self.total}'


