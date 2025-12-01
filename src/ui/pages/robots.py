"""
Robot profile management.

Create, edit, and delete robot profiles with AI model configs.
"""

from nicegui import ui
from starlette.requests import Request
from src.database.models import RobotProfile, User
from src.ai.model_config import get_available_models, PROVIDER_NAMES
from src.ui.components import create_navbar


@ui.page('/robots')
async def robots_list_page():
    """List all robot profiles."""
    create_navbar()
    
    ui.label('Robot Profiles').classes('text-h4')
    ui.label('Manage robot configurations').classes('text-subtitle1 text-grey')
    
    ui.space()
    
    # Create button
    ui.button('+ Create New Robot', on_click=lambda: ui.navigate.to('/robots/create')).props('color=primary')
    
    ui.space()
    
    # Load robots
    robots = await RobotProfile.all().prefetch_related('created_by')
    
    if not robots:
        with ui.card():
            ui.label('No robot profiles yet. Create your first one!').classes('text-grey')
    else:
        # Table of robots
        columns = [
            {'name': 'name', 'label': 'Name', 'field': 'name', 'align': 'left'},
            {'name': 'provider', 'label': 'AI Provider', 'field': 'provider', 'align': 'left'},
            {'name': 'model', 'label': 'Model', 'field': 'model', 'align': 'left'},
            {'name': 'temperature', 'label': 'Temperature', 'field': 'temperature', 'align': 'center'},
            {'name': 'actions', 'label': 'Actions', 'field': 'actions', 'align': 'right'},
        ]
        
        rows = [
            {
                'id': robot.id,
                'name': robot.name,
                'provider': PROVIDER_NAMES.get(robot.ai_provider, robot.ai_provider),
                'model': robot.model_name or 'Not set',
                'temperature': robot.default_temperature,
                'actions': robot.id
            }
            for robot in robots
        ]
        
        table = ui.table(columns=columns, rows=rows).classes('w-full')
        
        # Add action buttons to each row
        table.add_slot('body-cell-actions', '''
            <q-td key="actions" :props="props">
                <q-btn flat dense icon="edit" @click="$parent.$emit('edit', props.row)" />
                <q-btn flat dense icon="delete" color="red" @click="$parent.$emit('delete', props.row)" />
            </q-td>
        ''')
        
        table.on('edit', lambda e: ui.navigate.to(f'/robots/{e.args["id"]}/edit'))
        
        async def delete_robot(e):
            robot_id = e.args['id']
            await RobotProfile.filter(id=robot_id).delete()
            ui.notify(f'Robot deleted', type='positive')
            ui.navigate.to('/robots')  # Refresh page
        
        table.on('delete', delete_robot)


@ui.page('/robots/create')
async def create_robot_page(request: Request):
    """Create new robot profile."""
    create_navbar()
    
    # Get current user
    user = getattr(request.state, 'user', None)
    if not user:
        ui.label('Please log in to create robots').classes('text-negative')
        return
    
    ui.label('Create Robot Profile').classes('text-h4')
    
    ui.space()
    
    with ui.card().classes('w-full max-w-2xl'):
        # Form fields
        name_input = ui.input('Robot Name').classes('w-full').props('outlined')
        description_input = ui.textarea('Description').classes('w-full').props('outlined')
        system_prompt_input = ui.textarea('System Prompt').classes('w-full').props('outlined rows=4')
        
        # AI Configuration
        ui.label('AI Configuration').classes('text-h6 mt-4')
        
        provider_options = list(PROVIDER_NAMES.items())
        provider_select = ui.select(
            options={k: v for k, v in provider_options},
            label='AI Provider',
            value='openai'
        ).classes('w-full').props('outlined')
        
        # Model dropdown (filtered by provider)
        model_select = ui.select(
            options=get_available_models('openai'),
            label='Model',
            value='gpt-4o'
        ).classes('w-full').props('outlined')
        
        # Update model options when provider changes
        def update_models():
            models = get_available_models(provider_select.value)
            model_select.options = models
            model_select.value = models[0] if models else None
        
        provider_select.on('update:model-value', update_models)
        
        # Temperature slider
        temperature_slider = ui.slider(
            min=0.0,
            max=2.0,
            step=0.1,
            value=0.7
        ).classes('w-full')
        ui.label().bind_text_from(temperature_slider, 'value', lambda v: f'Temperature: {v:.1f}')
        
        ui.space()
        
        # Save button
        async def save_robot():
            # Create robot with current user
            await RobotProfile.create(
                name=name_input.value,
                description=description_input.value or '',
                system_prompt=system_prompt_input.value or 'You are a helpful assistant.',
                ai_provider=provider_select.value,
                model_name=model_select.value,
                default_temperature=temperature_slider.value,
                created_by=user
            )
            
            ui.notify(f'Robot "{name_input.value}" created!', type='positive')
            ui.navigate.to('/robots')
        
        with ui.row().classes('w-full justify-end gap-2'):
            ui.button('Cancel', on_click=lambda: ui.navigate.to('/robots')).props('flat')
            ui.button('Create Robot', on_click=save_robot).props('color=primary')


@ui.page('/robots/{robot_id}/edit')
async def edit_robot_page(robot_id: int):
    """
    Edit an existing robot profile.
    """
    create_navbar()
    
    # Load robot
    robot = await RobotProfile.get_or_none(id=robot_id)
    
    if not robot:
        ui.label('Robot not found').classes('text-h5 text-red')
        ui.button('Back to Robots', on_click=lambda: ui.navigate.to('/robots'))
        return
    
    ui.label(f'Edit Robot: {robot.name}').classes('text-h4')
    
    ui.space()
    
    with ui.card().classes('w-full max-w-2xl'):
        # Form fields (pre-filled)
        name_input = ui.input('Robot Name', value=robot.name).classes('w-full').props('outlined')
        description_input = ui.textarea('Description', value=robot.description or '').classes('w-full').props('outlined')
        system_prompt_input = ui.textarea('System Prompt', value=robot.system_prompt).classes('w-full').props('outlined rows=4')
        
        # AI Configuration
        ui.label('AI Configuration').classes('text-h6 mt-4')
        
        provider_options = list(PROVIDER_NAMES.items())
        provider_select = ui.select(
            options={k: v for k, v in provider_options},
            label='AI Provider',
            value=robot.ai_provider
        ).classes('w-full').props('outlined')
        
        model_select = ui.select(
            options=get_available_models(robot.ai_provider),
            label='Model',
            value=robot.model_name
        ).classes('w-full').props('outlined')
        
        def update_models():
            models = get_available_models(provider_select.value)
            model_select.options = models
            model_select.value = models[0] if models else None
        
        provider_select.on('update:model-value', update_models)
        
        temperature_slider = ui.slider(
            min=0.0,
            max=2.0,
            step=0.1,
            value=robot.default_temperature
        ).classes('w-full')
        ui.label().bind_text_from(temperature_slider, 'value', lambda v: f'Temperature: {v:.1f}')
        
        ui.space()
        
        # Update button
        async def update_robot():
            robot.name = name_input.value
            robot.description = description_input.value
            robot.system_prompt = system_prompt_input.value
            robot.ai_provider = provider_select.value
            robot.model_name = model_select.value
            robot.default_temperature = temperature_slider.value
            await robot.save()
            
            ui.notify(f'Robot "{robot.name}" updated!', type='positive')
            ui.navigate.to('/robots')
        
        with ui.row().classes('w-full justify-end gap-2'):
            ui.button('Cancel', on_click=lambda: ui.navigate.to('/robots')).props('flat')
            ui.button('Save Changes', on_click=update_robot).props('color=primary')
