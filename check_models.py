import os
import google.generativeai as genai
from dotenv import load_dotenv

def check_google_models():
    """
    Connects to the Google API and lists all available models
    that support the 'generateContent' method.
    """
    # Load environment variables from .env file
    load_dotenv()

    # Get the API key from the environment
    api_key = os.getenv("GOOGLE_API_KEY")

    if not api_key:
        print("Error: GOOGLE_API_KEY not found in .env file.")
        print("Please add your Google API key to the .env file to check available models.")
        return

    try:
        # Configure the library with the API key
        genai.configure(api_key=api_key)

        print("\n--- Querying Google API for available models... ---")
        
        found_models = False
        # List all available models
        for m in genai.list_models():
            # Check if the model supports the 'generateContent' method
            if 'generateContent' in m.supported_generation_methods:
                print(f"- {m.name}")
                found_models = True
        
        if not found_models:
            print("No models supporting 'generateContent' were found for your API key.")
        
        print("\n---")
        print("Recommendation: Copy one of the model names listed above (e.g., 'models/gemini-pro')")
        print("and paste it into 'llm_clients/gemini.py' as the 'self.model_name'.")

    except Exception as e:
        print(f"\nAn error occurred while trying to list the models: {e}")
        print("\nPlease check the following:")
        print("1. Is your GOOGLE_API_KEY in the .env file correct and valid?")
        print("2. Do you have an active internet connection?")
        print("3. Is billing enabled for your Google Cloud project if you are outside the free tier?")

if __name__ == "__main__":
    check_google_models()
