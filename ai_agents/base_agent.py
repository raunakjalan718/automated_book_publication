from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class BaseAgent(ABC):
    """Base class for AI agents."""
    
    def __init__(self, model_name: str, api_key: str):
        """
        Initialize the base agent.
        
        Args:
            model_name: Name of the model to use
            api_key: API key for the service
        """
        self.model_name = model_name
        self.api_key = api_key
    
    @abstractmethod
    async def process(self, content: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process content with the AI agent.
        
        Args:
            content: The input content to process
            context: Additional context for processing
            
        Returns:
            Processed output and any additional metadata
        """
        pass
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """
        Get the system prompt for the agent.
        
        Returns:
            The system prompt string
        """
        pass
