import openai
from typing import Dict, Any, Optional
from .base_agent import BaseAgent
from config import OPENAI_API_KEY

class OpenAIAgent(BaseAgent):
    """Agent implementation using OpenAI models."""
    
    def __init__(self, model_name: str = "gpt-3.5-turbo"):
        """
        Initialize the OpenAI agent.
        
        Args:
            model_name: OpenAI model to use
        """
        super().__init__(model_name, OPENAI_API_KEY)
        openai.api_key = self.api_key
    
    async def process(self, content: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process content using the OpenAI model.
        
        Args:
            content: Input content to process
            context: Additional context for processing
            
        Returns:
            Dictionary containing processed content and metadata
        """
        if context is None:
            context = {}
        
        system_prompt = self.get_system_prompt()
        
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        user_message = ""
        
        if "chapter_title" in context:
            user_message += f"Chapter Title: {context['chapter_title']}\n\n"
            
        if "chapter_number" in context:
            user_message += f"Chapter Number: {context['chapter_number']}\n\n"
            
        if "previous_versions" in context and context["previous_versions"]:
            user_message += "Previous Version:\n"
            user_message += context["previous_versions"][0] + "\n\n"
            
        if "feedback" in context and context["feedback"]:
            user_message += f"Feedback to Address:\n{context['feedback']}\n\n"
        
        user_message += f"Original Content:\n{content}"
        
        messages.append({"role": "user", "content": user_message})
        
        # Generate content with OpenAI
        response = openai.ChatCompletion.create(
            model=self.model_name,
            messages=messages,
            temperature=0.7,
            max_tokens=4000,
        )
        
        return {
            "processed_content": response.choices[0].message.content,
            "model": self.model_name,
            "prompt": user_message,
            "usage": response.usage
        }
    
    def get_system_prompt(self) -> str:
        """
        To be implemented by subclasses.
        """
        return ""
