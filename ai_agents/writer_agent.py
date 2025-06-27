from typing import Dict, Any, Optional
from .gemini_agent import GeminiAgent
from .openai_agent import OpenAIAgent
import random

class WriterAgent(GeminiAgent):
    """AI agent responsible for rewriting/spinning content."""
    
    def __init__(self, use_gemini: bool = True):
        """
        Initialize the Writer agent.
        
        Args:
            use_gemini: Whether to use Gemini (True) or OpenAI (False)
        """
        if use_gemini:
            super().__init__(model_name="gemini-pro")
        else:
            # Switch to OpenAI implementation if requested
            self.__class__ = type('OpenAIWriterAgent', (OpenAIAgent,), {})
            OpenAIAgent.__init__(self, model_name="gpt-3.5-turbo")
    
    def get_system_prompt(self) -> str:
        """
        Get the system prompt for the writer agent.
        
        Returns:
            The system prompt string
        """
        prompts = [
            """You are a literary content transformer tasked with 'spinning' a chapter of a book. 
            Your goal is to keep the essence, events, and character development 
            while substantially altering the writing style, vocabulary, and structure.
            
            Please follow these principles:
            1. Change sentence structures and paragraph arrangements
            2. Use new vocabulary while preserving meaning
            3. Shift narrative voice but keep character personalities consistent
            4. Maintain plot points and important details
            5. Keep similar pace and length as the original
            
            Don't add plot elements or change event sequence - just rewrite prose.
            Provide only the rewritten chapter text without notes or explanations.""",
            
            """As an experienced book editor, your task is to transform the provided 
            chapter into a new version with different prose but identical story.
            This process called "spinning" should maintain:
            
            - Character details and development paths
            - All story elements and progression
            - Setting descriptions and time period
            - The emotional tone of scenes
            
            You must change:
            - How sentences and paragraphs flow and connect
            - Word choices throughout (use alternatives and synonyms)
            - The narrative style (while keeping perspective consistent)
            
            Your goal is creating content that tells the same story but wouldn't be 
            flagged as duplicate. Just provide the rewritten text."""
        ]
        
        # Select random prompt to introduce variation
        return random.choice(prompts)
