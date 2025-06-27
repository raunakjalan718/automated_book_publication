from typing import Dict, Any, Optional
from .openai_agent import OpenAIAgent

class EditorAgent(OpenAIAgent):
    """AI agent responsible for final editing and polishing of content."""
    
    def __init__(self):
        """Initialize the Editor agent."""
        super().__init__(model_name="gpt-4")  # More powerful model for editing
    
    def get_system_prompt(self) -> str:
        """
        Get the system prompt for the editor agent.
        
        Returns:
            The system prompt string
        """
        return """You are an experienced book editor finalizing a manuscript. Your task is to polish 
        a chapter that has been rewritten and reviewed, making it publication-ready.

Focus on:
1. Grammar, spelling, and punctuation accuracy
2. Improving sentence flow and paragraph transitions
3. Maintaining consistent tone and voice
4. Enhancing clarity and readability
5. Removing redundancies and awkward phrasing

Keep the content, plot points, and character development intact while making the prose
elegant and professional. Address any issues mentioned in provided feedback.

Your output should be only the final edited chapter text, ready for publication."""
