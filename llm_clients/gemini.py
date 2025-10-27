import google.generativeai as genai
from .base import BaseLLMClient
from typing import List, Dict

class GoogleGeminiClient(BaseLLMClient):
    """
    Client for Google's Gemini API.
    Handles the conversion between OpenAI's message format (which we use as our
    standard) and Gemini's specific format requirements.
    """
    
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        # Using flash model for speed during prototyping
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    def generate_response(self, messages: List[Dict[str, str]]) -> str:
        """
        Generate a response from Gemini.
        
        Gemini has some quirks:
        - It uses 'model' role instead of 'assistant'
        - System instructions are set separately, not in the message list
        - History format is different from OpenAI's
        """
        gemini_history = []
        system_prompt = None
        
        # Extract system prompt and convert message format
        for msg in messages:
            if msg['role'] == 'system':
                system_prompt = msg['content']
                continue
            
            # Gemini uses 'model' where OpenAI uses 'assistant'
            role = 'model' if msg['role'] == 'assistant' else 'user'
            gemini_history.append({'role': role, 'parts': [msg['content']]})
        
        # If there's a system prompt, recreate the model with it
        if system_prompt:
            self.model = genai.GenerativeModel(
                'gemini-1.5-flash',
                system_instruction=system_prompt
            )
        
        # Create chat session with all but the last message as history
        # The last message will be sent separately to get the response
        if len(gemini_history) > 1:
            chat = self.model.start_chat(history=gemini_history[:-1])
            last_message_content = messages[-1]['content']
            response = chat.send_message(last_message_content)
        else:
            # First message - no history yet
            last_message_content = messages[-1]['content']
            response = self.model.generate_content(last_message_content)
        
        return response.text
