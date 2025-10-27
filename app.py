import streamlit as st
import os
from dotenv import load_dotenv

# Import our custom modules
import database
from llm_clients.base import BaseLLMClient
from llm_clients.gemini import GoogleGeminiClient
from llm_clients.openai import OpenAIClient

# Load environment variables from .env file
load_dotenv()

# --- Authentication ---

def check_password():
    """
    Simple password protection to prevent unauthorized access.
    Uses session state to remember authentication across reruns.
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

    # Show login form
    password = st.text_input("Lab Password", type="password")
    if st.button("Login"):
        if password == correct_password:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Incorrect password")
    return False

# --- LLM Client Factory ---

def get_llm_client(client_name: str) -> BaseLLMClient | None:
    """
    Factory function to instantiate the appropriate LLM client.
    This pattern makes it easy to add new models - just add a new elif block.
    
    Args:
        client_name: Display name of the model ("Google Gemini", etc.)
        
    Returns:
        An instance of the appropriate client, or None if API key is missing
    """
    if client_name == "Google Gemini":
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            st.error("GOOGLE_API_KEY not found in .env file.")
            return None
        return GoogleGeminiClient(api_key=api_key)
    
    elif client_name == "OpenAI (GPT-4)":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            st.error("OPENAI_API_KEY not found in .env file.")
            return None
        return OpenAIClient(api_key=api_key)
    
    # Add more clients here (Azure, Claude, etc.)
    
    return None

# --- Main Application ---

def main_app():
    """
    The main RRI conversation orchestrator interface.
    Sidebar handles experiment setup, main area displays the conversation.
    """
    st.set_page_config(layout="wide")
    st.title("🤖 RRI Conversation Orchestrator")

    # --- Sidebar: Experiment Configuration ---
    with st.sidebar:
        st.header("🔬 Experiment Setup")
        
        # Model selection dropdowns
        available_models = ["Google Gemini", "OpenAI (GPT-4)"]
        model_a_name = st.selectbox("Select Model A (Starts)", available_models, index=0)
        model_b_name = st.selectbox("Select Model B (Responds)", available_models, index=1)
        
        # System prompts define each model's role and behavior
        st.subheader("System Prompts")
        prompt_a = st.text_area(
            "System Prompt for Model A", 
            f"You are {model_a_name}. You are talking to {model_b_name}. Start the conversation.", 
            height=100
        )
        prompt_b = st.text_area(
            "System Prompt for Model B", 
            f"You are {model_b_name}. You are talking to {model_a_name}. Wait for them to speak first, then respond.", 
            height=100
        )

        if st.button("Start New Experiment"):
            # Initialize a fresh experiment in the database
            exp_id = database.create_experiment(model_a_name, model_b_name, prompt_a, prompt_b)
            
            # Reset session state for new conversation
            st.session_state.messages = []
            st.session_state.experiment_id = exp_id
            st.session_state.model_a_name = model_a_name
            st.session_state.model_b_name = model_b_name
            # Each model maintains its own conversation history for context
            st.session_state.model_a_history = [{"role": "system", "content": prompt_a}]
            st.session_state.model_b_history = [{"role": "system", "content": prompt_b}]
            st.success(f"Started new experiment: {exp_id}")
            st.rerun()

    # --- Main Chat Interface ---
    
    if "messages" not in st.session_state:
        st.info("Set up a new experiment in the sidebar to begin.")
        return

    # Display the conversation history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Handle new user input
    if user_prompt := st.chat_input("Researcher: Start the conversation or intervene..."):
        
        exp_id = st.session_state.experiment_id
        
        # Step 1: Log and display researcher's message
        database.log_message(exp_id, "researcher", user_prompt)
        st.session_state.messages.append({"role": "researcher", "content": user_prompt})
        
        # Add to both models' histories so they know what the researcher said
        st.session_state.model_a_history.append({"role": "user", "content": user_prompt})
        st.session_state.model_b_history.append({"role": "user", "content": user_prompt})
        
        with st.chat_message("researcher"):
            st.markdown(user_prompt)

        # Initialize clients for both models
        client_a = get_llm_client(st.session_state.model_a_name)
        client_b = get_llm_client(st.session_state.model_b_name)

        if not client_a or not client_b:
            st.error("Failed to initialize LLM clients. Check API keys.")
            return

        # Step 2: Get Model A's response
        with st.chat_message(st.session_state.model_a_name):
            with st.spinner(f"{st.session_state.model_a_name} is thinking..."):
                try:
                    response_a = client_a.generate_response(st.session_state.model_a_history)
                    
                    # Log and display
                    database.log_message(exp_id, st.session_state.model_a_name, response_a)
                    st.session_state.messages.append({"role": st.session_state.model_a_name, "content": response_a})
                    
                    # Update both histories
                    # Model A sees its own response as 'assistant'
                    st.session_state.model_a_history.append({"role": "assistant", "content": response_a})
                    # Model B sees Model A's response as incoming 'user' message
                    st.session_state.model_b_history.append({"role": "user", "content": response_a})
                    
                    st.markdown(response_a)

                except Exception as e:
                    st.error(f"Error from {st.session_state.model_a_name}: {e}")

        # Step 3: Get Model B's response
        with st.chat_message(st.session_state.model_b_name):
            with st.spinner(f"{st.session_state.model_b_name} is thinking..."):
                try:
                    response_b = client_b.generate_response(st.session_state.model_b_history)
                    
                    # Log and display
                    database.log_message(exp_id, st.session_state.model_b_name, response_b)
                    st.session_state.messages.append({"role": st.session_state.model_b_name, "content": response_b})
                    
                    # Update both histories
                    st.session_state.model_b_history.append({"role": "assistant", "content": response_b})
                    st.session_state.model_a_history.append({"role": "user", "content": response_b})
                    
                    st.markdown(response_b)

                except Exception as e:
                    st.error(f"Error from {st.session_state.model_b_name}: {e}")


# --- Entry Point ---

if __name__ == "__main__":
    # Ensure database tables exist before running the app
    database.setup_database()
    
    if check_password():
        main_app()
