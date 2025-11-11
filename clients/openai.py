from openai import OpenAI
from .base import BaseLLMClient
from typing import List, Dict

class OpenAIClient(BaseLLMClient):
    """
    Client for OpenAI's API (GPT models).
    This is the simplest client since we're using OpenAI's message format
    as our standard across all clients.
    """
    
    def __init__(self, api_key: str, model_id: str = "gpt-4o-mini"):
        """
        Initialize OpenAI client.
        
        Args:
            api_key: OpenAI API key
            model_id: Model ID (e.g., "gpt-4o", "gpt-3.5-turbo")
        """
        self.client = OpenAI(api_key=api_key)
        self.model_name = model_id

    def generate_response(self, messages: List[Dict[str, str]]) -> str:
        """
        Generate a response from OpenAI's API.
        The message format is already correct, so we just pass it through.
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages
            )
            
            content = response.choices[0].message.content
            return content if content else "No response from model."
            
        except Exception as e:
            # Log the error but return a user-friendly message
            print(f"Error calling OpenAI: {e}")
            return f"An error occurred: {e}"
