import streamlit as st
import os
import time
import csv
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Import our custom modules
from core import database
from config import model_config
from clients.base import BaseLLMClient
from clients.gemini import GoogleGeminiClient
from clients.openai import OpenAIClient

# Load environment variables from .env file
load_dotenv()

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
    
    Args:
        provider: Provider name ("gemini" or "openai")
        model_variant: Model key from model_config
        
    Returns:
        An instance of the appropriate client, or None if API key is missing
    """
    # Create cache key
    cache_key = f"client_{provider}_{model_variant}"
    
    # Return cached client if available
    if cache_key in st.session_state:
        return st.session_state[cache_key]
    
    # Create new client
    client = None
    
    if provider == "gemini":
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            st.error("GOOGLE_API_KEY not found in .env file.")
            return None
        model_id = model_config.get_model_id("gemini", model_variant)
        client = GoogleGeminiClient(api_key=api_key, model_id=model_id)
    
    elif provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            st.error("OPENAI_API_KEY not found in .env file.")
            return None
        model_id = model_config.get_model_id("openai", model_variant)
        client = OpenAIClient(api_key=api_key, model_id=model_id)
    
    # Cache the client
    if client:
        st.session_state[cache_key] = client
    
    return client

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
        
        # Calculate turn numbers
        turn_number = 0
        for i, msg in enumerate(messages):
            if msg['sender_role'] == 'researcher':
                turn_number = 0  # Reset for researcher intervention
            else:
                # Increment turn after Model B responds
                if i > 0 and messages[i-1]['sender_role'] != 'researcher':
                    if experiment['model_b_name'] == msg['sender_role']:
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
    """Display active (non-deleted) experiments."""
    # Get all experiments
    experiments = database.get_all_experiments()
    
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
        model_a_display = f"{exp['model_a_name']} ({exp.get('model_a_variant', 'default')})"
        model_b_display = f"{exp['model_b_name']} ({exp.get('model_b_variant', 'default')})"
        
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
            messages = database.get_experiment_messages(exp['id'])
            
            for msg in messages:
                role = msg['sender_role']
                content = msg['content']
                timestamp = msg['timestamp'][11:19]  # Extract time only
                is_error = msg.get('is_error', 0)
                error_type = msg.get('error_type')
                
                if is_error:
                    # Display error messages prominently
                    error_emoji = "⚠️" if error_type == "rate_limit" else "❌"
                    st.error(f"{error_emoji} **ERROR** ({timestamp}) [{error_type}]: {content}")
                elif role == 'researcher':
                    st.info(f"**👤 Researcher** ({timestamp}): {content}")
                elif role == exp['model_a_name']:
                    st.success(f"**🤖 {role}** ({timestamp}): {content}")
                else:
                    st.warning(f"**🤖 {role}** ({timestamp}): {content}")

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
        
        # Conversation Mode Selection
        conv_mode = st.radio(
            "Conversation Mode",
            ["Manual", "Automatic"],
            help="Manual: Click 'Continue' after each exchange. Automatic: Runs all turns automatically."
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
            st.success(f"✅ Started experiment #{exp_id}: {experiment_name}")
            st.rerun()

    # --- Main Chat Interface ---
    
    if "messages" not in st.session_state:
        st.info("👈 Set up a new experiment in the sidebar to begin.")
        return

    # Display current experiment info
    st.markdown(
        f"**Experiment:** {st.session_state.get('experiment_name', 'Unnamed')} (#{st.session_state.experiment_id}) | "
        f"**Mode:** {st.session_state.get('conversation_mode', 'Manual')} | "
        f"**Turn:** {st.session_state.turn_count}/{st.session_state.max_turns}"
    )

    # Display the conversation history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Stop button for automatic mode
    if st.session_state.get("conversation_mode") == "Automatic" and st.session_state.get("auto_running", False):
        if st.button("⏹️ Stop Conversation"):
            st.session_state.stop_requested = True
            st.session_state.auto_running = False
            st.warning("⏸️ Conversation stopped by user.")
            st.rerun()

    # Check if the turn limit has been reached
    if st.session_state.get("limit_reached", False):
        st.info("🏁 Turn limit reached.")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("➕ Continue for 5 more turns"):
                st.session_state.max_turns += 5
                st.session_state.limit_reached = False
                st.rerun()
        with col2:
            if st.button("✅ End Experiment"):
                st.success("Experiment completed! View it in the 'History' tab.")
                st.session_state.messages = []
        return

    # Allow starting conversation without researcher message
    # Check if this is the first turn and no researcher message yet
    if st.session_state.turn_count == 0 and len(st.session_state.messages) == 0:
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
            st.session_state.messages.append({"role": "researcher", "content": user_prompt})
            
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
    Used for both manual and automatic modes.
    """
    exp_id = st.session_state.experiment_id
    
    # Delete any previous error messages from the database before continuing
    # This ensures new attempts replace old errors rather than accumulating them
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages WHERE experiment_id = ? AND is_error = 1", (exp_id,))
    conn.commit()
    conn.close()
    
    # Reset status to in_progress if it was previously in error state
    database.update_experiment_status(exp_id, "in_progress")
    
    # Display turn indicator
    current_turn = st.session_state.turn_count + 1
    st.info(f"🔄 **Processing Turn {current_turn}/{st.session_state.max_turns}**")
    
    # Get cached clients (prevents re-initialization)
    client_a = get_llm_client(st.session_state.provider_a, st.session_state.model_a_variant)
    client_b = get_llm_client(st.session_state.provider_b, st.session_state.model_b_variant)

    if not client_a or not client_b:
        st.error("❌ Failed to initialize LLM clients. Check API keys.")
        st.session_state.auto_running = False
        return

    # Model A's response
    with st.chat_message(st.session_state.model_a_display):
        with st.spinner(f"🤔 {st.session_state.model_a_display} is thinking... (Turn {current_turn})"):
            try:
                response_a = client_a.generate_response(st.session_state.model_a_history)
                
                # Log and display
                database.log_message(exp_id, model_config.PROVIDERS[st.session_state.provider_a], response_a)
                
                # Append to messages if it exists (only used in new conversation page)
                if hasattr(st.session_state, 'messages'):
                    st.session_state.messages.append({"role": st.session_state.model_a_display, "content": response_a})
                
                # Update histories
                st.session_state.model_a_history.append({"role": "assistant", "content": response_a})
                st.session_state.model_b_history.append({"role": "user", "content": response_a})
                
                st.markdown(response_a)

            except Exception as e:
                error_msg = f"Error from {st.session_state.model_a_display}: {str(e)}"
                st.error(f"❌ {error_msg}")
                
                # Determine error type
                error_type = "api_error"
                if "rate" in str(e).lower() or "quota" in str(e).lower() or "limit" in str(e).lower():
                    error_type = "rate_limit"
                elif "timeout" in str(e).lower() or "connection" in str(e).lower():
                    error_type = "network_error"
                
                # Log error to database
                database.log_message(exp_id, st.session_state.model_a_display, error_msg, is_error=True, error_type=error_type)
                database.update_experiment_status(exp_id, "error")
                
                # Append to messages if it exists
                if hasattr(st.session_state, 'messages'):
                    st.session_state.messages.append({"role": "error", "content": error_msg, "error_type": error_type})
                
                st.session_state.auto_running = False
                return

    # Small delay for automatic mode visibility
    if st.session_state.get("conversation_mode") == "Automatic":
        time.sleep(1)

    # Model B's response
    with st.chat_message(st.session_state.model_b_display):
        with st.spinner(f"🤔 {st.session_state.model_b_display} is thinking... (Turn {current_turn})"):
            try:
                response_b = client_b.generate_response(st.session_state.model_b_history)
                
                # Log and display
                database.log_message(exp_id, model_config.PROVIDERS[st.session_state.provider_b], response_b)
                
                # Append to messages if it exists (only used in new conversation page)
                if hasattr(st.session_state, 'messages'):
                    st.session_state.messages.append({"role": st.session_state.model_b_display, "content": response_b})
                
                # Update histories
                st.session_state.model_b_history.append({"role": "assistant", "content": response_b})
                st.session_state.model_a_history.append({"role": "user", "content": response_b})
                
                st.markdown(response_b)

                # Increment turn count
                st.session_state.turn_count += 1
                
                # Check if limit reached
                if st.session_state.turn_count >= st.session_state.max_turns:
                    st.session_state.limit_reached = True
                    st.session_state.auto_running = False
                    database.update_experiment_status(exp_id, "completed")
                    st.rerun()
                
                # Continue automatic mode
                if st.session_state.get("conversation_mode") == "Automatic" and not st.session_state.get("stop_requested", False):
                    time.sleep(1)
                    st.rerun()

            except Exception as e:
                error_msg = f"Error from {st.session_state.model_b_display}: {str(e)}"
                st.error(f"❌ {error_msg}")
                
                # Determine error type
                error_type = "api_error"
                if "rate" in str(e).lower() or "quota" in str(e).lower() or "limit" in str(e).lower():
                    error_type = "rate_limit"
                elif "timeout" in str(e).lower() or "connection" in str(e).lower():
                    error_type = "network_error"
                
                # Log error to database
                database.log_message(exp_id, st.session_state.model_b_display, error_msg, is_error=True, error_type=error_type)
                database.update_experiment_status(exp_id, "error")
                
                # Append to messages if it exists
                if hasattr(st.session_state, 'messages'):
                    st.session_state.messages.append({"role": "error", "content": error_msg, "error_type": error_type})
                
                st.session_state.auto_running = False
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
    
    # Navigation back
    if st.button("← Back to History"):
        st.session_state['page'] = 'history'
        del st.session_state['continue_exp_id']
        st.rerun()
    
    st.markdown("---")
    
    # Display existing conversation
    st.subheader("📜 Previous Conversation")
    messages = database.get_experiment_messages(exp_id)
    
    for msg in messages:
        role = msg['sender_role']
        content = msg['content']
        is_error = msg.get('is_error', 0)
        error_type = msg.get('error_type')
        
        with st.chat_message("assistant" if role != "researcher" else "user"):
            if is_error:
                st.error(f"❌ [{error_type}] {content}")
            else:
                st.markdown(f"**{role}**: {content}")
    
    # Load conversation state if not already loaded
    if 'continued_experiment_id' not in st.session_state or st.session_state['continued_experiment_id'] != exp_id:
        st.session_state['continued_experiment_id'] = exp_id
        st.session_state['experiment_id'] = exp_id
        
        # Restore providers and models
        st.session_state.provider_a = list(model_config.PROVIDERS.keys())[list(model_config.PROVIDERS.values()).index(exp['model_a_name'])]
        st.session_state.provider_b = list(model_config.PROVIDERS.keys())[list(model_config.PROVIDERS.values()).index(exp['model_b_name'])]
        st.session_state.model_a_variant = exp.get('model_a_variant') or 'gemini-2.5-pro'
        st.session_state.model_b_variant = exp.get('model_b_variant') or 'gpt-4o-mini'
        st.session_state.model_a_display = model_config.get_model_display_name(st.session_state.provider_a, st.session_state.model_a_variant)
        st.session_state.model_b_display = model_config.get_model_display_name(st.session_state.provider_b, st.session_state.model_b_variant)
        
        # Restore max turns and current turn count
        st.session_state.max_turns = exp['max_turns']
        
        # Count non-error messages to get turn count
        non_error_messages = [m for m in messages if not m.get('is_error', 0)]
        researcher_messages = [m for m in non_error_messages if m['sender_role'] == 'researcher']
        st.session_state.turn_count = (len(non_error_messages) - len(researcher_messages)) // 2
        
        # Rebuild conversation histories
        st.session_state.model_a_history = [{"role": "system", "content": exp['model_a_prompt']}]
        st.session_state.model_b_history = [{"role": "system", "content": exp['model_b_prompt']}]
        
        for msg in non_error_messages:
            if msg['sender_role'] == exp['model_a_name']:
                st.session_state.model_a_history.append({"role": "assistant", "content": msg['content']})
                st.session_state.model_b_history.append({"role": "user", "content": msg['content']})
            elif msg['sender_role'] == exp['model_b_name']:
                st.session_state.model_b_history.append({"role": "assistant", "content": msg['content']})
                st.session_state.model_a_history.append({"role": "user", "content": msg['content']})
            elif msg['sender_role'] == 'researcher':
                # Initial message from researcher
                st.session_state.model_a_history.append({"role": "user", "content": msg['content']})
        
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
