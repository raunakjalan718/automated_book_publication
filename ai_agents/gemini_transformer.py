import google.generativeai as genai
from typing import Dict, Any, Optional, List
import time
from datetime import datetime
import re
import asyncio

from .language_processor import ContentProcessor

class GeminiTransformer(ContentProcessor):
    """Content transformation using Google's Gemini API."""
    
    def __init__(self, transformation_style: str = "creative"):
        """
        Initialize Gemini transformer.
        
        Args:
            transformation_style: Style of transformation (creative, academic, technical)
        """
        super().__init__("gemini-pro", transformation_style)
        
        # Initialize Gemini with API key from environment
        from dotenv import load_dotenv
        import os
        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY")
        genai.configure(api_key=api_key)
        
        # Set up the model
        generation_config = {
            "temperature": 0.7 if transformation_style == "creative" else 0.4,
            "top_p": 0.95,
            "top_k": 40,
        }
        
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        ]
        
        self.model = genai.GenerativeModel(
            model_name="gemini-pro",
            generation_config=generation_config,
            safety_settings=safety_settings
        )
        self.style = transformation_style
        
    def build_transformation_prompt(self, 
                                  input_text: str, 
                                  params: Dict[str, Any]) -> str:
        """Build a specialized prompt for content transformation."""
        chapter_title = params.get("chapter_title", "")
        chapter_number = params.get("chapter_number", "")
        
        # Create a dynamic prompt based on transformation style
        if self.style == "creative":
            prompt_template = f"""
            As an expert literary transformer, rewrite this text with a fresh creative voice while preserving the core narrative elements.
            
            CHAPTER INFORMATION:
            {'Title: ' + chapter_title if chapter_title else ''}
            {'Chapter: ' + str(chapter_number) if chapter_number else ''}
            
            TRANSFORMATION GUIDELINES:
            1. Change sentence structures, vocabulary, and paragraph flow
            2. Keep all plot points, characters, and settings intact
            3. Maintain the emotional tone and theme of the original
            4. Ensure the rewritten text has similar length to the original
            5. Use creative language that differs from the original but conveys the same meaning
            
            ORIGINAL TEXT:
            {input_text}
            
            REWRITTEN TEXT:
            """
        else:
            # For other styles (academic, technical)
            prompt_template = f"""
            Transform the following text while maintaining its core information and narrative structure.
            
            CHAPTER INFORMATION:
            {'Title: ' + chapter_title if chapter_title else ''}
            {'Chapter: ' + str(chapter_number) if chapter_number else ''}
            
            TRANSFORMATION GUIDELINES:
            1. Adapt to a {self.style} writing style
            2. Preserve all key information and concepts
            3. Maintain logical flow and coherence
            4. Keep similar length and detail level
            
            ORIGINAL TEXT:
            {input_text}
            
            TRANSFORMED TEXT:
            """
            
        return prompt_template
        
    async def transform_content(self, 
                              input_text: str, 
                              transformation_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Transform content using the Gemini model.
        
        Args:
            input_text: Text to transform
            transformation_params: Parameters controlling transformation
            
        Returns:
            Dictionary with transformed content and metadata
        """
        if transformation_params is None:
            transformation_params = {}
            
        start_time = time.time()
        
        # Build the specialized prompt
        prompt = self.build_transformation_prompt(input_text, transformation_params)
        
        # Process with Gemini API
        try:
            response = self.model.generate_content(prompt)
            transformed_text = response.text
            
            # Clean up the response - remove any prefixes or code blocks
            transformed_text = re.sub(r'^(REWRITTEN TEXT:|TRANSFORMED TEXT:)', '', transformed_text, flags=re.IGNORECASE)
            transformed_text = transformed_text.strip()
            
            # Track transformation for learning
            self.track_transformation(
                input_text, 
                transformed_text, 
                {
                    "timestamp": datetime.now().isoformat(),
                    "parameters": transformation_params,
                    "processing_time": time.time() - start_time
                }
            )
            
            return {
                "transformed_content": transformed_text,
                "original_length": len(input_text),
                "transformed_length": len(transformed_text),
                "processing_time": time.time() - start_time,
                "model": self.model_id,
                "transformation_style": self.style
            }
            
        except Exception as e:
            return {
                "error": f"Transformation failed: {str(e)}",
                "model": self.model_id,
                "processing_time": time.time() - start_time
            }
