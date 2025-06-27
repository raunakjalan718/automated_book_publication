import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from sentence_transformers import SentenceTransformer, util
import numpy as np
from typing import Dict, Any, Optional, List
import time
from datetime import datetime
import asyncio
import os
import re

from .language_processor import ContentProcessor

class HuggingFaceEvaluator(ContentProcessor):
    """Content evaluation using open-source Hugging Face models."""
    
    def __init__(self, evaluation_focus: str = "quality"):
        """
        Initialize the HuggingFace evaluator.
        
        Args:
            evaluation_focus: Focus area for evaluation (quality, coherence, etc)
        """
        super().__init__("huggingface-evaluator", evaluation_focus)
        self.focus = evaluation_focus
        
        # Load text quality assessment model
        os.environ["TOKENIZERS_PARALLELISM"] = "false"  # Avoid warnings
        
        # Use sentence-transformers for semantic similarity
        self.similarity_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Set up criteria weightings
        self.criteria = {
            "coherence": 0.25,
            "consistency": 0.25, 
            "distinctiveness": 0.3,
            "grammatical": 0.2
        }
    
    def compute_similarity(self, text1: str, text2: str) -> float:
        """Compute semantic similarity between two texts."""
        # Get embeddings
        embedding1 = self.similarity_model.encode(text1, convert_to_tensor=True)
        embedding2 = self.similarity_model.encode(text2, convert_to_tensor=True)
        
        # Compute cosine similarity
        similarity = util.pytorch_cos_sim(embedding1, embedding2).item()
        return similarity
        
    def analyze_paragraph_structure(self, text: str) -> Dict[str, Any]:
        """Analyze paragraph structure and flow."""
        paragraphs = re.split(r'\n{2,}', text.strip())
        
        return {
            "paragraph_count": len(paragraphs),
            "avg_paragraph_length": sum(len(p) for p in paragraphs) / len(paragraphs) if paragraphs else 0,
            "shortest_paragraph": min(len(p) for p in paragraphs) if paragraphs else 0,
            "longest_paragraph": max(len(p) for p in paragraphs) if paragraphs else 0,
        }
    
    async def evaluate_content(self, original: str, transformed: str) -> Dict[str, float]:
        """Evaluate transformed content against the original."""
        # Semantic similarity (lower is more distinct, but we don't want too low)
        similarity = self.compute_similarity(original, transformed)
        
        # Too similar is bad (not enough transformation)
        # Too different is also bad (lost the plot)
        distinctiveness_score = 1.0 - abs(0.7 - similarity) * 2  # Optimal similarity around 0.7
        
        # Analyze paragraph structure
        orig_structure = self.analyze_paragraph_structure(original)
        trans_structure = self.analyze_paragraph_structure(transformed)
        
        # Coherence proxy: paragraph count ratio (should be similar)
        paragraph_ratio = min(
            orig_structure["paragraph_count"], 
            trans_structure["paragraph_count"]
        ) / max(
            orig_structure["paragraph_count"], 
            trans_structure["paragraph_count"]
        ) if max(orig_structure["paragraph_count"], trans_structure["paragraph_count"]) > 0 else 0.5
        
        # Basic length consistency check
        length_ratio = min(len(original), len(transformed)) / max(len(original), len(transformed))
        
        # Grammatical check (simplified proxy - real implementation would use a grammar model)
        grammatical_score = 0.9  # Assume mostly grammatical
        
        # Combine scores based on criteria weights
        evaluation = {
            "coherence": paragraph_ratio,
            "consistency": length_ratio,
            "distinctiveness": distinctiveness_score,
            "grammatical": grammatical_score
        }
        
        # Calculate weighted score
        weighted_score = sum(evaluation[key] * self.criteria[key] for key in self.criteria)
        evaluation["weighted_score"] = weighted_score
        
        return evaluation
        
    async def transform_content(self, 
                              input_text: str, 
                              transformation_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Evaluate content and provide feedback.
        
        Args:
            input_text: Text to evaluate 
            transformation_params: Parameters for evaluation including previous versions
            
        Returns:
            Evaluation results and feedback
        """
        if transformation_params is None:
            transformation_params = {}
            
        start_time = time.time()
        
        # Extract original and transformed content
        original_content = transformation_params.get("original_content", "")
        transformed_content = input_text
        
        if not original_content:
            return {
                "error": "Original content not provided for comparison",
                "processing_time": time.time() - start_time
            }
            
        # Evaluate the transformation
        evaluation = await self.evaluate_content(original_content, transformed_content)
        
        # Generate feedback based on evaluation results
        feedback = await self._generate_feedback(evaluation, transformation_params)
        
        return {
            "processed_content": feedback,
            "evaluation": evaluation,
            "processing_time": time.time() - start_time,
            "model": self.model_id
        }
        
    async def _generate_feedback(self, 
                              evaluation: Dict[str, float], 
                              params: Dict[str, Any]) -> str:
        """Generate actionable feedback based on evaluation results."""
        chapter_title = params.get("chapter_title", "Unknown Chapter")
        
        feedback_pieces = [f"## Review for: {chapter_title}"]
        feedback_pieces.append(f"\nOverall Score: {evaluation['weighted_score']:.2f}/1.0\n")
        
        # Generate feedback for each criterion
        if evaluation["distinctiveness"] < 0.7:
            feedback_pieces.append("- **Distinctiveness Issue**: The transformed content is too similar to the original. Consider using more varied vocabulary and sentence structures.")
            
        if evaluation["distinctiveness"] > 0.9:  
            feedback_pieces.append("- **Consistency Warning**: The transformed content may be too different from the original, potentially losing key plot elements.")
            
        if evaluation["coherence"] < 0.7:
            feedback_pieces.append("- **Coherence Concern**: The paragraph structure differs significantly from the original. Consider maintaining similar paragraph breaks to preserve reading flow.")
            
        if evaluation["consistency"] < 0.8:
            feedback_pieces.append("- **Length Inconsistency**: The transformed content is significantly longer or shorter than the original. Aim for similar length to maintain pacing.")
            
        # Always add improvement suggestions
        feedback_pieces.append("\n### Improvement Suggestions:")
        feedback_pieces.append("1. Ensure all character names and key plot points are preserved")
        feedback_pieces.append("2. Check for consistent narrative voice throughout the chapter")
        feedback_pieces.append("3. Verify that setting descriptions maintain the same atmosphere as the original")
        
        return "\n".join(feedback_pieces)
