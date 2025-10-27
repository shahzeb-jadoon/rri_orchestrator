from abc import ABC, abstractmethod
from typing import List, Dict

class BaseLLMClient(ABC):
    """
    Abstract base class defining the interface all LLM clients must implement.
    This ensures any model provider (OpenAI, Google, Anthropic, etc.) can be
    used interchangeably in the conversation orchestrator.
    
    The design follows the Strategy pattern - each concrete client is a different
    strategy for generating responses, but they all share the same interface.
    """
    
    @abstractmethod
    def generate_response(self, messages: List[Dict[str, str]]) -> str:
        """
        Generate a response from the LLM based on conversation history.
        
        Args:
            messages: List of message dicts in OpenAI chat format:
                     [{'role': 'system', 'content': 'You are a helpful assistant'},
                      {'role': 'user', 'content': 'Hello!'},
                      {'role': 'assistant', 'content': 'Hi there!'}]
                     
        Returns:
            The model's response as a string
        """
        pass
