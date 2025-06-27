import os
import json
import requests
from typing import Dict, List, Optional, Union

class AIWriter:
    """A class to generate and refine content using AI language models."""
    
    def __init__(self, api_key: str = None, model: str = "gpt-3.5-turbo"):
        """
        Step 1: Initialize the AI Writer with API credentials and configuration
        
        Args:
            api_key: The API key for the language model service
            model: The specific model to use for generation
        """
        # Use provided API key or get from environment variables
        self.api_key = api_key or os.environ.get("AI_API_KEY")
        if not self.api_key:
            raise ValueError("API key must be provided or set as AI_API_KEY environment variable")
        
        self.model = model
        self.base_url = "https://api.openai.com/v1/chat/completions"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
    def prepare_prompt(self, 
                      content_type: str,
                      topic: str, 
                      tone: str = "informative",
                      length: str = "medium",
                      additional_instructions: str = "",
                      examples: List[str] = None) -> List[Dict[str, str]]:
        """
        Step 2: Process and prepare the prompt for the AI model
        
        Args:
            content_type: Type of content to generate (blog, email, social post, etc.)
            topic: The main topic or subject to write about
            tone: The desired tone of the content
            length: Desired content length (short, medium, long)
            additional_instructions: Any specific requirements or constraints
            examples: Optional list of example outputs to guide the model
            
        Returns:
            Formatted messages for the API request
        """
        # Convert length to approximate word count
        length_guide = {
            "short": "150-300 words",
            "medium": "500-750 words",
            "long": "1000-1500 words"
        }
        word_count = length_guide.get(length.lower(), "500-750 words")
        
        # Build the system message with clear instructions
        system_msg = (
            f"You are an expert content creator specializing in {content_type} writing. "
            f"Write in a {tone} tone and aim for {word_count}. "
            "Structure the content clearly with appropriate headings and paragraphs."
        )
        
        # Build the main instruction message
        user_msg = f"Write a {content_type} about {topic}. {additional_instructions}"
        
        messages = [{"role": "system", "content": system_msg}]
        
        # Add examples if provided (one-shot or few-shot learning)
        if examples:
            for example in examples:
                messages.append({"role": "assistant", "content": example})
        
        messages.append({"role": "user", "content": user_msg})
        return messages
        
    def generate_content(self, 
                       messages: List[Dict[str, str]], 
                       temperature: float = 0.7,
                       max_tokens: int = 1500,
                       refine_output: bool = True) -> Dict[str, Union[str, Dict]]:
        """
        Step 3: Generate content using the AI model and optionally refine it
        
        Args:
            messages: Prepared prompt messages for the API
            temperature: Creativity parameter (0.0-1.0)
            max_tokens: Maximum length of generated content
            refine_output: Whether to refine the output with a second pass
            
        Returns:
            Dictionary containing the generated content and metadata
        """
        # Prepare the request payload
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        # Make the API request
        response = requests.post(
            self.base_url,
            headers=self.headers,
            data=json.dumps(payload)
        )
        
        # Check for errors
        if response.status_code != 200:
            error_info = response.json()
            return {
                "success": False,
                "error": f"API request failed: {error_info.get('error', {}).get('message', 'Unknown error')}"
            }
        
        # Extract the generated content
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        
        # Optional refinement step
        if refine_output:
            refine_messages = [
                {"role": "system", "content": "You are an expert editor. Improve the following content by fixing any grammar issues, enhancing clarity, and ensuring a cohesive flow."},
                {"role": "user", "content": f"Please refine this content:\n\n{content}"}
            ]
            
            refine_payload = {
                "model": self.model,
                "messages": refine_messages,
                "temperature": 0.3,  # Lower temperature for editing
                "max_tokens": max_tokens
            }
            
            refine_response = requests.post(
                self.base_url,
                headers=self.headers,
                data=json.dumps(refine_payload)
            )
            
            if refine_response.status_code == 200:
                refine_result = refine_response.json()
                content = refine_result["choices"][0]["message"]["content"]
        
        return {
            "success": True,
            "content": content,
            "metadata": {
                "model": self.model,
                "temperature": temperature,
                "token_count": result["usage"]["total_tokens"]
            }
        }
    
    def create_content(self,
                     content_type: str,
                     topic: str,
                     tone: str = "informative",
                     length: str = "medium",
                     additional_instructions: str = "",
                     temperature: float = 0.7,
                     examples: List[str] = None,
                     refine_output: bool = True) -> Dict[str, Union[str, Dict]]:
        """
        Convenience method to create content in one step
        
        Combines all three steps: initialization (already done), prompt preparation, and content generation
        """
        messages = self.prepare_prompt(
            content_type=content_type,
            topic=topic,
            tone=tone,
            length=length,
            additional_instructions=additional_instructions,
            examples=examples
        )
        
        return self.generate_content(
            messages=messages,
            temperature=temperature,
            refine_output=refine_output
        )
