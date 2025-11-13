import google.generativeai as genai
from .base import BaseLLMClient
from typing import List, Dict
import json

class GoogleGeminiClient(BaseLLMClient):
    """
    Client for Google's Gemini API.
    Handles the conversion between OpenAI's message format (which we use as our
    standard) and Gemini's specific format requirements.
    """
    
    def __init__(self, api_key: str, model_id: str = "models/gemini-pro-latest"):
        """
        Initialize Gemini client.
        
        Args:
            api_key: Google API key
            model_id: Full model ID (e.g., "models/gemini-2.5-pro")
        """
        genai.configure(api_key=api_key)
        self.model_name = model_id
        self.model = genai.GenerativeModel(self.model_name)
    
    def generate_response(self, messages: List[Dict[str, str]]) -> str:
        """
        Generates a response from Gemini.
        
        Gemini has some quirks:
        - It uses 'model' role instead of 'assistant'
        - System instructions are set separately, not in the message list
        - History format is different from OpenAI's
        """
        try:
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
                    self.model_name,
                    system_instruction=system_prompt
                )
            
            # Create chat session with all but the last message as history
            if len(gemini_history) > 1:
                chat = self.model.start_chat(history=gemini_history[:-1])
                last_message_content = messages[-1]['content']
                response = chat.send_message(
                    last_message_content,
                    request_options={"timeout": 30}
                )
            else:
                # First message - no history yet
                last_message_content = messages[-1]['content']
                response = self.model.generate_content(
                    last_message_content,
                    request_options={"timeout": 30}
                )
            
            # Validate response
            if not response:
                print("⚠️ Gemini API: Received None response")
                raise ValueError("Gemini API: Received None response")
            
            if not hasattr(response, 'text') or not response.text:
                print("⚠️ Gemini API: Response has no text attribute or empty text")
                raise ValueError("Gemini API: Response has no text attribute or empty text")
            
            return response.text
        
        except AttributeError as e:
            print(f"❌ Gemini API: AttributeError - {str(e)}")
            raise e
        
        except ValueError as e:
            print(f"❌ Gemini API: ValueError (likely content policy) - {str(e)}")
            raise e
        
        except Exception as e:
            error_type = type(e).__name__
            print(f"❌ Gemini API: Unexpected error ({error_type}) - {str(e)}")
            raise e
