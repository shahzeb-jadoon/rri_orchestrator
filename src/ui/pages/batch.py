"""
Batch experiment creation page.

This page allows researchers to upload CSV files, preview parsed experiments,
configure batch settings, and create experiment batches.
"""

from nicegui import ui, app, Client
from starlette.requests import Request
from datetime import datetime
import asyncio

from src.database import User, ExperimentBatch, Experiment, RobotProfile
from src.batch import parse_csv, validate_csv_format


# Global state for current upload session
upload_session = {
    "file_content": None,
    "parse_result": None,
    "preview_visible": False
}


@ui.page('/batch/create')
async def batch_create_page(request: Request):
    """Batch creation page with CSV upload and preview."""
    
    # Get current user from request state (set by middleware)
    user = getattr(request.state, 'user', None)
    user_email = getattr(request.state, 'user_email', None)
    
    if not user:
        ui.label('Please log in to create batches').classes('text-negative')
        ui.label(f'Debug: Email={user_email}, User={user}').classes('text-caption')
        return
    
    # Page header
    with ui.column().classes('w-full max-w-4xl mx-auto p-6 gap-6'):
        ui.label('Create Experiment Batch').classes('text-h4 font-bold')
        ui.label('Upload a CSV file with experiment prompts to run multiple experiments automatically.').classes('text-subtitle1 text-grey-7')
        
        ui.separator()
        
        # Step 1: File Upload
        with ui.card().classes('w-full p-6'):
            ui.label('Step 1: Upload CSV File').classes('text-h6 font-bold mb-4')
            
            ui.label('CSV Format Options:').classes('text-subtitle2 font-bold mt-2')
            with ui.column().classes('text-caption text-grey-7 gap-1 mb-4'):
                ui.label('• With header: prompt,description,max_turns')
                ui.label('• Simple format: One prompt per line')
                ui.label('• Maximum 100 experiments per batch')
            
            # File uploader
            upload_container = ui.column().classes('w-full')
            
            async def handle_upload(e):
                """Handle CSV file upload and parsing."""
                file_content = e.content.read().decode('utf-8')
                
                # Quick validation
                validation = validate_csv_format(file_content)
                if not validation["valid"]:
                    ui.notify(f'Invalid CSV: {validation["message"]}', type='negative')
                    return
                
                # Parse CSV
                result = parse_csv(file_content, has_header=True)
                
                # Store in session
                upload_session["file_content"] = file_content
                upload_session["parse_result"] = result
                upload_session["preview_visible"] = True
                
                # Show results
                if result.success:
                    ui.notify(f'✓ Parsed {len(result.experiments)} experiments', type='positive')
                    if result.errors:
                        ui.notify(f'⚠ {len(result.errors)} warnings', type='warning')
                    
                    # Refresh page to show preview
                    ui.navigate.reload()
                else:
                    ui.notify(f'✗ Parsing failed: {result.errors[0] if result.errors else "Unknown error"}', type='negative')
            
            with upload_container:
                ui.upload(
                    on_upload=handle_upload,
                    auto_upload=True,
                    label='Choose CSV File',
                    max_files=1
                ).props('accept=".csv"').classes('w-full')
        
        # Step 2: Preview (shown after upload)
        if upload_session.get("preview_visible") and upload_session.get("parse_result"):
            result = upload_session["parse_result"]
            
            if result.success:
                with ui.card().classes('w-full p-6 mt-4'):
                    ui.label('Step 2: Review Parsed Experiments').classes('text-h6 font-bold mb-4')
                    
                    # Summary stats
                    with ui.row().classes('gap-4 mb-4'):
                        with ui.card().classes('p-4'):
                            ui.label('Total Experiments').classes('text-caption text-grey-7')
                            ui.label(str(len(result.experiments))).classes('text-h5 font-bold')
                        
                        with ui.card().classes('p-4'):
                            ui.label('Average Turns').classes('text-caption text-grey-7')
                            avg_turns = sum(exp.max_turns for exp in result.experiments) // len(result.experiments)
                            ui.label(str(avg_turns)).classes('text-h5 font-bold')
                    
                    # Warnings (if any)
                    if result.errors:
                        with ui.expansion('Warnings', icon='warning').classes('bg-orange-100 mb-4'):
                            for error in result.errors:
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
                            'prompt': exp.prompt[:80] + '...' if len(exp.prompt) > 80 else exp.prompt,
                            'description': (exp.description[:50] + '...' if exp.description and len(exp.description) > 50 else exp.description) or '-',
                            'max_turns': exp.max_turns
                        }
                        for i, exp in enumerate(result.experiments)
                    ]
                    
                    ui.table(columns=columns, rows=rows, row_key='row').classes('w-full').props('dense')
        
        # Step 3: Configuration (shown after successful preview)
        if upload_session.get("preview_visible") and upload_session.get("parse_result") and upload_session["parse_result"].success:
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
                profile_options = [f"{profile.name}" for profile in robot_profiles]
                
                with ui.row().classes('w-full gap-4'):
                    robot_a_select = ui.select(
                        label='Robot A',
                        options=profile_options,
                        value=profile_options[0] if profile_options else None
                    ).classes('flex-1').props('outlined')
                    
                    robot_b_select = ui.select(
                        label='Robot B',
                        options=profile_options,
                        value=profile_options[1] if len(profile_options) > 1 else profile_options[0]
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
                    
                    result = upload_session["parse_result"]
                    
                    try:
                        # Create batch record
                        batch = await ExperimentBatch.create(
                            name=batch_name_input.value.strip(),
                            description=batch_desc_input.value.strip() or None,
                            created_by=user,
                            total_experiments=len(result.experiments),
                            max_concurrent=int(max_concurrent_slider.value),
                            status='pending'
                        )
                        
                        # Create individual experiments
                        for i, parsed_exp in enumerate(result.experiments):
                            await Experiment.create(
                                name=f"{batch.name} - Experiment {i+1}",
                                description=parsed_exp.description,
                                created_by=user,
                                batch=batch,
                                batch_index=i,
                                initial_prompt=parsed_exp.prompt,
                                max_turns=parsed_exp.max_turns,
                                robot_a_profile_name=robot_a_select.value,
                                robot_b_profile_name=robot_b_select.value
                            )
                        
                        # Clear session
                        upload_session.clear()
                        
                        ui.notify(f'✓ Batch created with {len(result.experiments)} experiments!', type='positive')
                        
                        # Navigate to experiments page
                        await asyncio.sleep(1)
                        ui.navigate.to('/experiments')
                        
                    except Exception as e:
                        ui.notify(f'Error creating batch: {str(e)}', type='negative')
                
                ui.button('Create Batch', on_click=create_batch).props('color=primary size=lg').classes('w-full mt-6')
