"""
Experiment management and chat interface pages.

Provides setup for robot-robot experiments and real-time chat display.
"""

from nicegui import ui
from src.database.models import Experiment, RobotProfile, ChatMessage
from src.ai.conversation import orchestrate_conversation_turn
from src.ui.components import create_navbar


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
    View experiment with chat interface.
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
    
    ui.separator()
    
    # Controls
    with ui.card().classes('w-full max-w-4xl'):
        ui.label('Controls').classes('text-h6')
        
        # Initial prompt for first turn
        initial_prompt = ui.textarea(
            'Initial Prompt (for first turn only)',
            value='Discuss the ethical implications of AI in healthcare.'
        ).classes('w-full').props('outlined rows=2')
        
        with ui.row().classes('w-full gap-4 items-center'):
            # Next turn button
            async def run_turn():
                messages = await ChatMessage.filter(experiment=experiment).count()
                
                # Alternate between robots
                initiating_robot = 'robot_a' if messages % 2 == 0 else 'robot_b'
                
                # Use initial prompt only for first message
                prompt = initial_prompt.value if messages == 0 else None
                
                ui.notify(f'Generating response...', type='info')
                
                try:
                    await orchestrate_conversation_turn(
                        experiment=experiment,
                        initiating_robot=initiating_robot,
                        initial_prompt=prompt
                    )
                    
                    ui.notify('Turn complete!', type='positive')
                    await display_messages.refresh()
                    
                except Exception as e:
                    ui.notify(f'Error: {str(e)}', type='negative')
            
            ui.button('▶ Next Turn', on_click=run_turn).props('color=primary')
            
            # Message count
            msg_count_label = ui.label('')
            
            async def update_count():
                count = await ChatMessage.filter(experiment=experiment).count()
                msg_count_label.text = f'{count} messages'
            
            ui.timer(1.0, update_count, once=True)
        
        # Cost summary
        cost_summary = ui.label('').classes('text-caption text-grey mt-2')
        
        async def update_cost():
            messages = await ChatMessage.filter(experiment=experiment).all()
            
            total_cost = sum(msg.cost_usd or 0 for msg in messages)
            total_tokens = sum(msg.token_count or 0 for msg in messages)
            
            # Per-provider breakdown
            breakdown = {}
            for msg in messages:
                provider = msg.robot_provider or 'unknown'
                if provider not in breakdown:
                    breakdown[provider] = {'cost': 0, 'tokens': 0}
                breakdown[provider]['cost'] += msg.cost_usd or 0
                breakdown[provider]['tokens'] += msg.token_count or 0
            
            summary = f'Total: {total_tokens} tokens, ${total_cost:.4f}'
            if breakdown:
                summary += ' | Breakdown: '
                parts = [f'{p}: ${d["cost"]:.4f}' for p, d in breakdown.items()]
                summary += ', '.join(parts)
            
            cost_summary.text = summary
        
        ui.timer(1.0, update_cost, once=True)
