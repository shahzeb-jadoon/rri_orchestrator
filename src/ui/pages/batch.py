"""
Batch creation page with CSV upload and preview.

Upload CSV, review experiments, configure batch settings.
"""

from nicegui import ui, app
from starlette.requests import Request
from datetime import datetime
import asyncio

from src.database import User, ExperimentBatch, Experiment, RobotProfile, ExperimentQueue
from src.ui.components import create_navbar
from src.batch import parse_csv, validate_csv_format


@ui.page('/batch/create')
async def batch_create_page(request: Request):
    """Create batch from CSV with preview."""
    
    create_navbar()
    
    # Get current user from middleware
    user = getattr(request.state, 'user', None)
    
    if not user:
        ui.label('Please log in to create batches').classes('text-negative')
        return
    
    # Page header
    with ui.column().classes('w-full max-w-4xl mx-auto p-6 gap-6'):
        ui.label('Create Experiment Batch').classes('text-h4 font-bold')
        ui.label('Upload a CSV file with experiment prompts to run multiple experiments automatically.').classes('text-subtitle1 text-grey-7')
        
        ui.separator()
        
        # State for parsed results
        parse_state = {'experiments': [], 'errors': [], 'success': False}
        
        # Step 1: File Upload
        with ui.card().classes('w-full p-6'):
            ui.label('Step 1: Upload CSV File').classes('text-h6 font-bold mb-4')
            
            ui.label('CSV Format Options:').classes('text-subtitle2 font-bold mt-2')
            with ui.column().classes('text-caption text-grey-7 gap-1 mb-4'):
                ui.label('• With header: prompt,description,max_turns')
                ui.label('• Simple format: One prompt per line')
                ui.label('• Maximum 100 experiments per batch')
            
            # Containers for dynamic content
            preview_container = ui.column().classes('w-full')
            config_container = ui.column().classes('w-full')
            
            @ui.refreshable
            def show_preview():
                """Preview table of parsed experiments."""
                preview_container.clear()
                
                if not parse_state['success']:
                    return
                
                experiments = parse_state['experiments']
                errors = parse_state['errors']
                
                with preview_container:
                    with ui.card().classes('w-full p-6 mt-4'):
                        ui.label('Step 2: Review Parsed Experiments').classes('text-h6 font-bold mb-4')
                        
                        # Summary stats
                        with ui.row().classes('gap-4 mb-4'):
                            with ui.card().classes('p-4'):
                                ui.label('Total Experiments').classes('text-caption text-grey-7')
                                ui.label(str(len(experiments))).classes('text-h5 font-bold')
                            
                            with ui.card().classes('p-4'):
                                ui.label('Average Turns').classes('text-caption text-grey-7')
                                avg_turns = sum(exp['max_turns'] for exp in experiments) // len(experiments) if experiments else 0
                                ui.label(str(avg_turns)).classes('text-h5 font-bold')
                        
                        # Warnings (if any)
                        if errors:
                            with ui.expansion('Warnings', icon='warning').classes('bg-orange-100 mb-4'):
                                for error in errors:
                                    ui.label(f'• {error}').classes('text-caption')
                        
                        # Preview table
                        ui.label('Preview:').classes('text-subtitle2 font-bold mb-2')
                        
                        columns = [
                            {'name': 'row', 'label': '#', 'field': 'row', 'align': 'left'},
                            {'name': 'prompt', 'label': 'Prompt', 'field': 'prompt', 'align': 'left'},
                            {'name': 'description', 'label': 'Description', 'field': 'description', 'align': 'left'},
                            {'name': 'max_turns', 'label': 'Max Turns', 'field': 'max_turns', 'align': 'center'},
                        ]
                        
                        rows = [
                            {
                                'row': i + 1,
                                'prompt': exp['prompt'][:80] + '...' if len(exp['prompt']) > 80 else exp['prompt'],
                                'description': (exp['description'][:50] + '...' if exp['description'] and len(exp['description']) > 50 else exp['description']) or '-',
                                'max_turns': exp['max_turns']
                            }
                            for i, exp in enumerate(experiments)
                        ]
                        
                        ui.table(columns=columns, rows=rows, row_key='row').classes('w-full').props('dense')
            
            @ui.refreshable
            async def show_config():
                """Configuration form for batch settings."""
                config_container.clear()
                
                if not parse_state['success']:
                    return
                
                with config_container:
                    with ui.card().classes('w-full p-6 mt-4'):
                        ui.label('Step 3: Configure Batch Settings').classes('text-h6 font-bold mb-4')
                        
                        # Batch name
                        batch_name_input = ui.input(
                            label='Batch Name',
                            placeholder='e.g., AI Exploration Batch #1',
                            validation={'Required': lambda v: bool(v and v.strip())}
                        ).classes('w-full').props('outlined')
                        
                        # Batch description
                        batch_desc_input = ui.textarea(
                            label='Description (Optional)',
                            placeholder='Describe the purpose of this batch...'
                        ).classes('w-full mt-4').props('outlined')
                        
                        # Robot selection
                        ui.label('Robot Configuration').classes('text-subtitle2 font-bold mt-6 mb-2')
                        
                        # Fetch available robot profiles
                        robot_profiles = await RobotProfile.all()
                        
                        if len(robot_profiles) < 2:
                            ui.label('⚠️ You need at least 2 robot profiles to create a batch.').classes('text-orange')
                            ui.button('Create Robots', on_click=lambda: ui.navigate.to('/robots/create')).props('color=primary')
                            return
                        
                        profile_options = {profile.id: profile.name for profile in robot_profiles}
                        
                        with ui.row().classes('w-full gap-4'):
                            robot_a_select = ui.select(
                                label='Robot A',
                                options=profile_options,
                                value=list(profile_options.keys())[0] if profile_options else None
                            ).classes('flex-1').props('outlined')
                            
                            robot_b_select = ui.select(
                                label='Robot B',
                                options=profile_options,
                                value=list(profile_options.keys())[1] if len(profile_options) > 1 else list(profile_options.keys())[0]
                            ).classes('flex-1').props('outlined')
                        
                        # Advanced settings
                        ui.label('Advanced Settings').classes('text-subtitle2 font-bold mt-6 mb-2')
                        
                        max_concurrent_slider = ui.slider(
                            min=1,
                            max=10,
                            value=5,
                            step=1
                        ).props('label-always').classes('w-full')
                        ui.label('Max Concurrent Experiments: 5').bind_text_from(
                            max_concurrent_slider,
                            'value',
                            backward=lambda v: f'Max Concurrent Experiments: {int(v)}'
                        ).classes('text-caption text-grey-7')
                        
                        # Create batch button
                        async def create_batch():
                            """Create the experiment batch."""
                            if not batch_name_input.value or not batch_name_input.value.strip():
                                ui.notify('Please enter a batch name', type='negative')
                                return
                            
                            experiments = parse_state['experiments']
                            
                            if not experiments:
                                ui.notify('No experiments found. Please upload a CSV first.', type='negative')
                                return
                            
                            try:
                                # Get selected robots
                                robot_a = await RobotProfile.get(id=robot_a_select.value)
                                robot_b = await RobotProfile.get(id=robot_b_select.value)
                                
                                # Create batch record
                                batch = await ExperimentBatch.create(
                                    name=batch_name_input.value.strip(),
                                    description=batch_desc_input.value.strip() or None,
                                    created_by=user,
                                    total_experiments=len(experiments),
                                    max_concurrent=int(max_concurrent_slider.value),
                                    status='pending'
                                )
                                
                                # Create individual experiments
                                for i, parsed_exp in enumerate(experiments):
                                    exp = await Experiment.create(
                                        name=f"{batch.name} - Experiment {i+1}",
                                        description=parsed_exp.get('description'),
                                        created_by=user,
                                        batch=batch,
                                        batch_index=i,
                                        initial_prompt=parsed_exp['prompt'],
                                        max_turns=parsed_exp['max_turns'],
                                        robot_a_profile=robot_a,
                                        robot_b_profile=robot_b
                                    )
                                    
                                    # Add to queue for execution
                                    await ExperimentQueue.create(
                                        experiment=exp,
                                        batch=batch,
                                        priority=0,
                                        status='queued'
                                    )
                                
                                ui.notify(f'✓ Batch created with {len(experiments)} experiments!', type='positive')
                                
                                # Navigate to experiments page
                                await asyncio.sleep(1)
                                ui.navigate.to('/experiments')
                                
                            except Exception as e:
                                ui.notify(f'Error creating batch: {str(e)}', type='negative')
                        
                        ui.button('Create Batch', on_click=create_batch).props('color=primary size=lg').classes('w-full mt-6')
            
            # File upload handler
            async def handle_upload(e):
                """Handle CSV file upload and parsing."""
                try:
                    # Read file content (e.content is already bytes)
                    file_content = e.content.decode('utf-8')
                    
                    # Quick validation
                    validation = validate_csv_format(file_content)
                    if not validation["valid"]:
                        ui.notify(f'Invalid CSV: {validation["message"]}', type='negative')
                        return
                    
                    # Parse CSV
                    result = parse_csv(file_content, has_header=True)
                    
                    # Update state
                    parse_state['experiments'] = [
                        {
                            'prompt': exp.prompt,
                            'description': exp.description,
                            'max_turns': exp.max_turns
                        }
                        for exp in result.experiments
                    ]
                    parse_state['errors'] = result.errors
                    parse_state['success'] = result.success
                    
                    # Show results
                    if result.success:
                        ui.notify(f'✓ Parsed {len(result.experiments)} experiments', type='positive')
                        if result.errors:
                            ui.notify(f'⚠ {len(result.errors)} warnings', type='warning')
                        
                        # Refresh preview and config sections
                        show_preview.refresh()
                        await show_config.refresh()
                    else:
                        ui.notify(f'✗ Parsing failed: {result.errors[0] if result.errors else "Unknown error"}', type='negative')
                
                except Exception as ex:
                    ui.notify(f'Error reading file: {str(ex)}', type='negative')
            
            # File uploader
            ui.upload(
                on_upload=handle_upload,
                auto_upload=True,
                label='Choose CSV File',
                max_files=1
            ).props('accept=".csv"').classes('w-full')
        
        # Render preview and config containers
        show_preview()
        await show_config()
