from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import asyncio

class ContentProcessor(ABC):
    """Base content processing system with customizable behavior."""
    
    def __init__(self, model_identifier: str, processing_type: str):
        """
        Initialize the content processor.
        
        Args:
            model_identifier: Identifier for the model to use
            processing_type: Type of processing (transform, analyze, enhance)
        """
        self.model_id = model_identifier
        self.processor_type = processing_type
        self.history = []
        
    @abstractmethod
    async def transform_content(self, 
                              input_text: str, 
                              transformation_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process content according to the processor's function."""
        pass
    
    def create_processing_guidelines(self, transformation_params: Dict[str, Any]) -> str:
        """Create guidelines for content processing based on parameters."""
        guidelines = [f"Content Processing Type: {self.processor_type}"]
        
        # Add custom guidelines based on parameters
        for key, value in transformation_params.items():
            if key == "style_reference":
                guidelines.append(f"Reference Style: {value}")
            elif key == "intensity":
                guidelines.append(f"Transformation Intensity: {value}/10")
            elif key == "preserve_elements":
                elements = ", ".join(value)
                guidelines.append(f"Preserve Elements: {elements}")
                
        return "\n".join(guidelines)
    
    def track_transformation(self, 
                           input_text: str, 
                           output_text: str, 
                           metadata: Dict[str, Any]) -> None:
        """Track transformation for learning and improvement."""
        self.history.append({
            "timestamp": metadata.get("timestamp"),
            "input_length": len(input_text),
            "output_length": len(output_text),
            "processing_type": self.processor_type,
            "model_id": self.model_id,
            "parameters": metadata.get("parameters", {})
        })
