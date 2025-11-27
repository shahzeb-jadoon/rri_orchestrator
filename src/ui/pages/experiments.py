"""
Experiment management and chat interface pages.

Provides setup for robot-robot experiments and real-time chat display.
"""

from nicegui import ui, app
import asyncio
from src.database.models import Experiment, RobotProfile, ChatMessage
from src.ai.conversation import orchestrate_conversation_turn
from src.ui.components import create_navbar
from src.utils.logger import logger
from src.utils.logger import logger


@ui.page('/experiments')
async def experiments_list_page():
    """
    List all experiments with status and actions.
    """
    create_navbar()
    
    ui.label('Experiments').classes('text-h4')
    ui.label('Manage robot-robot interaction experiments').classes('text-subtitle1 text-grey')
    
    ui.space()
    
    # Create button
    ui.button('+ Create New Experiment', on_click=lambda: ui.navigate.to('/experiments/create')).props('color=primary')
    
    ui.space()
    
    # Load experiments
    experiments = await Experiment.all().prefetch_related('created_by', 'robot_a_profile', 'robot_b_profile')
    
    if not experiments:
        with ui.card():
            ui.label('No experiments yet. Create your first one!').classes('text-grey')
    else:
        # Table of experiments
        columns = [
            {'name': 'name', 'label': 'Name', 'field': 'name', 'align': 'left'},
            {'name': 'robot_a', 'label': 'Robot A', 'field': 'robot_a', 'align': 'left'},
            {'name': 'robot_b', 'label': 'Robot B', 'field': 'robot_b', 'align': 'left'},
            {'name': 'messages', 'label': 'Messages', 'field': 'messages', 'align': 'center'},
            {'name': 'actions', 'label': 'Actions', 'field': 'actions', 'align': 'right'},
        ]
        
        rows = []
        for exp in experiments:
            msg_count = await ChatMessage.filter(experiment=exp).count()
            rows.append({
                'id': exp.id,
                'name': exp.name,
                'robot_a': exp.robot_a_profile.name if exp.robot_a_profile else 'N/A',
                'robot_b': exp.robot_b_profile.name if exp.robot_b_profile else 'N/A',
                'messages': msg_count,
                'actions': exp.id
            })
        
        table = ui.table(columns=columns, rows=rows).classes('w-full')
        
        # Add action buttons
        table.add_slot('body-cell-actions', '''
            <q-td key="actions" :props="props">
                <q-btn flat dense icon="chat" @click="$parent.$emit('view', props.row)" label="View" />
                <q-btn flat dense icon="delete" color="red" @click="$parent.$emit('delete', props.row)" />
            </q-td>
        ''')
        
        table.on('view', lambda e: ui.navigate.to(f'/experiments/{e.args["id"]}'))
        
        async def delete_experiment(e):
            exp_id = e.args['id']
            await Experiment.filter(id=exp_id).delete()
            ui.notify('Experiment deleted', type='positive')
            ui.navigate.to('/experiments')
        
        table.on('delete', delete_experiment)


@ui.page('/experiments/create')
async def create_experiment_page():
    """
    Create a new experiment with robot selection.
    """
    create_navbar()
    
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
            
            # Get or create default user
            from src.database.models import User
            user = await User.get_or_none(username='default_user')
            if not user:
                user = await User.create(
                    username='default_user',
                    email='user@example.com',
                    hashed_password='placeholder'
                )
            
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
    
    # Header
    ui.label(f'Experiment: {experiment.name}').classes('text-h4')
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
        'auto_mode': True,  # Default to auto
        'current_turn_count': 0
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
            
            mode_toggle.on('update:model-value', update_mode)
        
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
                    status_label.text = f'Max turns reached ({max_per_robot} per robot)'
                    ui.notify(f'Max turns reached! Each robot has spoken {max_per_robot} times.', type='warning')
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
        cost_summary = ui.label('').classes('text-caption text-grey')
        
        async def update_stats():
            """Update all statistics."""
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
            
            # Per-provider breakdown
            breakdown = {}
            for msg in messages:
                provider = msg.robot_provider or 'unknown'
                if provider not in breakdown:
                    breakdown[provider] = {'cost': 0, 'tokens': 0}
                breakdown[provider]['cost'] += msg.cost_usd or 0
                breakdown[provider]['tokens'] += msg.token_count or 0
            
            summary = f'Total: {total_tokens} tokens (in: {total_input}, out: {total_output}), ${total_cost:.4f}'
            if breakdown:
                summary += ' | Breakdown: '
                parts = [f'{p}: ${d["cost"]:.4f}' for p, d in breakdown.items()]
                summary += ', '.join(parts)
            
            cost_summary.text = summary
        
        # Initial stats
        await update_stats()
