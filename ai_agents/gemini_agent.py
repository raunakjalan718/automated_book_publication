import google.generativeai as genai
from typing import Dict, Any, Optional
from .base_agent import BaseAgent
from config import GEMINI_API_KEY

class GeminiAgent(BaseAgent):
    """Agent implementation using Google's Gemini models."""
    
    def __init__(self, model_name: str = "gemini-pro"):
        """
        Initialize the Gemini agent.
        
        Args:
            model_name: Gemini model to use (default: gemini-pro)
        """
        super().__init__(model_name, GEMINI_API_KEY)
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(model_name=self.model_name)
    
    async def process(self, content: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process content using the Gemini model.
        
        Args:
            content: Input content to process
            context: Additional context for processing
            
        Returns:
            Dictionary containing processed content and metadata
        """
        if context is None:
            context = {}
        
        system_prompt = self.get_system_prompt()
        
        # Construct prompt with context variables
        prompt = f"{system_prompt}\n\n"
        
        if "chapter_title" in context:
            prompt += f"Chapter Title: {context['chapter_title']}\n\n"
            
        if "chapter_number" in context:
            prompt += f"Chapter Number: {context['chapter_number']}\n\n"
            
        if "previous_versions" in context and context["previous_versions"]:
            prompt += "Previous Version:\n"
            prompt += context["previous_versions"][0] + "\n\n"
            
        if "feedback" in context and context["feedback"]:
            prompt += f"Feedback to Address:\n{context['feedback']}\n\n"
        
        prompt += f"Original Content:\n{content}"
        
        # Generate content with Gemini
        response = self.model.generate_content(prompt)
        
        return {
            "processed_content": response.text,
            "model": self.model_name,
            "prompt": prompt
        }
    
    def get_system_prompt(self) -> str:
        """
        To be implemented by subclasses.
        """
        return ""
