from typing import Dict, Any, Optional, List
import time
from datetime import datetime
import re
import asyncio
import string
import random

from .language_processor import ContentProcessor

class TextEvaluator(ContentProcessor):
    """Simple text evaluation without heavy dependencies."""
    
    def __init__(self, evaluation_focus: str = "quality"):
        """Initialize the text evaluator."""
        super().__init__("text-evaluator", evaluation_focus)
        self.focus = evaluation_focus
        
        # Set up criteria weightings
        self.criteria = {
            "coherence": 0.25,
            "consistency": 0.25, 
            "distinctiveness": 0.3,
            "grammatical": 0.2
        }
    
    def compute_text_similarity(self, text1: str, text2: str) -> float:
        """Compute basic text similarity using word overlap."""
        # Convert to lowercase and remove punctuation
        def normalize(text):
            text = text.lower()
            text = re.sub(f'[{string.punctuation}]', '', text)
            return text
        
        words1 = set(normalize(text1).split())
        words2 = set(normalize(text2).split())
        
        # Calculate Jaccard similarity
        if not words1 or not words2:
            return 0.0
            
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
        
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
        # Basic similarity (lower is more distinct, but we don't want too low)
        similarity = self.compute_text_similarity(original, transformed)
        
        # Too similar is bad (not enough transformation)
        # Too different is also bad (lost the plot)
        distinctiveness_score = 1.0 - abs(0.6 - similarity) * 2  # Optimal around 0.6
        
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
        
        # Grammar check proxy using sentence length variety
        def sentence_variety(text):
            sentences = re.split(r'[.!?]+', text)
            if len(sentences) <= 1:
                return 0.5
            lengths = [len(s.strip()) for s in sentences if s.strip()]
            if not lengths:
                return 0.5
            avg_len = sum(lengths) / len(lengths)
            variance = sum((l - avg_len) ** 2 for l in lengths) / len(lengths)
            return min(1.0, variance / 500)  # Normalize
        
        grammatical_score = 0.5 + (sentence_variety(transformed) * 0.5)
        
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
