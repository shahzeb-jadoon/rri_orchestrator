import streamlit as st
import os
import time
import csv
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Import our custom modules
from core import database
from config import model_config
from config.model_config import get_client
from clients.base import BaseLLMClient
from clients.gemini import GoogleGeminiClient
from clients.openai import OpenAIClient

# Load environment variables from .env file
load_dotenv()

# --- Session State Initialization ---

def initialize_all_session_state():
    """
    Initialize all session state variables with safe defaults.
    Prevents AttributeError exceptions from missing state variables.
    Must be called before any session state access.
    """
    defaults = {
        # Page navigation
        'page': 'main',
        
        # UI display
        'messages': [],
        
        # Conversation state
        'conversation_active': False,
        'paused': False,
        'mid_turn_pause': False,
        'turn_count': 0,
        'max_turns': 10,
        'limit_reached': False,
        'conversation_explicitly_ended': False,
        
        # Model tracking
        'last_speaker': None,
        'next_speaker': None,
        'model_a_history': [],
        'model_b_history': [],
        
        # Client instances
        'model_a_client': None,
        'model_b_client': None,
        
        # Experiment tracking
        'experiment_id': None,
        'current_exp_name': '',
        'continued_experiment_id': None,
        
        # History viewer
        'show_history': False,
        'selected_exp_id': None,
        
        # Researcher interaction
        'researcher_message': '',
        'researcher_target': 'both',
        'manual_override_text': '',
        'show_manual_override': False,
        
        # Model configuration
        'provider_a': None,
        'model_a': None,
        'variant_a': None,
        'prompt_a': '',
        'model_a_display': '',
        'provider_b': None,
        'model_b': None,
        'variant_b': None,
        'prompt_b': '',
        'model_b_display': '',
        'initial_prompt': '',
        
        # Authentication
        'authenticated': False,
    }
    
    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

# Initialize session state before any other code
initialize_all_session_state()

# --- Helper Functions ---

def add_message_to_ui(role: str, name: str, content: str):
    """
    Safely add a message to the UI display list.
    Handles cases where st.session_state.messages doesn't exist or is corrupted.
    
    Args:
        role: Chat role for styling ("assistant" or "user")
        name: Display name (e.g., "Gemini", "GPT-4", "Researcher")
        content: Message text
    """
    if 'messages' not in st.session_state:
        print("⚠️ WARNING: st.session_state.messages not initialized. Creating now.")
        st.session_state.messages = []
    
    if not isinstance(st.session_state.messages, list):
        print(f"⚠️ WARNING: st.session_state.messages corrupted (type: {type(st.session_state.messages)}). Resetting.")
        st.session_state.messages = []
    
    st.session_state.messages.append({
        "role": role,
        "name": name,
        "content": content
    })

# --- Authentication ---

def check_password():
    """
    Simple password protection to prevent unauthorized access.
    Uses session state to remember authentication across reruns.
    Uses a form to allow Enter key submission.
    """
    # Already authenticated in this session
    if st.session_state.get("authenticated"):
        return True
    
    # Check if password is configured
    correct_password = os.getenv("LAB_PASSWORD")
    if not correct_password:
        # Development mode - no password required
        st.warning("No LAB_PASSWORD set in .env file. Skipping authentication.")
        st.session_state.authenticated = True
        return True

    # Show login form with Enter key support
    with st.form("login_form"):
        st.subheader("🔒 Lab Access")
        password = st.text_input("Enter Lab Password", type="password")
        submitted = st.form_submit_button("Login")
        
        if submitted:
            if password == correct_password:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("❌ Incorrect password. Please try again.")
    
    return False

# --- LLM Client Factory ---

def get_llm_client(provider: str, model_variant: str) -> BaseLLMClient | None:
    """
    Factory function to instantiate the appropriate LLM client with specific model.
    Caches clients in session state to prevent re-initialization.
    Validates API keys to prevent stale client issues.
    
    Args:
        provider: Provider name ("gemini" or "openai")
        model_variant: Model key from model_config
        
    Returns:
        An instance of the appropriate client, or None if API key is missing
    """
    # Create cache key
    cache_key = f"client_{provider}_{model_variant}"
    
    # Get current API key from environment
    if provider == "gemini":
        current_api_key = os.getenv("GOOGLE_API_KEY", "")
    elif provider == "openai":
        current_api_key = os.getenv("OPENAI_API_KEY", "")
    else:
        current_api_key = ""
    
    # API key validation key
    api_key_cache_key = f"api_key_{provider}"
    stored_api_key = st.session_state.get(api_key_cache_key, "")
    
    # Return cached client only if API key hasn't changed
    if cache_key in st.session_state and current_api_key == stored_api_key:
        return st.session_state[cache_key]
    
    # Create new client using centralized factory
    try:
        client = get_client(provider, model_variant)
        # Cache the client and the API key it was created with
        st.session_state[cache_key] = client
        st.session_state[api_key_cache_key] = current_api_key
        return client
    except ValueError as e:
        st.error(f"Failed to create LLM client: {str(e)}")
        return None

# --- History Reconstruction ---

def rebuild_conversation_histories(exp: dict, non_error_messages: list) -> tuple[list, list]:
    """
    Rebuild model conversation histories from database messages.
    Critical for the "Continue Conversation" feature.
    Reconstructs the exact state of both models' conversation histories by replaying logged messages.
    
    Args:
        exp: Experiment dictionary containing model names and prompts
        non_error_messages: List of message dicts from database (excluding errors)
    
    Returns:
        Tuple of (model_a_history, model_b_history) as lists of message dicts
        Message dict format: {"role": "system"|"user"|"assistant", "content": str}
    """
    model_a_name = exp['model_a_name']
    model_b_name = exp['model_b_name']
    
    # Initialize with system prompts
    model_a_history = [{"role": "system", "content": exp['model_a_prompt']}]
    model_b_history = [{"role": "system", "content": exp['model_b_prompt']}]
    
    for msg in non_error_messages:
        role = msg['sender_role']
        content = msg['content']
        target = msg.get('target_model')
        
        # Case 1: Regular Model A response
        if role == model_a_name:
            model_a_history.append({"role": "assistant", "content": content})
            model_b_history.append({"role": "user", "content": content})
        
        # Case 2: Regular Model B response
        elif role == model_b_name:
            model_b_history.append({"role": "assistant", "content": content})
            model_a_history.append({"role": "user", "content": content})
        
        # Case 3: Initial researcher prompt (conversation starter)
        elif role == 'researcher':
            model_a_history.append({"role": "user", "content": content})
            model_b_history.append({"role": "user", "content": content})
        
        # Case 4: Researcher interjection (mid-conversation)
        elif role == 'researcher_interjection':
            formatted = f"[Researcher note: {content}]"
            
            # Use target if available, otherwise assume 'both' for backward compatibility
            if target == "model_a":
                model_a_history.append({"role": "user", "content": formatted})
            elif target == "model_b":
                model_b_history.append({"role": "user", "content": formatted})
            else:
                model_a_history.append({"role": "user", "content": formatted})
                model_b_history.append({"role": "user", "content": formatted})
        
        # Case 5: Manual overrides
        elif "(Override)" in role:
            base_role = role.replace(" (Override)", "").strip()
            
            if base_role == model_a_name:
                model_a_history.append({"role": "assistant", "content": content})
                model_b_history.append({"role": "user", "content": content})
            elif base_role == model_b_name:
                model_b_history.append({"role": "assistant", "content": content})
                model_a_history.append({"role": "user", "content": content})
            else:
                print(f"⚠️ Override for unknown model: {base_role}")
        
        # Case 6: System notifications
        elif role == 'system':
            pass
        
        # Case 7: Unknown role type
        else:
            print(f"⚠️ Unknown message role during history rebuild: '{role}'")
    
    return model_a_history, model_b_history

# --- CSV Export Functionality ---

def export_to_csv(experiment_ids=None):
    """
    Export experiment data to CSV format.
    
    Args:
        experiment_ids: List of experiment IDs to export. If None, exports all.
        
    Returns:
        CSV data as list of dicts
    """
    if experiment_ids is None:
        experiments = database.get_all_experiments()
        experiment_ids = [exp['id'] for exp in experiments]
    
    # Prepare CSV data
    csv_data = []
    
    for exp_id in experiment_ids:
        experiment = database.get_experiment_by_id(exp_id)
        if not experiment:
            continue
            
        messages = database.get_experiment_messages(exp_id)
        
        # Filter out errors before counting turns
        non_error_messages = [m for m in messages if not m.get('is_error')]
        
        # Calculate turn numbers
        turn_number = 0
        for i, msg in enumerate(non_error_messages):
            if msg['sender_role'] == 'researcher':
                turn_number = 0  # Reset for researcher intervention
            else:
                # Increment turn after Model B responds
                if i > 0 and non_error_messages[i-1]['sender_role'] != 'researcher':
                    # Check if the sender_role contains the model B name (handles overrides)
                    if experiment['model_b_name'] in msg['sender_role']:
                        turn_number += 1
            
            csv_data.append({
                'experiment_id': exp_id,
                'experiment_name': experiment.get('name', 'Unnamed'),
                'experiment_start_time': experiment['start_time'],
                'model_a_provider': experiment['model_a_name'],
                'model_a_variant': experiment.get('model_a_variant', 'default'),
                'model_b_provider': experiment['model_b_name'],
                'model_b_variant': experiment.get('model_b_variant', 'default'),
                'turn_number': turn_number,
                'speaker': msg['sender_role'],
                'timestamp': msg['timestamp'],
                'message_content': msg['content'],
                'model_a_system_prompt': experiment['model_a_prompt'],
                'model_b_system_prompt': experiment['model_b_prompt'],
                'max_turns': experiment['max_turns']
            })
    
    return csv_data

def generate_csv_file(csv_data):
    """
    Generate a downloadable CSV file from data.
    
    Args:
        csv_data: List of dicts with CSV row data
        
    Returns:
        CSV string ready for download
    """
    if not csv_data:
        return ""
    
    import io
    output = io.StringIO()
    
    fieldnames = [
        'experiment_id', 'experiment_name', 'experiment_start_time',
        'model_a_provider', 'model_a_variant', 'model_b_provider', 'model_b_variant',
        'turn_number', 'speaker', 'timestamp', 'message_content',
        'model_a_system_prompt', 'model_b_system_prompt', 'max_turns'
    ]
    
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(csv_data)
    
    return output.getvalue()

# --- Conversation History Viewer Page ---

def history_viewer_page():
    """
    Display past experiments with filtering, rename, delete, and export options.
    """
    st.title("📚 Conversation History")
    
    # Tab navigation for active and deleted experiments
    tab1, tab2 = st.tabs(["📁 Active Experiments", "🗑️ Deleted (Recoverable)"])
    
    with tab1:
        show_active_experiments()
    
    with tab2:
        show_deleted_experiments()

def show_active_experiments():
    """Display active (non-deleted) experiments with pagination."""
    # Initialize pagination state
    if 'exp_page_num' not in st.session_state:
        st.session_state.exp_page_num = 0
    
    PAGE_SIZE = 25
    total_experiments = database.get_experiment_count()
    total_pages = max(1, (total_experiments + PAGE_SIZE - 1) // PAGE_SIZE)
    current_offset = st.session_state.exp_page_num * PAGE_SIZE
    
    # Store in session state for pagination controls
    st.session_state._total_pages = total_pages
    
    # Get paginated experiments
    experiments = database.get_all_experiments(limit=PAGE_SIZE, offset=current_offset)
    
    if not experiments:
        st.info("No experiments recorded yet. Start a new conversation to create your first experiment!")
        return
    
    # Filter options
    st.subheader("🔍 Filter Experiments")
    col1, col2 = st.columns(2)
    
    with col1:
        # Get unique model combinations
        model_combos = list(set([f"{exp['model_a_name']} ↔ {exp['model_b_name']}" for exp in experiments]))
        selected_combo = st.selectbox("Filter by Model Pair", ["All"] + model_combos)
    
    with col2:
        search_term = st.text_input("Search in messages (keyword)", "")
    
    # Apply filters
    filtered_experiments = experiments
    
    if selected_combo != "All":
        model_a, model_b = selected_combo.split(" ↔ ")
        filtered_experiments = [
            exp for exp in filtered_experiments 
            if exp['model_a_name'] == model_a and exp['model_b_name'] == model_b
        ]
    
    if search_term:
        # Filter by searching message content
        filtered_ids = []
        for exp in filtered_experiments:
            messages = database.get_experiment_messages(exp['id'])
            if any(search_term.lower() in msg['content'].lower() for msg in messages):
                filtered_ids.append(exp['id'])
        filtered_experiments = [exp for exp in filtered_experiments if exp['id'] in filtered_ids]
    
    # Export buttons
    st.subheader("📥 Export Options")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📊 Export All Experiments to CSV"):
            csv_data = export_to_csv()
            csv_string = generate_csv_file(csv_data)
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
            st.download_button(
                label="⬇️ Download CSV",
                data=csv_string,
                file_name=f"rri_conversations_all_{timestamp}.csv",
                mime="text/csv"
            )
    
    with col2:
        if filtered_experiments and st.button("📊 Export Filtered Results to CSV"):
            exp_ids = [exp['id'] for exp in filtered_experiments]
            csv_data = export_to_csv(experiment_ids=exp_ids)
            csv_string = generate_csv_file(csv_data)
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
            st.download_button(
                label="⬇️ Download Filtered CSV",
                data=csv_string,
                file_name=f"rri_conversations_filtered_{timestamp}.csv",
                mime="text/csv"
            )
    
    # Display experiments table
    st.subheader(f"📋 Experiments ({len(filtered_experiments)} found)")
    
    for exp in filtered_experiments:
        exp_name = exp.get('name') or f"Experiment #{exp['id']}"
        # Attempt to show the specific model variant (human-friendly) next to the provider
        def _infer_provider_key(exp_name, variant_key):
            # Reverse-lookup by provider display name
            for pk, pv in model_config.PROVIDERS.items():
                if pv == exp_name:
                    return pk
            # Fallback: infer from variant prefix
            if variant_key:
                if variant_key.startswith('gemini'):
                    return 'gemini'
                if variant_key.startswith('gpt') or variant_key.startswith('gpt-'):
                    return 'openai'
            return None

        a_provider_key = _infer_provider_key(exp['model_a_name'], exp.get('model_a_variant'))
        b_provider_key = _infer_provider_key(exp['model_b_name'], exp.get('model_b_variant'))

        a_variant_display = model_config.get_model_display_name(a_provider_key, exp.get('model_a_variant')) if a_provider_key else (exp.get('model_a_variant') or 'default')
        b_variant_display = model_config.get_model_display_name(b_provider_key, exp.get('model_b_variant')) if b_provider_key else (exp.get('model_b_variant') or 'default')

        model_a_display = f"{a_variant_display} ({exp['model_a_name']})"
        model_b_display = f"{b_variant_display} ({exp['model_b_name']})"
        
        with st.expander(
            f"🔬 {exp_name} - {model_a_display} ↔ {model_b_display} "
            f"({exp['message_count']} messages) - {exp['start_time'][:16]}"
        ):
            # Action buttons
            col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
            
            with col1:
                # Rename button
                if st.button(f"✏️ Rename", key=f"rename_btn_{exp['id']}"):
                    st.session_state[f"renaming_{exp['id']}"] = True
                    st.rerun()
            
            with col2:
                # Continue conversation button
                if st.button(f"▶️ Continue", key=f"continue_{exp['id']}"):
                    st.session_state['continue_exp_id'] = exp['id']
                    st.session_state['page'] = 'continue'
                    st.rerun()
            
            with col3:
                # Export button
                if st.button(f"📥 Export CSV", key=f"export_{exp['id']}"):
                    csv_data = export_to_csv(experiment_ids=[exp['id']])
                    csv_string = generate_csv_file(csv_data)
                    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
                    st.download_button(
                        label=f"⬇️ Download",
                        data=csv_string,
                        file_name=f"rri_experiment_{exp['id']}_{timestamp}.csv",
                        mime="text/csv",
                        key=f"download_{exp['id']}"
                    )
            
            with col4:
                # Delete button
                if st.button(f"🗑️ Delete", key=f"delete_{exp['id']}"):
                    database.soft_delete_experiment(exp['id'])
                    st.success(f"Experiment deleted. You can recover it within 30 days.")
                    st.rerun()
            
            # Rename form
            if st.session_state.get(f"renaming_{exp['id']}", False):
                with st.form(f"rename_form_{exp['id']}"):
                    new_name = st.text_input("New name:", value=exp_name)
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.form_submit_button("💾 Save"):
                            database.rename_experiment(exp['id'], new_name)
                            st.session_state[f"renaming_{exp['id']}"] = False
                            st.success(f"Renamed to: {new_name}")
                            st.rerun()
                    with col2:
                        if st.form_submit_button("❌ Cancel"):
                            st.session_state[f"renaming_{exp['id']}"] = False
                            st.rerun()
            
            # Show experiment details
            st.markdown("---")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**ID:** {exp['id']}")
                st.markdown(f"**Started:** {exp['start_time']}")
                st.markdown(f"**Model A:** {model_a_display}")
                st.markdown(f"**Model B:** {model_b_display}")
                st.markdown(f"**Max Turns:** {exp['max_turns']}")
            
            with col2:
                st.markdown("**Model A Prompt:**")
                st.text(exp['model_a_prompt'][:100] + "..." if len(exp['model_a_prompt']) > 100 else exp['model_a_prompt'])
                st.markdown("**Model B Prompt:**")
                st.text(exp['model_b_prompt'][:100] + "..." if len(exp['model_b_prompt']) > 100 else exp['model_b_prompt'])
            
            # Show conversation
            st.markdown("---")
            st.markdown("**💬 Conversation:**")
            
            # Display system prompts first (these don't count as turns)
            with st.expander("🔧 System Prompts (expand to view)", expanded=False):
                st.markdown(f"**{a_variant_display} System Prompt:**")
                st.info(exp['model_a_prompt'])
                st.markdown(f"**{b_variant_display} System Prompt:**")
                st.info(exp['model_b_prompt'])
            
            st.markdown("---")
            
            messages = database.get_experiment_messages(exp['id'])
            
            for msg in messages:
                role = msg['sender_role']
                content = msg['content']
                timestamp = msg['timestamp'][11:19]  # Extract time only
                is_error = msg.get('is_error', 0)
                error_type = msg.get('error_type')
                
                # Map stored sender_role to full model variant display name
                display_name = role
                if role == exp['model_a_name']:
                    display_name = a_variant_display
                elif role == exp['model_b_name']:
                    display_name = b_variant_display
                elif '(Override)' in role:
                    # Handle manual overrides - extract base model name and replace
                    if exp['model_a_name'] in role:
                        display_name = role.replace(exp['model_a_name'], a_variant_display)
                    elif exp['model_b_name'] in role:
                        display_name = role.replace(exp['model_b_name'], b_variant_display)
                
                if is_error:
                    # Display error messages prominently
                    error_emoji = "⚠️" if error_type == "rate_limit" else "❌"
                    st.error(f"{error_emoji} **ERROR** ({timestamp}) [{error_type}]: {content}")
                elif role == 'researcher' or role == 'researcher_interjection':
                    st.info(f"**👤 Researcher** ({timestamp}): {content}")
                elif role == exp['model_a_name'] or exp['model_a_name'] in role:
                    st.success(f"**🤖 {display_name}** ({timestamp}): {content}")
                else:
                    st.warning(f"**🤖 {display_name}** ({timestamp}): {content}")
    
    # Pagination controls
    st.markdown("---")
    col1, col2, col3 = st.columns([2, 1, 2])
    
    with col1:
        if st.session_state.exp_page_num > 0:
            if st.button("⬅️ Previous Page"):
                st.session_state.exp_page_num -= 1
                st.rerun()
    
    with col2:
        st.markdown(f"**Page {st.session_state.exp_page_num + 1} of {st.session_state._total_pages}**")
    
    with col3:
        if st.session_state.exp_page_num < st.session_state._total_pages - 1:
            if st.button("Next Page ➡️"):
                st.session_state.exp_page_num += 1
                st.rerun()

def show_deleted_experiments():
    """Display deleted experiments that can be recovered."""
    deleted_exps = database.get_deleted_experiments()
    
    if not deleted_exps:
        st.info("No deleted experiments. Deleted experiments can be recovered for up to 30 days.")
        return
    
    st.warning(f"⚠️ {len(deleted_exps)} deleted experiment(s) found. These will be permanently deleted after 30 days.")
    
    for exp in deleted_exps:
        exp_name = exp.get('name') or f"Experiment #{exp['id']}"
        deleted_date = datetime.fromisoformat(exp['deleted_at'])
        days_until_permanent = 30 - (datetime.now() - deleted_date).days
        
        with st.expander(f"🗑️ {exp_name} - Deleted {exp['deleted_at'][:10]} ({days_until_permanent} days left)"):
            st.markdown(f"**ID:** {exp['id']}")
            st.markdown(f"**Originally Started:** {exp['start_time']}")
            st.markdown(f"**Models:** {exp['model_a_name']} ↔ {exp['model_b_name']}")
            st.markdown(f"**Messages:** {exp['message_count']}")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button(f"♻️ Recover", key=f"recover_{exp['id']}"):
                    database.recover_experiment(exp['id'])
                    st.success(f"✅ Experiment recovered!")
                    st.rerun()
            
            with col2:
                if st.button(f"⚠️ Permanently Delete", key=f"perm_delete_{exp['id']}"):
                    # This would need confirmation in production
                    st.error("Permanent deletion requires confirmation. Coming soon...")

# --- Helper Functions for Pause Control ---

def send_researcher_message(message: str, target: str):
    """
    Send a researcher interjection to one or both models.
    Does NOT count as a model's turn and does NOT change turn order.
    
    Args:
        message: The researcher's message
        target: "model_a", "model_b", or "both"
    """
    exp_id = st.session_state.experiment_id
    
    # Log to database with target information
    database.log_message(exp_id, "researcher_interjection", message, target_model=target)
    
    # Determine target display names for message
    target_display = target.upper()
    if target == "model_a":
        target_display = st.session_state.model_a_display
    elif target == "model_b":
        target_display = st.session_state.model_b_display
    elif target == "both":
        target_display = "BOTH MODELS"
    
    # Add to display messages
    add_message_to_ui("researcher", "Researcher", f"**[Interjection to {target_display}]**\n\n{message}")
    
    # Add to appropriate model histories WITHOUT changing turn order
    formatted_message = f"[Researcher note: {message}]"
    
    if st.session_state.get("mid_turn_pause", False):
        # Mid-turn: Model A responded, Model B hasn't yet
        if target == "model_a":
            st.session_state.model_a_history.append({"role": "user", "content": formatted_message})
        elif target == "model_b":
            st.session_state.model_b_history.append({"role": "user", "content": formatted_message})
        else:
            st.session_state.model_a_history.append({"role": "user", "content": formatted_message})
            st.session_state.model_b_history.append({"role": "user", "content": formatted_message})
    else:
        # Normal state: add as user messages to target models
        if target == "model_a" or target == "both":
            st.session_state.model_a_history.append({"role": "user", "content": formatted_message})
        
        if target == "model_b" or target == "both":
            st.session_state.model_b_history.append({"role": "user", "content": formatted_message})
    
    st.success(f"✅ Message sent to {target_display}. Turn order unchanged.")

def submit_manual_override(response: str, model: str, notify_model: bool = False):
    """
    Submit a manual response AS a model (instead of API call).
    This COUNTS as that model's turn and APPENDS to conversation history.
    
    Args:
        response: The manual response text
        model: "model_a" or "model_b"
        notify_model: If True, add a system message to the impersonated model
                     informing them about the researcher override
    """
    exp_id = st.session_state.experiment_id
    
    if model == "model_a":
        model_name = model_config.PROVIDERS[st.session_state.provider_a]
        model_display = st.session_state.model_a_display
        
        # Log to database with override marker
        database.log_message(exp_id, f"{model_name} (Override)", response)
        
        # Add to display
        add_message_to_ui(model_display, model_display, f"**[Manual Override]**\n\n{response}")
        
        # Update histories - Model A speaks, Model B receives it as input
        st.session_state.model_a_history.append({"role": "assistant", "content": response})
        st.session_state.model_b_history.append({"role": "user", "content": response})
        
        # Optional: Notify Model A that researcher interjected on its behalf
        if notify_model:
            system_note = (
                "Note: A researcher has interjected a message on your behalf. "
                "The previous message was not generated by you, but by the researcher. "
                "Please continue the conversation from this point, taking the researcher's input into account."
            )
            st.session_state.model_a_history.append({"role": "system", "content": system_note})
            database.log_message(exp_id, "system", f"[Notification to {model_display}] {system_note}")
        
        # Set mid-turn state: Model A just spoke, Model B should respond next
        st.session_state.mid_turn_pause = True
        st.session_state.last_speaker = model_display
        st.session_state.next_speaker = st.session_state.model_b_display
        
        # Clear pause state and prepare for Model B to respond
        st.session_state.paused = False
        st.session_state.stop_requested = False
        
        # In automatic mode, trigger Model B to respond
        if st.session_state.get("conversation_mode") == "Automatic":
            st.session_state.auto_running = True
    
    else:  # model_b
        model_name = model_config.PROVIDERS[st.session_state.provider_b]
        model_display = st.session_state.model_b_display
        
        # Log to database with override marker
        database.log_message(exp_id, f"{model_name} (Override)", response)
        
        # Add to display
        add_message_to_ui(model_display, model_display, f"**[Manual Override]**\n\n{response}")
        
        # Update histories - Model B speaks, Model A receives it as input
        st.session_state.model_b_history.append({"role": "assistant", "content": response})
        st.session_state.model_a_history.append({"role": "user", "content": response})
        
        # Optional: Notify Model B that researcher interjected on its behalf
        if notify_model:
            system_note = (
                "Note: A researcher has interjected a message on your behalf. "
                "The previous message was not generated by you, but by the researcher. "
                "Please continue the conversation from this point, taking the researcher's input into account."
            )
            st.session_state.model_b_history.append({"role": "system", "content": system_note})
            database.log_message(exp_id, "system", f"[Notification to {model_display}] {system_note}")
        
        # Model B completes the turn - increment turn count
        st.session_state.turn_count += 1
        st.session_state.mid_turn_pause = False
        
        # Clear pause state and prepare for next turn
        st.session_state.paused = False
        st.session_state.stop_requested = False
        
        # Check if limit reached
        if st.session_state.turn_count >= st.session_state.max_turns:
            st.session_state.limit_reached = True
            database.update_experiment_status(exp_id, "completed")
        else:
            # In automatic mode, continue to next turn
            if st.session_state.get("conversation_mode") == "Automatic":
                st.session_state.auto_running = True
    
    notification_status = " (notified)" if notify_model else " (not notified)"
    st.success(f"✅ Submitted as {model_display}'s response{notification_status}")

# --- Main Conversation Page ---

def conversation_page():
    """
    The main RRI conversation orchestrator interface.
    Sidebar handles experiment setup, main area displays the conversation.
    """
    st.title("🤖 RRI Conversation Orchestrator")

    # --- Sidebar: Experiment Configuration ---
    with st.sidebar:
        st.header("🔬 Experiment Setup")
        
        # Conversation Mode
        conv_mode = st.radio(
            "Conversation Mode",
            ["Automatic", "Manual"],
            help="Automatic: Runs all turns automatically (can pause anytime). Manual: Click 'Continue' after each exchange (can pause anytime)."
        )
        
        # Provider and Model Selection for Model A
        st.subheader("Model A (Starts)")
        provider_a = st.selectbox(
            "Provider A",
            ["gemini", "openai"],
            format_func=lambda x: model_config.PROVIDERS[x],
            key="select_provider_a"
        )
        
        # Get available models for selected provider
        if provider_a == "gemini":
            models_a = list(model_config.GEMINI_MODELS.keys())
            model_a_variant = st.selectbox(
                "Model A Variant",
                models_a,
                format_func=lambda x: model_config.GEMINI_MODELS[x]['display_name'],
                help=model_config.GEMINI_MODELS[models_a[0]]['description'],
                key="select_model_a_variant"
            )
        else:  # openai
            models_a = list(model_config.OPENAI_MODELS.keys())
            model_a_variant = st.selectbox(
                "Model A Variant",
                models_a,
                format_func=lambda x: model_config.OPENAI_MODELS[x]['display_name'],
                help=model_config.OPENAI_MODELS[models_a[0]]['description'],
                key="select_model_a_variant"
            )
        
        # Provider and Model Selection for Model B
        st.subheader("Model B (Responds)")
        provider_b = st.selectbox(
            "Provider B",
            ["gemini", "openai"],
            format_func=lambda x: model_config.PROVIDERS[x],
            index=1,  # Default to different provider
            key="select_provider_b"
        )
        
        if provider_b == "gemini":
            models_b = list(model_config.GEMINI_MODELS.keys())
            model_b_variant = st.selectbox(
                "Model B Variant",
                models_b,
                format_func=lambda x: model_config.GEMINI_MODELS[x]['display_name'],
                help=model_config.GEMINI_MODELS[models_b[0]]['description'],
                key="select_model_b_variant"
            )
        else:  # openai
            models_b = list(model_config.OPENAI_MODELS.keys())
            model_b_variant = st.selectbox(
                "Model B Variant",
                models_b,
                format_func=lambda x: model_config.OPENAI_MODELS[x]['display_name'],
                help=model_config.OPENAI_MODELS[models_b[0]]['description'],
                key="select_model_b_variant"
            )
        
        # Turn limit to control costs
        max_turns = st.number_input(
            "Set Max Turns", 
            min_value=1, 
            max_value=50, 
            value=5,
            help="Each turn consists of one response from each model."
        )
        
        # Experiment name
        default_name = f"{model_config.PROVIDERS[provider_a]} vs {model_config.PROVIDERS[provider_b]}"
        experiment_name = st.text_input("Experiment Name (optional)", value=default_name)

        # Initial System Prompts
        st.subheader("System Prompts")
        model_a_display = model_config.get_model_display_name(provider_a, model_a_variant)
        model_b_display = model_config.get_model_display_name(provider_b, model_b_variant)
        
        prompt_a = st.text_area(
            "System Prompt for Model A", 
            f"You are {model_a_display}. You are having a conversation with {model_b_display}. Keep your responses brief and concise (2-3 sentences). Engage in a thoughtful discussion.", 
            height=100
        )
        prompt_b = st.text_area(
            "System Prompt for Model B", 
            f"You are {model_b_display}. You are having a conversation with {model_a_display}. Keep your responses brief and concise (2-3 sentences). Engage in a thoughtful discussion.", 
            height=100
        )

        if st.button("🚀 Start New Experiment"):
            # Create a new experiment in the database
            exp_id = database.create_experiment(
                model_config.PROVIDERS[provider_a],
                model_config.PROVIDERS[provider_b],
                prompt_a,
                prompt_b,
                max_turns,
                model_a_variant=model_a_variant,
                model_b_variant=model_b_variant,
                name=experiment_name
            )
            
            # Reset the session state for the new chat
            st.session_state.messages = []
            st.session_state.experiment_id = exp_id
            st.session_state.experiment_name = experiment_name
            st.session_state.provider_a = provider_a
            st.session_state.provider_b = provider_b
            st.session_state.model_a_variant = model_a_variant
            st.session_state.model_b_variant = model_b_variant
            st.session_state.model_a_display = model_a_display
            st.session_state.model_b_display = model_b_display
            st.session_state.model_a_history = [{"role": "system", "content": prompt_a}]
            st.session_state.model_b_history = [{"role": "system", "content": prompt_b}]
            st.session_state.turn_count = 0
            st.session_state.max_turns = max_turns
            st.session_state.limit_reached = False
            st.session_state.conversation_mode = conv_mode
            st.session_state.auto_running = False
            st.session_state.stop_requested = False
            st.session_state.paused = False
            st.session_state.mid_turn_pause = False
            st.session_state.pause_after_turn = False
            st.session_state.last_speaker = None
            st.success(f"✅ Started experiment #{exp_id}: {experiment_name}")
            st.rerun()

    # --- Main Chat Interface ---
    
    if "messages" not in st.session_state:
        st.info("👈 Set up a new experiment in the sidebar to begin.")
        return

    # Display current experiment info
    st.markdown(
        f"**Experiment:** {st.session_state.get('experiment_name', 'Unnamed')} (#{st.session_state.experiment_id}) | "
        f"**Mode:** {st.session_state.get('conversation_mode', 'Automatic')} | "
        f"**Turn:** {st.session_state.turn_count}/{st.session_state.max_turns}"
    )

    # Display the conversation history
    for message in st.session_state.messages:
        role = message["role"]
        # Create a more visible name for the chat message
        if role == "researcher":
            display_role = "👤 Researcher"
        elif role == st.session_state.get("model_a_display"):
            display_role = f"🤖 {role}"
        elif role == st.session_state.get("model_b_display"):
            display_role = f"🤖 {role}"
        else:
            display_role = role
        
        with st.chat_message(role):
            # Show the model name prominently above the message
            if role != "researcher" and role != "error":
                st.markdown(f"**{display_role}**")
            st.markdown(message["content"])

    # Pause buttons - shows when conversation is active (not paused)
    conversation_active = (
        (st.session_state.get("conversation_mode") == "Automatic" and st.session_state.get("auto_running", False)) or
        (st.session_state.turn_count > 0 and not st.session_state.get("paused", False))
    )
    
    if conversation_active and not st.session_state.get("paused", False):
        col1, col2 = st.columns(2)
        with col1:
            if st.button("⏸️ Pause Now", key="pause_now_btn", help="Pause immediately (may interrupt mid-turn)"):
                st.session_state.paused = True
                st.session_state.auto_running = False
                st.session_state.stop_requested = True
                st.warning("⏸️ Conversation paused immediately.")
                # Let run_conversation_turn handle the rerun after setting mid_turn_pause
        with col2:
            # Only show "Pause after turn" if not already set to pause after turn
            if not st.session_state.get("pause_after_turn", False):
                if st.button("⏸️ Pause After Turn", key="pause_after_turn_btn", help="Complete current turn, then pause"):
                    st.session_state.pause_after_turn = True
                    # Don't stop auto_running - let the turn complete first
                    st.info("⏸️ Will pause after current turn completes...")
                    st.rerun()
            else:
                st.info("⏸️ Pausing after turn...")

    # Pause Control Panel - shows when paused
    if st.session_state.get("paused", False):
        st.markdown("---")
        st.subheader("⏸️ Conversation Paused")
        
        # Show last speaker info if mid-turn pause
        if st.session_state.get("mid_turn_pause", False) and st.session_state.get("last_speaker"):
            st.info(f"⚠️ Paused after {st.session_state.last_speaker}'s response. {st.session_state.get('next_speaker', 'Next model')} hasn't responded yet.")
        
        # === DEBUG PANEL: State Machine Diagnostics ===
        with st.expander("🔍 Debug: State Machine Info", expanded=False):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("**🔢 Turn Metrics**")
                st.text(f"Current Turn: {st.session_state.turn_count}")
                st.text(f"Max Turns: {st.session_state.max_turns}")
                st.text(f"Progress: {st.session_state.turn_count}/{st.session_state.max_turns}")
            
            with col2:
                st.markdown("**👥 Speakers**")
                st.text(f"Last: {st.session_state.get('last_speaker', 'None')}")
                st.text(f"Next: {st.session_state.get('next_speaker', 'None')}")
                st.text(f"Model A: {st.session_state.model_a_display}")
                st.text(f"Model B: {st.session_state.model_b_display}")
            
            with col3:
                st.markdown("**🚦 State Flags**")
                mid_turn = st.session_state.get('mid_turn_pause', False)
                paused = st.session_state.get('paused', False)
                auto = st.session_state.get('auto_running', False)
                stop_req = st.session_state.get('stop_requested', False)
                
                st.text(f"mid_turn_pause: {'✅' if mid_turn else '❌'}")
                st.text(f"paused: {'✅' if paused else '❌'}")
                st.text(f"auto_running: {'✅' if auto else '❌'}")
                st.text(f"stop_requested: {'✅' if stop_req else '❌'}")
            
            # Interpretation
            st.markdown("**📊 State Interpretation**")
            if mid_turn:
                st.warning(f"⚠️ **Mid-Turn Pause**: Model A ({st.session_state.model_a_display}) completed, Model B ({st.session_state.model_b_display}) needs to respond.")
                st.caption(f"On resume, will skip Model A and go straight to Model B.")
            else:
                st.success(f"✅ **Full-Turn Pause**: Complete turn finished. Next turn will start with Model A.")
        
        # Control Panel Tabs
        if st.session_state.get("conversation_explicitly_ended", False):
            st.info("✅ Conversation ended. Click to resume with all previous messages.")
            if st.button("📖 Continue Conversation", key="continue_after_end"):
                st.session_state.conversation_explicitly_ended = False
                
                # Reload messages from database
                all_messages = database.get_experiment_messages(st.session_state.experiment_id)
                exp = database.get_experiment_by_id(st.session_state.experiment_id)
                
                if exp and all_messages:
                    model_a_name = exp['model_a_name']
                    model_b_name = exp['model_b_name']
                    non_error_messages = [m for m in all_messages if not m.get('is_error')]
                    
                    _, st.session_state.model_a_history = rebuild_conversation_histories(exp, non_error_messages)
                    st.session_state.model_b_history, _ = rebuild_conversation_histories(exp, non_error_messages)
                
                st.rerun()
        else:
            tab1, tab2, tab3, tab4 = st.tabs(["▶️ Resume", "💬 Researcher Interjection", "✍️ Manual Override", "⚙️ Settings"])
            
            with tab1:
                st.markdown("### Resume Conversation")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("▶️ Resume", help="Continue from where you left off"):
                        st.session_state.paused = False
                        st.session_state.stop_requested = False
                        if st.session_state.get("conversation_mode") == "Automatic":
                            st.session_state.auto_running = True
                        st.rerun()
                with col2:
                    if st.button("🛑 End Conversation", help="End experiment"):
                        st.session_state.conversation_explicitly_ended = True
                        database.update_experiment_status(st.session_state.experiment_id, "paused")
                        st.session_state.model_a_history = []
                        st.session_state.model_b_history = []
                        st.rerun()
            
            with tab2:
                st.markdown("### 💬 Send Message as Researcher")
                st.caption("Send a message to one or both models. This does NOT count as a model's turn.")
                
                researcher_msg = st.text_area("Your message:", key="researcher_interjection", height=100)
                
                if researcher_msg:
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if st.button(f"→ Send to {st.session_state.model_a_display} only"):
                            send_researcher_message(researcher_msg, target="model_a")
                            st.rerun()
                    with col2:
                        if st.button(f"→ Send to {st.session_state.model_b_display} only"):
                            send_researcher_message(researcher_msg, target="model_b")
                            st.rerun()
                    with col3:
                        if st.button("→ Send to BOTH models"):
                            send_researcher_message(researcher_msg, target="both")
                            st.rerun()
            
            with tab3:
                st.markdown("### ✍️ Respond AS a Model")
                st.caption("Type a response instead of calling the API. This COUNTS as that model's turn.")
                
                if st.session_state.get("mid_turn_pause", False):
                    next_model = "model_b" if st.session_state.get("last_speaker") == st.session_state.model_a_display else "model_a"
                    next_model_name = st.session_state.model_b_display if next_model == "model_b" else st.session_state.model_a_display
                else:
                    next_model = "model_a"
                    next_model_name = st.session_state.model_a_display
                
                st.info(f"ℹ️ Next to respond: **{next_model_name}**")
                
                manual_response = st.text_area(f"Respond as {next_model_name}:", key="manual_override", height=150)
                notify_model = st.checkbox(
                    f"Notify {next_model_name} about researcher override",
                    value=False,
                    key="notify_override"
                )
                
                if manual_response:
                    if st.button(f"✅ Submit as {next_model_name}'s response"):
                        submit_manual_override(manual_response, next_model, notify_model)
                        st.rerun()
            
            with tab4:
                st.markdown("### ⚙️ Conversation Settings")
                
                st.markdown("**Switch Mode:**")
                current_mode = st.session_state.get("conversation_mode", "Automatic")
                new_mode = st.radio(
                    "Conversation Mode",
                    ["Automatic", "Manual"],
                    index=0 if current_mode == "Automatic" else 1,
                    key="mode_switcher"
                )
                if new_mode != current_mode:
                    if st.button("💾 Apply Mode Change"):
                        st.session_state.conversation_mode = new_mode
                        st.success(f"✅ Switched to {new_mode} mode")
                        st.rerun()
                
                st.markdown("---")
                st.markdown("**Adjust Turn Limit:**")
                col1, col2 = st.columns([2, 1])
                with col1:
                    min_turns = max(st.session_state.turn_count + 1, st.session_state.max_turns)
                    new_max_turns = st.number_input(
                        "Maximum Turns",
                        min_value=min_turns,
                        value=max(st.session_state.max_turns, min_turns),
                        step=1,
                        key="turn_adjuster"
                    )
                with col2:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("💾 Update Limit"):
                        st.session_state.max_turns = new_max_turns
                        st.success(f"✅ Turn limit set to {new_max_turns}")
                        st.rerun()
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("➕ Add 1 turn"):
                        st.session_state.max_turns += 1
                        st.rerun()
                with col2:
                    if st.button("➕ Add 5 turns"):
                        st.session_state.max_turns += 5
                        st.rerun()
                with col3:
                    if st.button("➕ Add 10 turns"):
                        st.session_state.max_turns += 10
                        st.rerun()

        
        st.markdown("---")
        return  # Don't show other controls when paused

    # Check if the turn limit has been reached
    if st.session_state.get("limit_reached", False):
        st.info("🏁 Turn limit reached.")
        
        # Dynamic turn adjustment
        st.markdown("**Add more turns to continue:**")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            if st.button("➕ Add 1 turn"):
                st.session_state.max_turns += 1
                st.session_state.limit_reached = False
                # Auto-resume if in automatic mode
                if st.session_state.get("conversation_mode") == "Automatic":
                    st.session_state.auto_running = True
                st.rerun()
        with col2:
            if st.button("➕ Add 5 turns"):
                st.session_state.max_turns += 5
                st.session_state.limit_reached = False
                # Auto-resume if in automatic mode
                if st.session_state.get("conversation_mode") == "Automatic":
                    st.session_state.auto_running = True
                st.rerun()
        with col3:
            if st.button("➕ Add 10 turns"):
                st.session_state.max_turns += 10
                st.session_state.limit_reached = False
                # Auto-resume if in automatic mode
                if st.session_state.get("conversation_mode") == "Automatic":
                    st.session_state.auto_running = True
                st.rerun()
        with col4:
            custom_turns = st.number_input("Custom:", min_value=1, value=5, step=1, key="custom_turns")
            if st.button(f"➕ Add {custom_turns}"):
                st.session_state.max_turns += custom_turns
                st.session_state.limit_reached = False
                # Auto-resume if in automatic mode
                if st.session_state.get("conversation_mode") == "Automatic":
                    st.session_state.auto_running = True
                st.rerun()
        
        if st.button("✅ End Experiment"):
            database.update_experiment_status(st.session_state.experiment_id, "completed")
            st.success("Experiment completed! View it in the 'History' tab.")
            st.session_state.messages = []
        return

    # Allow starting conversation without researcher message
    # Check if this is the first turn and no researcher message yet
    if st.session_state.turn_count == 0 and len(st.session_state.messages) == 0:
        # Verify experiment is properly initialized before showing start button
        if not all(key in st.session_state for key in ['model_a_variant', 'model_b_variant', 'provider_a', 'provider_b']):
            st.warning("⚠️ Please complete the experiment setup in the sidebar before starting the conversation.")
            return
        
        col1, col2 = st.columns([3, 1])
        with col1:
            user_prompt = st.chat_input("Optional: Add an initial topic/question, or leave empty to let models start...")
        with col2:
            if st.button("🚀 Start Conversation", help="Start with system prompts only"):
                # No user message - models will use only their system prompts
                if st.session_state.get("conversation_mode") == "Automatic":
                    st.session_state.auto_running = True
                    st.rerun()
                else:
                    # Manual mode - run first turn
                    run_conversation_turn()
                    st.rerun()
        
        # If user provides initial prompt
        if user_prompt:
            exp_id = st.session_state.experiment_id
            
            # Log and display researcher's message
            database.log_message(exp_id, "researcher", user_prompt)
            add_message_to_ui("researcher", "Researcher", user_prompt)
            
            # Add to both models' histories
            st.session_state.model_a_history.append({"role": "user", "content": user_prompt})
            st.session_state.model_b_history.append({"role": "user", "content": user_prompt})
            
            with st.chat_message("researcher"):
                st.markdown(user_prompt)

            # Determine if we should run automatically
            if st.session_state.get("conversation_mode") == "Automatic":
                st.session_state.auto_running = True
                st.rerun()
    else:
        # Continue button for manual mode after first turn
        if st.session_state.get("conversation_mode") == "Manual":
            if st.button("▶️ Continue Conversation"):
                run_conversation_turn()
                st.rerun()

    # Automatic conversation loop
    if st.session_state.get("auto_running", False) and not st.session_state.get("stop_requested", False):
        run_conversation_turn()

# --- Conversation Turn Logic ---

def run_conversation_turn():
    """
    Execute one complete conversation turn (Model A + Model B).
    Handles mid-turn resume (skips to Model B if Model A already responded).
    """
    exp_id = st.session_state.experiment_id
    
    # Reset status to in_progress
    database.update_experiment_status(exp_id, "in_progress")
    
    # Display turn indicator
    current_turn = st.session_state.turn_count + 1
    
    # Check if we're starting a new turn and already at the limit
    if not st.session_state.get("mid_turn_pause", False) and st.session_state.turn_count >= st.session_state.max_turns:
        st.session_state.limit_reached = True
        st.session_state.auto_running = False
        st.info(f"🏁 Turn limit reached at turn {st.session_state.max_turns}.")
        st.rerun()
        return
    
    st.info(f"🔄 **Processing Turn {current_turn}/{st.session_state.max_turns}**")
    
    # Get cached clients
    client_a = get_llm_client(st.session_state.provider_a, st.session_state.model_a_variant)
    client_b = get_llm_client(st.session_state.provider_b, st.session_state.model_b_variant)

    if not client_a or not client_b:
        st.error("❌ Failed to initialize LLM clients. Check API keys.")
        st.session_state.auto_running = False
        return

    # Check if we're resuming mid-turn (Model A already responded)
    skip_model_a = st.session_state.get("mid_turn_pause", False) and st.session_state.get("last_speaker") == st.session_state.model_a_display
    
    # === MODEL A'S RESPONSE ===
    if not skip_model_a:
        
        # Set state BEFORE API call to make operation atomic
        st.session_state.last_speaker = st.session_state.model_a_display
        st.session_state.next_speaker = st.session_state.model_b_display
        st.session_state.mid_turn_pause = True
        
        with st.chat_message(st.session_state.model_a_display):
            with st.spinner(f"🤔 {st.session_state.model_a_display} is thinking... (Turn {current_turn})"):
                try:
                    response_a = client_a.generate_response(st.session_state.model_a_history)
                    
                    # Defensive check: ensure response is not None
                    if response_a is None:
                        raise ValueError(f"{st.session_state.model_a_display} returned None response")
                    
                    # Log and display
                    database.log_message(exp_id, model_config.PROVIDERS[st.session_state.provider_a], response_a)
                    add_message_to_ui(st.session_state.model_a_display, st.session_state.model_a_display, response_a)
                    
                    # Update histories
                    st.session_state.model_a_history.append({"role": "assistant", "content": response_a})
                    st.session_state.model_b_history.append({"role": "user", "content": response_a})
                    
                    st.markdown(response_a)

                except Exception as e:
                    error_msg = f"Error from {st.session_state.model_a_display}: {str(e)}"
                    st.error(f"❌ {error_msg}")
                    
                    error_type = "api_error"
                    if "rate" in str(e).lower() or "quota" in str(e).lower() or "limit" in str(e).lower():
                        error_type = "rate_limit"
                    elif "timeout" in str(e).lower() or "connection" in str(e).lower():
                        error_type = "network_error"
                    
                    database.log_message(exp_id, st.session_state.model_a_display, error_msg, is_error=True, error_type=error_type)
                    database.update_experiment_status(exp_id, "error")
                    add_message_to_ui("error", "Error", f"{error_msg} (Type: {error_type})")
                    
                    # Error: reset to clean state
                    st.session_state.mid_turn_pause = False
                    st.session_state.last_speaker = None
                    st.session_state.next_speaker = st.session_state.model_a_display
                    st.session_state.auto_running = False
                    st.session_state.paused = True
                    st.rerun()
                    return

        # Check if pause was requested after Model A
        if st.session_state.get("stop_requested", False):
            st.session_state.paused = True
            st.session_state.auto_running = False
            st.session_state.stop_requested = False
            st.warning(f"⏸️ Paused after {st.session_state.model_a_display}'s response.")
            st.rerun()
            return
    else:
        # Skipping Model A (resuming from pause)
        st.info(f"ℹ️ Resuming from Model B (Model A already responded)")

    # Small delay for automatic mode visibility
    if st.session_state.get("conversation_mode") == "Automatic":
        time.sleep(1)

    # === MODEL B'S RESPONSE ===
    with st.chat_message(st.session_state.model_b_display):
        with st.spinner(f"🤔 {st.session_state.model_b_display} is thinking... (Turn {current_turn})"):
            try:
                # Set state BEFORE API call
                st.session_state.last_speaker = st.session_state.model_b_display
                st.session_state.next_speaker = st.session_state.model_a_display
                
                response_b = client_b.generate_response(st.session_state.model_b_history)
                
                # Defensive check: ensure response is not None
                if response_b is None:
                    raise ValueError(f"{st.session_state.model_b_display} returned None response")
                
                # Log and display
                database.log_message(exp_id, model_config.PROVIDERS[st.session_state.provider_b], response_b)
                add_message_to_ui(st.session_state.model_b_display, st.session_state.model_b_display, response_b)
                
                # Update histories
                st.session_state.model_b_history.append({"role": "assistant", "content": response_b})
                st.session_state.model_a_history.append({"role": "user", "content": response_b})
                
                st.markdown(response_b)

                # Turn is now successfully complete
                st.session_state.turn_count += 1
                st.session_state.mid_turn_pause = False
                
                # Check limit BEFORE pause
                if st.session_state.turn_count >= st.session_state.max_turns:
                    st.session_state.limit_reached = True
                    st.session_state.auto_running = False
                    database.update_experiment_status(exp_id, "completed")
                    st.rerun()
                    return
                
                # Check if "pause after turn" was requested
                if st.session_state.get("pause_after_turn", False):
                    st.session_state.paused = True
                    st.session_state.auto_running = False
                    st.session_state.pause_after_turn = False
                    st.success("✅ Turn completed. Conversation paused.")
                    st.rerun()
                    return
                
                # Continue automatic mode
                if st.session_state.get("conversation_mode") == "Automatic" and not st.session_state.get("stop_requested", False):
                    time.sleep(1)
                    st.rerun()

            except Exception as e:
                error_msg = f"Error from {st.session_state.model_b_display}: {str(e)}"
                st.error(f"❌ {error_msg}")
                
                error_type = "api_error"
                if "rate" in str(e).lower() or "quota" in str(e).lower() or "limit" in str(e).lower():
                    error_type = "rate_limit"
                elif "timeout" in str(e).lower() or "connection" in str(e).lower():
                    error_type = "network_error"
                
                database.log_message(exp_id, st.session_state.model_b_display, error_msg, is_error=True, error_type=error_type)
                database.update_experiment_status(exp_id, "error")
                add_message_to_ui("error", "Error", f"{error_msg} (Type: {error_type})")
                
                # Model B failed but Model A succeeded - preserve mid-turn state
                st.session_state.mid_turn_pause = True
                st.session_state.last_speaker = st.session_state.model_a_display
                st.session_state.next_speaker = st.session_state.model_b_display
                st.session_state.auto_running = False
                st.session_state.paused = True
                st.rerun()
                return

# --- Continue Conversation Page ---

def continue_conversation_page():
    """
    Resume a conversation from history.
    """
    exp_id = st.session_state.get('continue_exp_id')
    
    if not exp_id:
        st.error("No experiment selected to continue.")
        if st.button("← Back to History"):
            st.session_state['page'] = 'history'
            st.rerun()
        return
    
    # Get experiment details
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM experiments WHERE id = ?", (exp_id,))
    exp = dict(cursor.fetchone())
    conn.close()
    
    st.title(f"▶️ Continue: {exp.get('name') or f'Experiment #{exp_id}'}")

    # Show specific model variant details for clarity
    def _infer_provider_key(exp_name, variant_key):
        for pk, pv in model_config.PROVIDERS.items():
            if pv == exp_name:
                return pk
        if variant_key:
            if variant_key.startswith('gemini'):
                return 'gemini'
            if variant_key.startswith('gpt') or variant_key.startswith('gpt-'):
                return 'openai'
        return None

    a_pk = _infer_provider_key(exp.get('model_a_name'), exp.get('model_a_variant'))
    b_pk = _infer_provider_key(exp.get('model_b_name'), exp.get('model_b_variant'))

    a_var_disp = model_config.get_model_display_name(a_pk, exp.get('model_a_variant')) if a_pk else (exp.get('model_a_variant') or 'default')
    b_var_disp = model_config.get_model_display_name(b_pk, exp.get('model_b_variant')) if b_pk else (exp.get('model_b_variant') or 'default')

    st.markdown(f"**Models:** {a_var_disp} ({exp.get('model_a_name')}) ↔ {b_var_disp} ({exp.get('model_b_name')})")
    
    # Navigation back
    if st.button("← Back to History"):
        st.session_state['page'] = 'history'
        del st.session_state['continue_exp_id']
        st.rerun()
    
    st.markdown("---")
    
    # Display existing conversation
    st.subheader("📜 Previous Conversation")
    
    # Display system prompts first (these don't count as turns)
    with st.expander("🔧 System Prompts (expand to view)", expanded=False):
        st.markdown(f"**{a_var_disp} System Prompt:**")
        st.info(exp.get('model_a_prompt'))
        st.markdown(f"**{b_var_disp} System Prompt:**")
        st.info(exp.get('model_b_prompt'))
    
    st.markdown("---")
    
    messages = database.get_experiment_messages(exp_id)
    
    for msg in messages:
        role = msg['sender_role']
        content = msg['content']
        is_error = msg.get('is_error', 0)
        error_type = msg.get('error_type')
        
        # Map stored sender_role to full model variant display name
        display_name = role
        if role == exp.get('model_a_name'):
            display_name = a_var_disp
        elif role == exp.get('model_b_name'):
            display_name = b_var_disp
        elif '(Override)' in role:
            # Handle manual overrides - extract base model name and replace
            if exp.get('model_a_name') in role:
                display_name = role.replace(exp.get('model_a_name'), a_var_disp)
            elif exp.get('model_b_name') in role:
                display_name = role.replace(exp.get('model_b_name'), b_var_disp)
        
        with st.chat_message("assistant" if role != "researcher" and role != "researcher_interjection" else "user"):
            if is_error:
                st.error(f"❌ [{error_type}] {content}")
            else:
                st.markdown(f"**{display_name}**: {content}")
    
    # Load conversation state if not already loaded
    if 'continued_experiment_id' not in st.session_state or st.session_state['continued_experiment_id'] != exp_id:
        st.session_state['continued_experiment_id'] = exp_id
        st.session_state['experiment_id'] = exp_id
        
        # Initialize messages list for live UI updates
        st.session_state.messages = []
        
        # Restore providers and models with fallback for old/custom experiments
        try:
            st.session_state.provider_a = list(model_config.PROVIDERS.keys())[list(model_config.PROVIDERS.values()).index(exp['model_a_name'])]
        except ValueError:
            # Old experiment with custom model name - default to gemini
            st.warning(f"⚠️ Model A '{exp['model_a_name']}' not found in current config. Defaulting to Gemini.")
            st.session_state.provider_a = 'gemini'
        
        try:
            st.session_state.provider_b = list(model_config.PROVIDERS.keys())[list(model_config.PROVIDERS.values()).index(exp['model_b_name'])]
        except ValueError:
            # Old experiment with custom model name - default to openai
            st.warning(f"⚠️ Model B '{exp['model_b_name']}' not found in current config. Defaulting to OpenAI.")
            st.session_state.provider_b = 'openai'
        
        st.session_state.model_a_variant = exp.get('model_a_variant') or 'gemini-2.5-flash'
        st.session_state.model_b_variant = exp.get('model_b_variant') or 'gpt-4o-mini'
        st.session_state.model_a_display = model_config.get_model_display_name(st.session_state.provider_a, st.session_state.model_a_variant)
        st.session_state.model_b_display = model_config.get_model_display_name(st.session_state.provider_b, st.session_state.model_b_variant)
        
        # Restore max turns and current turn count
        st.session_state.max_turns = exp['max_turns']
        
        # Count non-error messages to get turn count
        non_error_messages = [m for m in messages if not m.get('is_error', 0)]
        researcher_messages = [m for m in non_error_messages if m['sender_role'] == 'researcher']
        st.session_state.turn_count = (len(non_error_messages) - len(researcher_messages)) // 2
        
        # Rebuild conversation histories using robust function (CRITICAL FIX)
        st.session_state.model_a_history, st.session_state.model_b_history = \
            rebuild_conversation_histories(exp, non_error_messages)
        
        # Determine next speaker based on message history
        if non_error_messages:
            last_msg = non_error_messages[-1]
            last_role = last_msg['sender_role']
            
            if last_role == exp['model_a_name'] or f"{exp['model_a_name']} (Override)" in last_role:
                st.session_state.next_speaker = st.session_state.model_b_display
                st.session_state.last_speaker = st.session_state.model_a_display
                st.session_state.mid_turn_pause = True
            elif last_role == exp['model_b_name'] or f"{exp['model_b_name']} (Override)" in last_role:
                st.session_state.next_speaker = st.session_state.model_a_display
                st.session_state.last_speaker = st.session_state.model_b_display
                st.session_state.mid_turn_pause = False
            else:
                st.session_state.next_speaker = st.session_state.model_a_display
                st.session_state.last_speaker = None
                st.session_state.mid_turn_pause = False
        else:
            st.session_state.next_speaker = st.session_state.model_a_display
            st.session_state.last_speaker = None
            st.session_state.mid_turn_pause = False
        
        # Initialize clients
        st.session_state.client_a = get_llm_client(st.session_state.provider_a, st.session_state.model_a_variant)
        st.session_state.client_b = get_llm_client(st.session_state.provider_b, st.session_state.model_b_variant)
        
        # Update status to in_progress
        database.update_experiment_status(exp_id, "in_progress")
    
    st.markdown("---")
    st.subheader("➕ Continue the Conversation")
    
    # Show current state
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Current Turn", st.session_state.turn_count)
    with col2:
        st.metric("Max Turns", st.session_state.max_turns)
    with col3:
        remaining = st.session_state.max_turns - st.session_state.turn_count
        st.metric("Remaining", remaining)
    
    # Check if can continue
    if st.session_state.turn_count >= st.session_state.max_turns:
        st.warning("⚠️ This experiment has reached its maximum turn limit.")
        st.info("You can increase the max turns to continue:")
        new_max = st.number_input("New max turns", min_value=st.session_state.turn_count + 1, value=st.session_state.max_turns + 5)
        if st.button("Update Max Turns"):
            conn = database.get_db_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE experiments SET max_turns = ? WHERE id = ?", (new_max, exp_id))
            conn.commit()
            conn.close()
            st.session_state.max_turns = new_max
            st.success(f"Max turns updated to {new_max}")
            st.rerun()
        return
    
    # Continue button
    if st.button("▶️ Continue for One Turn", type="primary"):
        run_conversation_turn()
        st.rerun()
    
    # Auto-continue option
    if st.button("⚡ Continue Until Max Turns (Automatic)"):
        st.session_state.auto_running = True
        st.rerun()
    
    # Handle automatic continuation
    if st.session_state.get("auto_running", False):
        if st.session_state.turn_count < st.session_state.max_turns:
            run_conversation_turn()
            time.sleep(1)
            st.rerun()
        else:
            st.session_state.auto_running = False
            database.update_experiment_status(exp_id, "completed")
            st.success("✅ Conversation completed!")

# --- Main App with Page Navigation ---

def main_app():
    """
    Main application with page navigation.
    """
    st.set_page_config(page_title="RRI Orchestrator", layout="wide", page_icon="🤖")
    
    # Check for continue mode
    if st.session_state.get('page') == 'continue':
        continue_conversation_page()
        return
    
    # Page navigation
    page = st.sidebar.radio("📍 Navigation", ["💬 New Conversation", "📚 View History"])
    
    if page == "💬 New Conversation":
        conversation_page()
    elif page == "📚 View History":
        history_viewer_page()

# --- App Entry Point ---

if __name__ == "__main__":
    # Ensure database tables exist before running the app
    database.setup_database()
    
    # Optionally clean up old deleted experiments (could run this on a schedule)
    # database.permanently_delete_old_experiments()
    
    if check_password():
        main_app()
