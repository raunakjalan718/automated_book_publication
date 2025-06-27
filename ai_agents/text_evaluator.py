# ai_agents/text_evaluator.py
from typing import Dict, Any, Optional
import time
from datetime import datetime
import re
import asyncio
import random

from .language_processor import ContentProcessor

class TextEvaluator(ContentProcessor):
    """Simple text evaluation using basic algorithms instead of ML models."""
    
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
    
    def jaccard_similarity(self, text1: str, text2: str) -> float:
        """Compute basic text similarity using Jaccard similarity of words."""
        # Convert texts to sets of words
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        # Calculate Jaccard similarity
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
        
    def analyze_text_structure(self, text: str) -> Dict[str, Any]:
        """Analyze text structure metrics."""
        paragraphs = re.split(r'\n{2,}', text.strip())
        sentences = re.split(r'[.!?]+', text)
        
        # Filter out empty strings
        paragraphs = [p for p in paragraphs if p.strip()]
        sentences = [s for s in sentences if s.strip()]
        
        return {
            "paragraph_count": len(paragraphs),
            "sentence_count": len(sentences),
            "avg_paragraph_length": sum(len(p) for p in paragraphs) / max(len(paragraphs), 1),
            "avg_sentence_length": sum(len(s) for s in sentences) / max(len(sentences), 1),
        }
    
    async def evaluate_content(self, original: str, transformed: str) -> Dict[str, float]:
        """Evaluate transformed content against the original."""
        # Calculate similarity
        similarity = self.jaccard_similarity(original, transformed)
        
        # We want similarity around 0.5-0.6 (not too similar, not too different)
        # Transform to a score where 0.55 similarity = 1.0 score, decreasing on either side
        distinctiveness_score = 1.0 - abs(0.55 - similarity) * 2
        distinctiveness_score = max(0.0, min(1.0, distinctiveness_score))  # Clamp to [0,1]
        
        # Analyze structure
        orig_metrics = self.analyze_text_structure(original)
        trans_metrics = self.analyze_text_structure(transformed)
        
        # Coherence based on paragraph ratio
        para_ratio = min(orig_metrics["paragraph_count"], trans_metrics["paragraph_count"]) / \
                     max(orig_metrics["paragraph_count"], trans_metrics["paragraph_count"]) \
                     if max(orig_metrics["paragraph_count"], trans_metrics["paragraph_count"]) > 0 else 0.5
                     
        # Consistency based on overall length
        length_ratio = min(len(original), len(transformed)) / \
                      max(len(original), len(transformed))
        
        # Simple grammatical check (based on sentence length variation)
        orig_sent_lengths = [len(s.strip()) for s in re.split(r'[.!?]+', original) if s.strip()]
        trans_sent_lengths = [len(s.strip()) for s in re.split(r'[.!?]+', transformed) if s.strip()]
        
        orig_variance = sum((l - sum(orig_sent_lengths)/max(len(orig_sent_lengths), 1))**2 
                           for l in orig_sent_lengths) / max(len(orig_sent_lengths), 1) if orig_sent_lengths else 0
        trans_variance = sum((l - sum(trans_sent_lengths)/max(len(trans_sent_lengths), 1))**2 
                           for l in trans_sent_lengths) / max(len(trans_sent_lengths), 1) if trans_sent_lengths else 0
        
        # Good writing has sentence length variation, so we want similar variance
        variance_ratio = min(orig_variance, trans_variance) / max(orig_variance, trans_variance) if max(orig_variance, trans_variance) > 0 else 0.5
        grammatical_score = 0.7 + (variance_ratio * 0.3)  # Base score of 0.7, up to 1.0
        
        # Combine scores
        evaluation = {
            "coherence": para_ratio,
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
            transformation_params: Parameters including original content
            
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
        
        # Generate feedback
        feedback = await self._generate_feedback(evaluation, transformation_params)
        
        return {
            "processed_content": feedback,
            "evaluation": evaluation,
            "processing_time": time.time() - start_time,
            "model": self.model_id
        }
        
    async def _generate_feedback(self, evaluation: Dict[str, float], params: Dict[str, Any]) -> str:
        """Generate actionable feedback based on evaluation results."""
        chapter_title = params.get("chapter_title", "Unknown Chapter")
        
        feedback_parts = [f"## Review for: {chapter_title}", 
                        f"\nOverall Quality Score: {evaluation['weighted_score']:.2f}/1.0\n"]
        
        # Add specific feedback based on scores
        if evaluation["distinctiveness"] < 0.7:
            feedback_parts.append("- **Content Similarity Issue**: The transformed version is too similar to the original. Try using more varied vocabulary and restructuring sentences.")
        
        if evaluation["distinctiveness"] > 0.9:
            feedback_parts.append("- **Excessive Deviation Warning**: The content differs too much from the original, which may lose important story elements.")
            
        if evaluation["coherence"] < 0.7:
            feedback_parts.append("- **Structure Inconsistency**: The paragraph organization differs significantly from the original, potentially disrupting reading flow.")
            
        if evaluation["consistency"] < 0.8:
            feedback_parts.append("- **Length Discrepancy**: The transformed content's length varies significantly from the original. Consider adjusting to maintain similar pacing.")
            
        # Always include improvement suggestions
        feedback_parts.append("\n### Improvement Recommendations:")
        feedback_parts.append("1. Verify all character names and plot points are preserved accurately")
        feedback_parts.append("2. Review narrative perspective for consistency throughout")
        feedback_parts.append("3. Check that important scene descriptions retain their atmospheric qualities")
        feedback_parts.append("4. Ensure dialogue captures each character's unique voice")
        
        return "\n".join(feedback_parts)
