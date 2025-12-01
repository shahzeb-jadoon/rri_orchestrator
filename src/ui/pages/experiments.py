"""
Experiment management and chat interface.

Setup and monitor robot-robot experiments.
"""

from nicegui import ui, app
import asyncio
from datetime import datetime
from starlette.requests import Request
from src.database.models import Experiment, RobotProfile, ChatMessage, ExperimentQueue, ExperimentBatch
from src.ai.conversation import orchestrate_conversation_turn
from src.ui.components import create_navbar
from src.utils.logger import logger
from src.ui.utils import get_friendly_error_message
from src.ui.viewmodels import ExperimentListViewModel


async def export_all_experiments():
    """Export all experiments to a single JSON file."""
    import json
    from datetime import datetime
    
    experiments = await Experiment.all().prefetch_related('robot_a_profile', 'robot_b_profile', 'created_by')
    
    all_data = []
    for exp in experiments:
        messages = await ChatMessage.filter(experiment=exp).order_by('created_at')
        
        exp_data = {
            "experiment": {
                "id": exp.id,
                "name": exp.name,
                "description": exp.description,
                "initial_prompt": exp.initial_prompt,
                "max_turns": exp.max_turns,
                "created_at": exp.created_at.isoformat(),
                "created_by": exp.created_by.display_name
            },
            "robots": {
                "robot_a": {
                    "name": exp.robot_a_profile.name,
                    "provider": exp.robot_a_profile.ai_provider,
                    "model": exp.robot_a_profile.model_name,
                },
                "robot_b": {
                    "name": exp.robot_b_profile.name,
                    "provider": exp.robot_b_profile.ai_provider,
                    "model": exp.robot_b_profile.model_name,
                }
            },
            "messages": [
                {
                    "timestamp": msg.created_at.isoformat(),
                    "robot": msg.robot_name,
                    "content": msg.content,
                    "tokens": msg.token_count,
                    "cost_usd": float(msg.cost_usd) if msg.cost_usd else 0.0
                }
                for msg in messages
            ],
            "summary": {
                "total_messages": len(messages),
                "total_tokens": sum(m.token_count or 0 for m in messages),
                "total_cost_usd": float(sum(m.cost_usd or 0 for m in messages))
            }
        }
        all_data.append(exp_data)
    
    filename = f"all_experiments_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    ui.download(json.dumps(all_data, indent=2).encode(), filename)
    ui.notify(f'Exported {len(experiments)} experiments to {filename}', type='positive')


@ui.page('/experiments')
async def experiments_list_page(request: Request):
    """List all experiments with ViewModels pattern for zero-flicker auto-updates."""
    create_navbar()
    
    # Get current user
    user = getattr(request.state, 'user', None)
    if not user:
        ui.label('Please log in to view experiments').classes('text-negative')
        return
    
    # Header with export and deleted link
    with ui.row().classes('w-full justify-between items-center'):
        ui.label('Experiments').classes('text-h4')
        with ui.row().classes('gap-2'):
            ui.button('🗑️ Deleted', on_click=lambda: ui.navigate.to('/experiments/deleted')).props('flat color=grey')
            ui.button('📥 Export All', on_click=export_all_experiments).props('flat color=primary')
    
    ui.label('Manage robot-robot interaction experiments').classes('text-subtitle1 text-grey')
    
    ui.space()
    
    # Create button
    ui.button('+ Create New Experiment', on_click=lambda: ui.navigate.to('/experiments/create')).props('color=primary')
    
    ui.space()
    
    # ViewModels storage - tracks experiment state for reactive updates
    experiment_vms = {}  # {experiment_id: ExperimentListViewModel}
    batch_summaries = {}  # {batch_id: {'completed': 0, 'running': 0, ...}}
    
    async def delete_experiment(exp_id: int):
        """Soft delete experiment with permission check."""
        exp = await Experiment.get(id=exp_id).prefetch_related('created_by')
        
        # Permission check: must be creator or admin
        if not user.is_admin and exp.created_by_id != user.id:
            ui.notify('Permission denied: You can only delete your own experiments', type='negative')
            return
        
        # Soft delete
        exp.deleted_at = datetime.now()
        exp.deleted_by_id = user.id
        await exp.save()
        
        ui.notify('Experiment moved to trash', type='positive')
        # Trigger refresh
        await load_data()
        render_experiments.refresh()
    
    def render_experiment_card_from_vm(vm: ExperimentListViewModel):
        """Render a single experiment card from ViewModel (synchronous)."""
        # Make card clickable
        with ui.card().classes('w-full cursor-pointer hover:shadow-lg transition-all').on('click', lambda: ui.navigate.to(f'/experiments/{vm.id}')):
            with ui.row().classes('w-full items-center justify-between'):
                with ui.row().classes('items-center gap-2'):
                    ui.label(vm.name).classes('text-h5')
                    
                    # Creator badge (for standalone only)
                    if not vm.is_batch:
                        ui.badge(f'By: {vm.creator_name}', color='grey').props('outline')
                
                # Status badges and action buttons
                with ui.row().classes('gap-2'):
                    # Status for batch experiments
                    if vm.is_batch and vm.status_badge_text:
                        ui.badge(vm.status_badge_text, color=vm.status_badge_color).props('outline')
                        if vm.queue_status == 'failed' and vm.error_message:
                            badge_text, tooltip_msg, severity = get_friendly_error_message(vm.error_message)
                            ui.icon('help_outline', size='sm').classes(f'text-{severity}').tooltip(tooltip_msg).style('cursor: help')
            
            # Action buttons row (with click.stop to prevent card navigation)
            with ui.row().classes('gap-2').on('click.stop'):
                ui.button('View', on_click=lambda: ui.navigate.to(f'/experiments/{vm.id}')).props('flat size=sm')
                ui.button('📥 CSV', on_click=lambda: export_to_csv(vm.id)).props('flat size=sm')
                ui.button('📥 JSON', on_click=lambda: export_to_json(vm.id)).props('flat size=sm')
                
                # Only show delete if user has permission (admin or creator)
                if user.is_admin or vm.creator_id == user.id:
                    ui.button('Delete', on_click=lambda: delete_experiment(vm.id)).props('flat size=sm color=negative')
            
            ui.label(vm.robots_display).classes('text-caption text-grey')
            ui.label(vm.progress_text).classes('text-caption')
    
    @ui.refreshable
    def render_experiments():
        """Render all experiments - NiceGUI handles smart DOM updates!"""
        if not experiment_vms:
            ui.label('No experiments yet. Create one above to get started.').classes('text-grey')
            return
        
        # Group experiments by batch and standalone
        batch_groups = {}  # {batch_id: {'vms': [vms], 'created_at': datetime, 'batch_name': str, 'creator_name': str}}
        standalone_vms = []
        
        for vm in experiment_vms.values():
            if vm.batch_id:
                if vm.batch_id not in batch_groups:
                    batch_groups[vm.batch_id] = {
                        'vms': [],
                        'created_at': vm.created_at,
                        'batch_name': vm.batch_name,
                        'creator_name': vm.batch_creator_name
                    }
                batch_groups[vm.batch_id]['vms'].append(vm)
            else:
                standalone_vms.append(vm)
        
        # Create combined list sorted by creation time
        combined_items = []
        for batch_id, data in batch_groups.items():
            combined_items.append(('batch', batch_id, data['created_at'], data))
        for vm in standalone_vms:
            combined_items.append(('standalone', vm, vm.created_at, None))
        
        combined_items.sort(key=lambda x: x[2], reverse=True)
        
        # Render in order
        for item_type, item_data, created_at, extra in combined_items:
            if item_type == 'batch':
                batch_id = item_data
                batch_data = extra
                batch_vms = batch_data['vms']
                
                # Get batch summary from our pre-calculated dict
                summary = batch_summaries.get(batch_id, {})
                completed = summary.get('completed', 0)
                running = summary.get('running', 0)
                queued = summary.get('queued', 0)
                failed = summary.get('failed', 0)
                total = len(batch_vms)
                
                # Determine overall batch status
                if failed > 0:
                    status_icon, status_color, status_text = '⚠', 'negative', f'{completed}/{total} done, {failed} failed'
                elif completed == total:
                    status_icon, status_color, status_text = '✓', 'positive', f'{completed}/{total} complete'
                elif running > 0:
                    status_icon, status_color, status_text = '🔄', 'blue', f'{completed}/{total}, {running} running'
                elif queued > 0:
                    status_icon, status_color, status_text = '⏳', 'grey', f'{completed}/{total}, {queued} queued'
                else:
                    status_icon, status_color, status_text = '📊', 'grey', f'{completed}/{total}'
                
                # Batch summary card
                with ui.card().classes('w-full'):
                    with ui.row().classes('w-full items-center gap-2'):
                        with ui.expansion(
                            f'📦 Batch #{batch_id}: {batch_data["batch_name"]} • By: {batch_data["creator_name"]}',
                            icon='unfold_more'
                        ).classes('flex-grow'):
                            # Action buttons at top
                            with ui.row().classes('gap-2 mb-4'):
                                ui.button('View Batch Progress', on_click=lambda b=batch_id: ui.navigate.to(f'/batch/{b}')).props('flat size=sm color=primary')
                                ui.button('📥 Batch CSV', on_click=lambda b=batch_id: download_batch_csv(b)).props('flat size=sm')
                                ui.button('📥 Batch JSON', on_click=lambda b=batch_id: download_batch_json(b)).props('flat size=sm')
                            
                            # Individual experiments in batch
                            for vm in batch_vms:
                                render_experiment_card_from_vm(vm)
                        
                        # Status badge outside expansion
                        ui.badge(f'{status_icon} {status_text}', color=status_color)
            
            elif item_type == 'standalone':
                vm = item_data
                render_experiment_card_from_vm(vm)
    
    async def load_data():
        """Load data from database and populate ViewModels."""
        # Load all non-deleted experiments
        experiments = await Experiment.filter(
            deleted_at__isnull=True
        ).prefetch_related('created_by', 'robot_a_profile', 'robot_b_profile', 'batch', 'batch__created_by').order_by('-created_at')
        
        # Track which VMs to keep
        current_exp_ids = set()
        
        # Update/create ViewModels
        for exp in experiments:
            current_exp_ids.add(exp.id)
            
            if exp.id not in experiment_vms:
                # Create new ViewModel
                vm = ExperimentListViewModel(exp.id, exp.name)
                experiment_vms[exp.id] = vm
            else:
                # Use existing ViewModel
                vm = experiment_vms[exp.id]
            
            # Update ViewModel data
            vm.max_turns = exp.max_turns
            vm.created_at = exp.created_at
            
            vm.robot_a_name = exp.robot_a_profile.name
            vm.robot_a_model = exp.robot_a_profile.model_name
            vm.robot_b_name = exp.robot_b_profile.name
            vm.robot_b_model = exp.robot_b_profile.model_name
            
            vm.creator_name = exp.created_by.display_name if exp.created_by else (exp.created_by_name or 'Unknown')
            vm.creator_id = exp.created_by_id
            
            vm.batch_id = exp.batch_id
            if exp.batch:
                vm.batch_name = exp.batch.name
                vm.batch_creator_name = exp.batch.created_by.display_name if exp.batch.created_by else (exp.batch.created_by_name or 'Unknown')
            
            # Get message count
            vm.msg_count = await ChatMessage.filter(experiment=exp).count()
            
            # Get queue status for batch experiments
            if exp.batch_id:
                queue_entry = await ExperimentQueue.get_or_none(experiment=exp)
                if queue_entry:
                    vm.queue_status = queue_entry.status
                    vm.error_message = queue_entry.error_message if queue_entry.status == 'failed' else None
        
        # Remove VMs for deleted experiments
        for exp_id in list(experiment_vms.keys()):
            if exp_id not in current_exp_ids:
                del experiment_vms[exp_id]
        
        # Calculate batch summaries
        batch_summaries.clear()
        for vm in experiment_vms.values():
            if vm.batch_id:
                if vm.batch_id not in batch_summaries:
                    batch_summaries[vm.batch_id] = {'completed': 0, 'running': 0, 'queued': 0, 'failed': 0}
                
                if vm.queue_status == 'completed':
                    batch_summaries[vm.batch_id]['completed'] += 1
                elif vm.queue_status == 'running':
                    batch_summaries[vm.batch_id]['running'] += 1
                elif vm.queue_status == 'queued':
                    batch_summaries[vm.batch_id]['queued'] += 1
                elif vm.queue_status == 'failed':
                    batch_summaries[vm.batch_id]['failed'] += 1
    
    # Initial load
    await load_data()
    render_experiments()
    
    # Auto-refresh every 2 seconds
    async def refresh_data():
        await load_data()
        render_experiments.refresh()
    
    ui.timer(2.0, refresh_data)
    
    # Keep existing export functions (they're referenced above)
    async def download_batch_csv(batch_id):
        """Export all experiments in batch to combined CSV."""
        import csv
        import io
        
        batch_obj = await ExperimentBatch.get(id=batch_id).prefetch_related('created_by')
        batch_experiments = await Experiment.filter(batch_id=batch_id).prefetch_related(
            'robot_a_profile', 'robot_b_profile', 'created_by'
        )
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow(['Batch Name', 'Batch ID', 'Experiment Name', 'Experiment ID', 
                       'Robot A', 'Robot B', 'Max Turns', 'Messages', 'Status', 'Creator'])
        
        # Data
        for exp in batch_experiments:
            msg_count = await ChatMessage.filter(experiment=exp).count()
            queue_entry = await ExperimentQueue.get_or_none(experiment=exp)
            status = queue_entry.status if queue_entry else 'unknown'
            creator = exp.created_by.display_name if exp.created_by else (exp.created_by_name or 'Unknown')
            
            writer.writerow([
                batch_obj.name,
                batch_id,
                exp.name,
                exp.id,
                exp.robot_a_profile.name,
                exp.robot_b_profile.name,
                exp.max_turns,
                msg_count,
                status,
                creator
            ])
        
        # Download
        csv_data = output.getvalue()
        ui.download(csv_data.encode(), f'batch_{batch_id}_{batch_obj.name}.csv')
    
    async def download_batch_json(batch_id):
        """Export all experiments in batch to combined JSON."""
        import json
        
        batch_obj = await ExperimentBatch.get(id=batch_id).prefetch_related('created_by')
        batch_experiments = await Experiment.filter(batch_id=batch_id).prefetch_related(
            'robot_a_profile', 'robot_b_profile', 'created_by'
        )
        
        batch_data = {
            'batch_id': batch_id,
            'batch_name': batch_obj.name,
            'created_by': batch_obj.created_by.display_name if batch_obj.created_by else (batch_obj.created_by_name or 'Unknown'),
            'created_at': batch_obj.created_at.isoformat() if batch_obj.created_at else None,
            'total_experiments': len(batch_experiments),
            'experiments': []
        }
        
        for exp in batch_experiments:
            messages = await ChatMessage.filter(experiment=exp).order_by('created_at')
            queue_entry = await ExperimentQueue.get_or_none(experiment=exp)
            
            exp_data = {
                'id': exp.id,
                'name': exp.name,
                'description': exp.description,
                'robot_a': {
                    'name': exp.robot_a_profile.name,
                    'provider': exp.robot_a_profile.ai_provider,
                    'model': exp.robot_a_profile.model_name
                },
                'robot_b': {
                    'name': exp.robot_b_profile.name,
                    'provider': exp.robot_b_profile.ai_provider,
                    'model': exp.robot_b_profile.model_name
                },
                'max_turns': exp.max_turns,
                'status': queue_entry.status if queue_entry else 'unknown',
                'messages': [
                    {
                        'robot_name': msg.robot_name,
                        'content': msg.content,
                        'timestamp': msg.created_at.isoformat(),
                        'tokens': msg.token_count,
                        'cost_usd': float(msg.cost_usd) if msg.cost_usd else 0
                    }
                    for msg in messages
                ]
            }
            batch_data['experiments'].append(exp_data)
        
        # Download
        json_str = json.dumps(batch_data, indent=2)
        ui.download(json_str.encode(), f'batch_{batch_id}_{batch_obj.name}.json')


@ui.page('/experiments/create')
async def create_experiment_page(request: Request):
    """
    Create a new experiment with robot selection.
    """
    create_navbar()
    
    # Get current user from middleware
    user = getattr(request.state, 'user', None)
    
    if not user:
        ui.label('Please log in to create experiments').classes('text-negative')
        return
    
    ui.label('Create Experiment').classes('text-h4')
    
    ui.space()
    
    # Load available robots
    robots = await RobotProfile.all()
    
    if len(robots) < 2:
        with ui.card():
            ui.label('⚠️ You need at least 2 robot profiles to create an experiment.').classes('text-orange')
            ui.button('Create Robots', on_click=lambda: ui.navigate.to('/robots/create')).props('color=primary')
        return
    
    robot_options = {r.id: f'{r.name} ({r.ai_provider}/{r.model_name})' for r in robots}
    
    with ui.card().classes('w-full max-w-2xl'):
        # Experiment details
        name_input = ui.input('Experiment Name').classes('w-full').props('outlined')
        description_input = ui.textarea('Description').classes('w-full').props('outlined')
        
        ui.separator()
        
        # Robot selection
        ui.label('Robot Configuration').classes('text-h6 mt-4')
        
        robot_a_select = ui.select(
            options=robot_options,
            label='Robot A',
            value=list(robot_options.keys())[0] if robot_options else None
        ).classes('w-full').props('outlined')
        
        # Display Robot A details
        robot_a_info = ui.label('').classes('text-caption text-grey')
        
        async def update_robot_a_info():
            if robot_a_select.value:
                robot = await RobotProfile.get(id=robot_a_select.value)
                robot_a_info.text = f'Provider: {robot.ai_provider} | Model: {robot.model_name} | Temp: {robot.default_temperature}'
        
        robot_a_select.on('update:model-value', update_robot_a_info)
        await update_robot_a_info()
        
        ui.space()
        
        robot_b_select = ui.select(
            options=robot_options,
            label='Robot B',
            value=list(robot_options.keys())[1] if len(robot_options) > 1 else list(robot_options.keys())[0]
        ).classes('w-full').props('outlined')
        
        # Display Robot B details
        robot_b_info = ui.label('').classes('text-caption text-grey')
        
        async def update_robot_b_info():
            if robot_b_select.value:
                robot = await RobotProfile.get(id=robot_b_select.value)
                robot_b_info.text = f'Provider: {robot.ai_provider} | Model: {robot.model_name} | Temp: {robot.default_temperature}'
        
        robot_b_select.on('update:model-value', update_robot_b_info)
        await update_robot_b_info()
        
        ui.separator()
        
        # Conversation settings
        ui.label('Conversation Settings').classes('text-h6 mt-4')
        
        initial_prompt_input = ui.textarea(
            'Initial Prompt',
            value='Discuss the ethical implications of AI in healthcare.'
        ).classes('w-full').props('outlined rows=3')
        
        max_turns_input = ui.number(
            'Max Turns',
            value=10,
            min=1,
            max=100
        ).classes('w-full').props('outlined')
        
        ui.space()
        
        # Create button
        async def create_experiment():
            if not name_input.value:
                ui.notify('Please enter an experiment name', type='warning')
                return
            
            if robot_a_select.value == robot_b_select.value:
                ui.notify('Please select different robots for A and B', type='warning')
                return
            
            # Get robot profiles
            robot_a = await RobotProfile.get(id=robot_a_select.value)
            robot_b = await RobotProfile.get(id=robot_b_select.value)
            
            # Create experiment
            experiment = await Experiment.create(
                name=name_input.value,
                description=description_input.value or '',
                initial_prompt=initial_prompt_input.value or 'Discuss the ethical implications of AI in healthcare.',
                max_turns=int(max_turns_input.value or 10),
                created_by=user,
                robot_a_profile=robot_a,
                robot_b_profile=robot_b,
                is_active=True
            )
            
            ui.notify(f'Experiment "{name_input.value}" created!', type='positive')
            ui.navigate.to(f'/experiments/{experiment.id}')
        
        with ui.row().classes('w-full justify-end gap-2'):
            ui.button('Cancel', on_click=lambda: ui.navigate.to('/experiments')).props('flat')
            ui.button('Create & Start', on_click=create_experiment).props('color=primary')




async def export_to_csv(experiment_id: int):
    """Export experiment conversation to CSV format with metadata."""
    import csv
    from io import StringIO
    
    experiment = await Experiment.get(id=experiment_id)
    await experiment.fetch_related('robot_a_profile', 'robot_b_profile', 'created_by')
    messages = await ChatMessage.filter(experiment=experiment).order_by('created_at')
    
    output = StringIO()
    writer = csv.writer(output)
    
    # Metadata section
    writer.writerow(['EXPERIMENT METADATA'])
    writer.writerow(['Name', experiment.name])
    writer.writerow(['Description', experiment.description or ''])
    writer.writerow(['Topic/Initial Prompt', experiment.initial_prompt])
    writer.writerow(['Max Turns', experiment.max_turns])
    writer.writerow(['Created By', experiment.created_by.display_name])
    writer.writerow(['Created At', experiment.created_at.isoformat()])
    writer.writerow([])  # Blank row
    
    # Robot configuration section
    writer.writerow(['ROBOT CONFIGURATION'])
    writer.writerow(['Robot A Name', experiment.robot_a_profile.name])
    writer.writerow(['Robot A Provider', experiment.robot_a_profile.ai_provider])
    writer.writerow(['Robot A Model', experiment.robot_a_profile.model_name])
    writer.writerow(['Robot A System Prompt', experiment.robot_a_profile.system_prompt])
    writer.writerow([])  # Blank row
    writer.writerow(['Robot B Name', experiment.robot_b_profile.name])
    writer.writerow(['Robot B Provider', experiment.robot_b_profile.ai_provider])
    writer.writerow(['Robot B Model', experiment.robot_b_profile.model_name])
    writer.writerow(['Robot B System Prompt', experiment.robot_b_profile.system_prompt])
    writer.writerow([])  # Blank row
    
    # Conversation data section
    writer.writerow(['CONVERSATION MESSAGES'])
    writer.writerow([
        'timestamp', 'robot_name', 'robot_display_name', 'robot_provider',
        'model', 'message', 'tokens_total', 'tokens_in', 'tokens_out',
        'cost_usd', 'response_time_ms'
    ])
    
    # Data rows
    for msg in messages:
        robot_name = (experiment.robot_a_profile.name if msg.robot_name == 'robot_a'
                     else experiment.robot_b_profile.name)
        writer.writerow([
            msg.created_at.isoformat(),
            msg.robot_name,
            robot_name,
            msg.robot_provider,
            msg.model_used,
            msg.content,
            msg.token_count,
            msg.input_tokens,
            msg.output_tokens,
            float(msg.cost_usd) if msg.cost_usd else 0.0,  # Convert Decimal to float
            msg.response_time_ms
        ])
    
    # Download
    filename = f"{experiment.name.replace(' ', '_')}_{experiment.id}.csv"
    ui.download(output.getvalue().encode(), filename)
    ui.notify(f'Exported to {filename}', type='positive')


async def export_to_json(experiment_id: int):
    """Export experiment conversation to JSON format."""
    import json
    
    experiment = await Experiment.get(id=experiment_id)
    await experiment.fetch_related('robot_a_profile', 'robot_b_profile', 'created_by')
    messages = await ChatMessage.filter(experiment=experiment).order_by('created_at')
    
    data = {
        "experiment": {
            "id": experiment.id,
            "name": experiment.name,
            "description": experiment.description,
            "initial_prompt": experiment.initial_prompt,
            "max_turns": experiment.max_turns,
            "created_at": experiment.created_at.isoformat(),
            "created_by": experiment.created_by.display_name
        },
        "robots": {
            "robot_a": {
                "name": experiment.robot_a_profile.name,
                "provider": experiment.robot_a_profile.ai_provider,
                "model": experiment.robot_a_profile.model_name,
                "temperature": experiment.robot_a_profile.default_temperature,
                "system_prompt": experiment.robot_a_profile.system_prompt
            },
            "robot_b": {
                "name": experiment.robot_b_profile.name,
                "provider": experiment.robot_b_profile.ai_provider,
                "model": experiment.robot_b_profile.model_name,
                "temperature": experiment.robot_b_profile.default_temperature,
                "system_prompt": experiment.robot_b_profile.system_prompt
            }
        },
        "messages": [
            {
                "timestamp": msg.created_at.isoformat(),
                "robot": msg.robot_name,
                "robot_display_name": (experiment.robot_a_profile.name if msg.robot_name == 'robot_a'
                                      else experiment.robot_b_profile.name),
                "provider": msg.robot_provider,
                "model": msg.model_used,
                "content": msg.content,
                "tokens": {
                    "total": msg.token_count,
                    "input": msg.input_tokens,
                    "output": msg.output_tokens
                },
                "cost_usd": float(msg.cost_usd) if msg.cost_usd else 0.0,  # Convert Decimal to float
                "response_time_ms": msg.response_time_ms
            }
            for msg in messages
        ],
        "summary": {
            "total_messages": len(messages),
            "robot_a_messages": sum(1 for m in messages if m.robot_name == 'robot_a'),
            "robot_b_messages": sum(1 for m in messages if m.robot_name == 'robot_b'),
            "total_tokens": sum(m.token_count or 0 for m in messages),
            "total_cost_usd": float(sum(m.cost_usd or 0 for m in messages)),  # Convert Decimal to float
            "duration_seconds": (messages[-1].created_at - messages[0].created_at).total_seconds() if messages else 0
        }
    }
    
    filename = f"{experiment.name.replace(' ', '_')}_{experiment.id}.json"
    ui.download(json.dumps(data, indent=2).encode(), filename)
    ui.notify(f'Exported to {filename}', type='positive')


@ui.page('/experiments/{experiment_id}')
async def chat_page(experiment_id: int):
    """
    Enhanced chat interface with auto-run mode, pause controls, and error display.
    """
    create_navbar()
    
    # Load experiment
    experiment = await Experiment.get_or_none(id=experiment_id)
    
    if not experiment:
        ui.label('Experiment not found').classes('text-h5 text-red')
        ui.button('Back to Experiments', on_click=lambda: ui.navigate.to('/experiments'))
        return
    
    await experiment.fetch_related('robot_a_profile', 'robot_b_profile')
    
    # Header with export buttons
    with ui.row().classes('w-full items-center justify-between'):
        ui.label(f'Experiment: {experiment.name}').classes('text-h4')
        with ui.row().classes('gap-2'):
            ui.button('📥 Export CSV', on_click=lambda: export_to_csv(experiment.id)).props('flat')
            ui.button('📥 Export JSON', on_click=lambda: export_to_json(experiment.id)).props('flat')
    
    ui.label(
        f'{experiment.robot_a_profile.name} ({experiment.robot_a_profile.model_name}) '
        f'vs '
        f'{experiment.robot_b_profile.name} ({experiment.robot_b_profile.model_name})'
    ).classes('text-subtitle1 text-grey')
    
    ui.separator()
    
    # Chat display area
    chat_container = ui.column().classes('w-full max-w-4xl gap-2')
    
    # Load and display messages
    @ui.refreshable
    async def display_messages():
        messages = await ChatMessage.filter(experiment=experiment).order_by('created_at')
        
        chat_container.clear()
        
        with chat_container:
            if not messages:
                ui.label('No messages yet. Start the conversation below.').classes('text-grey text-center')
            else:
                for msg in messages:
                    # Determine robot and color
                    is_robot_a = msg.robot_name == 'robot_a'
                    robot_name = experiment.robot_a_profile.name if is_robot_a else experiment.robot_b_profile.name
                    card_color = 'bg-green-100' if is_robot_a else 'bg-purple-100'
                    
                    with ui.card().classes(f'w-full {card_color}'):
                        ui.label(f'🤖 {robot_name}').classes('text-bold')
                        ui.label(msg.content).classes('text-body1 whitespace-pre-wrap')
                        
                        # Metadata
                        metadata = f'Model: {msg.model_used} | Tokens: {msg.token_count}'
                        if msg.input_tokens and msg.output_tokens:
                            metadata += f' (in: {msg.input_tokens}, out: {msg.output_tokens})'
                        if msg.cost_usd:
                            metadata += f' | Cost: ${msg.cost_usd:.4f}'
                        if msg.response_time_ms:
                            metadata += f' | Time: {msg.response_time_ms}ms'
                        
                        ui.label(metadata).classes('text-caption text-grey')
    
    await display_messages()
    
    # State management
    state = {
        'is_running': False,
        'is_paused': False,
        'pause_after_round': False,
        'auto_mode': True,
        'current_turn_count': 0,
        'max_turns_notified': False  # Track if user has been notified in manual mode
    }
    
    # Loading/status indicator
    status_label = ui.label('Ready').classes('text-caption text-grey')
    
    ui.separator()
    
    # Controls
    with ui.card().classes('w-full max-w-4xl'):
        ui.label('Controls').classes('text-h6')
        
        # Mode selection
        with ui.row().classes('w-full items-center gap-4'):
            ui.label('Mode:').classes('text-subtitle2')
            mode_toggle = ui.toggle(['Manual', 'Auto'], value='Auto' if state['auto_mode'] else 'Manual').classes('mt-2')
            
            async def update_mode():
                state['auto_mode'] = (mode_toggle.value == 'Auto')
                # Update button text based on mode
                msg_count = await ChatMessage.filter(experiment=experiment).count()
                if msg_count == 0:
                    start_btn.text = '▶ Start Conversation'
                elif state['auto_mode']:
                    start_btn.text = '▶ Resume Conversation'
                else:
                    start_btn.text = '▶ Next Turn'
                
                # Show/hide buttons based on mode
                if state['auto_mode']:
                    run_round_btn.set_visibility(False)
                    pause_round_btn.set_visibility(True)
                else:
                    run_round_btn.set_visibility(True)
                    pause_round_btn.set_visibility(False)
                
                # Refresh max turns UI
                await max_turns_status.refresh()
            
            mode_toggle.on('update:model-value', update_mode)
        
        # Max turns status and extension
        @ui.refreshable
        async def max_turns_status():
            """Display max turns status and extension options."""
            robot_a_count = await ChatMessage.filter(experiment=experiment, robot_name='robot_a').count()
            robot_b_count = await ChatMessage.filter(experiment=experiment, robot_name='robot_b').count()
            max_per_robot = experiment.max_turns or 10
            
            if robot_a_count >= max_per_robot and robot_b_count >= max_per_robot:
                with ui.card().classes('w-full bg-orange-50 border-l-4 border-orange-500 mt-2'):
                    ui.label('🎯 Max Turns Reached').classes('text-subtitle2 text-orange-800')
                    ui.label(f'Each robot has spoken {max_per_robot} times.').classes('text-caption')
                    
                    # Only show extension options in auto mode
                    if state['auto_mode']:
                        ui.separator()
                        ui.label('Continue for:').classes('text-caption font-bold mt-2')
                        
                        async def extend_and_continue(additional_turns: int):
                            """Extend max turns and resume."""
                            experiment.max_turns += additional_turns
                            await experiment.save()
                            state['max_turns_notified'] = False
                            await max_turns_status.refresh()
                            ui.notify(f'Extended by {additional_turns} turns. Resuming...', type='positive')
                            await run_auto_mode()
                        
                        with ui.row().classes('gap-2 mt-2'):
                            ui.button('+1', on_click=lambda: extend_and_continue(1)).props('size=sm')
                            ui.button('+2', on_click=lambda: extend_and_continue(2)).props('size=sm')
                            ui.button('+5', on_click=lambda: extend_and_continue(5)).props('size=sm')
                        
                        with ui.row().classes('gap-2 items-center mt-2'):
                            custom_turns = ui.number(label='Custom', value=10, min=1, max=100).classes('w-24').props('dense outlined')
                            ui.button('Go', on_click=lambda: extend_and_continue(int(custom_turns.value))).props('size=sm')
                    else:
                        # Manual mode: just show info
                        ui.label('Click "Next Turn" to continue (auto-increments turns).').classes('text-caption text-grey mt-1')
        
        await max_turns_status()
        
        ui.space()
        
        # Initial prompt (only for first turn)
        @ui.refreshable
        async def show_initial_prompt():
            msg_count = await ChatMessage.filter(experiment=experiment).count()
            
            if msg_count == 0:
                ui.label('Initial Prompt (first turn only):').classes('text-subtitle2 mt-2')
                return ui.textarea(
                    value=experiment.initial_prompt or 'Discuss the ethical implications of AI in healthcare.',
                    placeholder='Enter the starting prompt'
                ).classes('w-full').props('outlined rows=2')
            else:
                return None
        
        initial_prompt_input = await show_initial_prompt()
        
        # Buttons
        with ui.row().classes('w-full gap-4 items-center mt-4'):
            
            async def run_single_turn():
                """Run one turn of the conversation."""
                messages = await ChatMessage.filter(experiment=experiment).count()
                
                # Check max turns
                robot_a_count = await ChatMessage.filter(experiment=experiment, robot_name='robot_a').count()
                robot_b_count = await ChatMessage.filter(experiment=experiment, robot_name='robot_b').count()
                max_per_robot = experiment.max_turns or 10
                
                if robot_a_count >= max_per_robot and robot_b_count >= max_per_robot:
                    # Notify in both modes (once)
                    if not state['max_turns_notified']:
                        ui.notify(
                            f'Max turns reached! Each robot has spoken {max_per_robot} times.',
                            type='warning',
                            timeout=5000
                        )
                        state['max_turns_notified'] = True
                        await max_turns_status.refresh()
                    
                    # In manual mode: auto-increment by 1 and continue
                    if not state['auto_mode']:
                        experiment.max_turns += 1
                        await experiment.save()
                        ui.notify(f'Max turns extended to {experiment.max_turns}', type='info', timeout=2000)
                        await max_turns_status.refresh()
                    else:
                        # In auto mode: stop and show extension UI
                        status_label.text = f'Max turns reached ({max_per_robot} per robot)'
                        await max_turns_status.refresh()
                        return False
                
                # Determine which robot speaks
                initiating_robot = 'robot_a' if messages % 2 == 0 else 'robot_b'
                robot_name = experiment.robot_a_profile.name if initiating_robot == 'robot_a' else experiment.robot_b_profile.name
                
                # Initial prompt only for first turn
                prompt = None
                if messages == 0 and initial_prompt_input:
                    prompt = initial_prompt_input.value
                
                status_label.text = f'🔄 Generating response from {robot_name}...'
                ui.notify(f'Generating response from {robot_name}...', type='info')
                
                try:
                    await orchestrate_conversation_turn(
                        experiment=experiment,
                        initiating_robot=initiating_robot,
                        initial_prompt=prompt
                    )
                    
                    await display_messages.refresh()
                    await update_stats()
                    await show_initial_prompt.refresh()
                    await max_turns_status.refresh()
                    
                    status_label.text = f'✓ {robot_name} responded'
                    ui.notify(f'{robot_name} responded successfully', type='positive')
                    return True
                    
                except Exception as e:
                    logger.error(f"Turn failed: {e}")
                    status_label.text = f'❌ Error: {str(e)[:50]}...'
                   
                    # Display error in chat as system message
                    with chat_container:
                        with ui.card().classes('w-full bg-red-100'):
                            ui.label('⚠️ System Error').classes('text-bold text-red')
                            ui.label(str(e)).classes('text-caption')
                    
                    ui.notify(f'Error: {str(e)}', type='negative', timeout=10000)
                    return False
            
            async def run_full_round():
                """Run a full round (both robots speak once)."""
                # Run robot A
                success_a = await run_single_turn()
                if not success_a:
                    return
                
                # Short delay between robots
                await asyncio.sleep(0.5)
                
                # Run robot B
                await run_single_turn()
            
            async def run_auto_mode():
                """Run conversation automatically until max turns or pause."""
                state['is_running'] = True
                state['is_paused'] = False
                
                start_btn.props('disable')
                pause_btn.props(remove='disable')
                pause_round_btn.props(remove='disable')
                
                try:
                    while state['is_running'] and not state['is_paused']:
                        # Run one turn
                        success = await run_single_turn()
                        
                        if not success:
                            break
                        
                        # Check for pause after round
                        messages = await ChatMessage.filter(experiment=experiment).count()
                        if state['pause_after_round'] and messages % 2 == 0:
                            state['is_paused'] = True
                            ui.notify('Paused after completing round', type='info')
                            break
                        
                        # Short delay between turns
                        await asyncio.sleep(1)
                    
                finally:
                    state['is_running'] = False
                    state['pause_after_round'] = False
                    start_btn.props(remove='disable')
                    pause_btn.props('disable')
                    pause_round_btn.props('disable')
            
            async def start_conversation():
                """Start conversation (auto or manual)."""
                if state['auto_mode']:
                    await run_auto_mode()
                else:
                    await run_single_turn()
            
            def pause_immediately():
                """Pause conversation immediately."""
                state['is_paused'] = True
                status_label.text = 'Paused'
                ui.notify('Conversation paused', type='info')
            
            def pause_after_round():
                """Pause after current round completes."""
                state['pause_after_round'] = True
                ui.notify('Will pause after current round finishes', type='info')
            
            # Determine button text
            msg_count = await ChatMessage.filter(experiment=experiment).count()
            start_text = '▶ Start Conversation' if msg_count == 0 else ('▶ Resume Conversation' if state['auto_mode'] else '▶ Next Turn')
            
            start_btn = ui.button(start_text, on_click=start_conversation).props('color=primary')
            run_round_btn = ui.button('▶▶ Run Round', on_click=run_full_round).props('color=secondary')
            pause_btn = ui.button('⏸ Pause Now', on_click=pause_immediately).props('color=orange disable')
            pause_round_btn = ui.button('⏸ Pause After Round', on_click=pause_after_round).props('flat disable')
            
            # Set initial visibility based on mode
            if state['auto_mode']:
                run_round_btn.set_visibility(False)
            else:
                pause_round_btn.set_visibility(False)
        
        # Stats
        ui.separator()
        
        msg_count_label = ui.label('').classes('text-caption text-grey mt-2')
        
        # Stats container with proper formatting
        stats_container = ui.column().classes('w-full gap-1 mt-2')
        
        # Token usage progress bar
        with ui.row().classes('w-full items-center gap-2 mt-2'):
            ui.label('Context Window:').classes('text-caption')
            token_progress = ui.linear_progress(value=0).classes('flex-grow')
            token_label = ui.label('0 / 0 tokens (0%)').classes('text-caption')
        
        async def update_stats():
            """Update all statistics including token progress."""
            messages = await ChatMessage.filter(experiment=experiment).all()
            
            # Message count
            robot_a_count = sum(1 for m in messages if m.robot_name == 'robot_a')
            robot_b_count = sum(1 for m in messages if m.robot_name == 'robot_b')
            msg_count_label.text = f'{len(messages)} messages ({robot_a_count} from {experiment.robot_a_profile.name}, {robot_b_count} from {experiment.robot_b_profile.name})'
            
            # Cost and tokens
            total_cost = sum(m.cost_usd or 0 for m in messages)
            total_tokens = sum(m.token_count or 0 for m in messages)
            total_input = sum(m.input_tokens or 0 for m in messages)
            total_output = sum(m.output_tokens or 0 for m in messages)
            
            # Token usage progress (use robot_a's model as reference)
            from src.ai.token_counter import get_model_token_limit
            max_tokens = get_model_token_limit(experiment.robot_a_profile.model_name)
            token_percentage = min(total_tokens / max_tokens, 1.0) if max_tokens > 0 else 0
            
            token_progress.value = token_percentage
            token_label.text = f'{total_tokens:,} / {max_tokens:,} tokens ({token_percentage*100:.1f}%)'
            
            # Color coding for token usage
            if token_percentage > 0.8:
                token_progress.props('color=orange')
            elif token_percentage > 0.6:
                token_progress.props('color=yellow')
            else:
                token_progress.props('color=primary')
            
            # Per-robot detailed breakdown
            robot_stats = {}
            for msg in messages:
                robot_key = msg.robot_name
                if robot_key not in robot_stats:
                    robot_profile = (experiment.robot_a_profile if msg.robot_name == 'robot_a' 
                                    else experiment.robot_b_profile)
                    robot_stats[robot_key] = {
                        'name': robot_profile.name,
                        'provider': msg.robot_provider,
                        'model': msg.model_used,
                        'tokens': 0,
                        'input_tokens': 0,
                        'output_tokens': 0,
                        'cost': 0,
                        'count': 0
                    }
                
                robot_stats[robot_key]['tokens'] += msg.token_count or 0
                robot_stats[robot_key]['input_tokens'] += msg.input_tokens or 0
                robot_stats[robot_key]['output_tokens'] += msg.output_tokens or 0
                robot_stats[robot_key]['cost'] += msg.cost_usd or 0
                robot_stats[robot_key]['count'] += 1
            
            # Clear and rebuild stats display
            stats_container.clear()
            
            with stats_container:
                # Total (bold)
                ui.label(f'Total: {total_tokens:,} tokens (in: {total_input:,}, out: {total_output:,}), ${total_cost:.4f}').classes('text-bold text-caption')
                
                # Per-robot breakdown
                if robot_stats:
                    ui.label('Per-Robot Breakdown:').classes('text-caption mt-2')
                    for robot_key, stats in robot_stats.items():
                        avg_tokens = stats['tokens'] / stats['count'] if stats['count'] > 0 else 0
                        
                        # Robot name
                        ui.label(f"• {stats['name']} ({stats['provider']}/{stats['model']})").classes('text-caption ml-4')
                        
                        # Tokens
                        ui.label(f"Tokens: {stats['tokens']:,} (in: {stats['input_tokens']:,}, out: {stats['output_tokens']:,})").classes('text-caption ml-8 text-grey-7')
                        
                        # Cost
                        cost_text = f"Cost: ${stats['cost']:.4f}"
                        if stats['cost'] == 0:
                            cost_text += " (free tier)"
                        ui.label(cost_text).classes('text-caption ml-8 text-grey-7')
                        
                        # Message stats
                        ui.label(f"{stats['count']} messages, avg {avg_tokens:.0f} tokens/msg").classes('text-caption ml-8 text-grey-7')
        
        # Initial stats
        await update_stats()
