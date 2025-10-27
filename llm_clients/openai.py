from openai import OpenAI
from .base import BaseLLMClient
from typing import List, Dict

class OpenAIClient(BaseLLMClient):
    """
    Client for OpenAI's API (GPT models).
    This is the simplest client since we're using OpenAI's message format
    as our standard across all clients.
    """
    
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
        # Using mini model for cost-effectiveness during prototyping
        self.model_name = "gpt-4o-mini"

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
