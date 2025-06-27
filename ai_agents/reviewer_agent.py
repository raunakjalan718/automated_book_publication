from typing import Dict, Any, Optional
from .gemini_agent import GeminiAgent
from .openai_agent import OpenAIAgent

class ReviewerAgent(OpenAIAgent):
    """AI agent responsible for reviewing and providing feedback on content."""
    
    def __init__(self, use_openai: bool = True):
        """
        Initialize the Reviewer agent.
        
        Args:
            use_openai: Whether to use OpenAI (True) or Gemini (False)
        """
        if use_openai:
            super().__init__(model_name="gpt-3.5-turbo")
        else:
            # Switch to Gemini implementation if requested
            self.__class__ = type('GeminiReviewerAgent', (GeminiAgent,), {})
            GeminiAgent.__init__(self)
    
    def get_system_prompt(self) -> str:
        """
        Get the system prompt for the reviewer agent.
        
        Returns:
            The system prompt string
        """
        return """You are a literary reviewer examining a rewritten chapter. Provide constructive feedback on:

1. Content integrity: Are all key plot elements preserved from the original?
2. Distinctiveness: Is the rewritten version sufficiently different stylistically?
3. Quality: Is the writing clear, engaging and error-free?
4. Consistency: Does it maintain a coherent voice throughout?
5. Readability: Is it well-organized and easy to follow?

Include specific examples from the text. Format your review in two sections:
1. General Assessment: Overall evaluation
2. Specific Recommendations: 3-5 concrete improvement suggestions

Be thorough but concise - help improve the text without completely rewriting it."""
