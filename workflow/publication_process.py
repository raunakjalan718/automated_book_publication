from typing import Dict, List, Any, Optional
import asyncio
import uuid
import time
from datetime import datetime
import os

from scrapers.content_harvester import ContentHarvester
from ai_agents.gemini_transformer import GeminiTransformer
from ai_agents.huggingface_evaluator import HuggingFaceEvaluator
from storage.version_manager import VersionManager

class PublicationProcess:
    """Content publication process orchestrator."""
    
    def __init__(self, db_path: str = None):
        """
        Initialize the publication process.
        
        Args:
            db_path: Path to the database directory
        """
        self.harvester = ContentHarvester()
        self.transformer = GeminiTransformer("creative")
        self.evaluator = HuggingFaceEvaluator("quality")
        self.version_manager = VersionManager(db_path)
        
        # Generate a unique process ID
        self.process_id = f"process_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        self.start_time = datetime.now()
        
        # Process metrics
        self.metrics = {
            "chapters_processed": 0,
            "total_characters": 0,
            "transformation_time": 0,
            "evaluation_time": 0
        }
    
    async def process_content_item(self, content_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single content item through the transformation pipeline.
        
        Args:
            content_data: Dictionary with content and metadata
            
        Returns:
            Processing results and version IDs
        """
        processing_start = time.time()
        
        # Store the original content
        content_id = self.version_manager.store_source_content(content_data)
        
        print(f"Processing content: {content_data['title']} (ID: {content_id})")
        
        # Prepare transformation parameters
        transform_params = {
            "chapter_title": content_data["title"],
            "chapter_number": content_data["chapter_number"],
            "source_url": content_data["url"]
        }
        
        # Step 1: Transform the content
        print("Transforming content...")
        transform_start = time.time()
        transform_result = await self.transformer.transform_content(content_data["content"], transform_params)
        transform_time = time.time() - transform_start
        
        # Store the transformed version
        if "error" not in transform_result:
            transform_version_id = self.version_manager.store_content_version(
                content_id,
                transform_result["transformed_content"],
                "transformed",
                {
                    "model": transform_result["model"],
                    "transformation_style": transform_result["transformation_style"],
                    "processing_time": transform_result["processing_time"]
                }
            )
        else:
            print(f"Error transforming content: {transform_result['error']}")
            return {
                "content_id": content_id,
                "error": transform_result["error"],
                "status": "failed"
            }
        
        # Step 2: Evaluate the transformed content
        print("Evaluating transformed content...")
        eval_start = time.time()
        eval_params = {
            "chapter_title": content_data["title"],
            "original_content": content_data["content"]
        }
        eval_result = await self.evaluator.transform_content(
            transform_result["transformed_content"], 
            eval_params
        )
        eval_time = time.time() - eval_start
        
        # Store the evaluation
        if "error" not in eval_result:
            eval_version_id = self.version_manager.store_content_version(
                content_id,
                eval_result["processed_content"],
                "evaluation",
                {
                    "model": eval_result["model"],
                    "evaluation_scores": eval_result["evaluation"],
                    "processing_time": eval_result["processing_time"]
                }
            )
        else:
            print(f"Error evaluating content: {eval_result['error']}")
            eval_version_id = None
        
        # Update metrics
        self.metrics["chapters_processed"] += 1
        self.metrics["total_characters"] += len(content_data["content"])
        self.metrics["transformation_time"] += transform_time
        self.metrics["evaluation_time"] += eval_time
        
        return {
            "content_id": content_id,
            "transform_version_id": transform_version_id,
            "eval_version_id": eval_version_id,
            "processing_time": time.time() - processing_start,
            "status": "success"
        }
    
    async def run_publication_process(self, start_url: str = None) -> Dict[str, Any]:
        """
        Run the complete publication process.
        
        Args:
            start_url: URL to start content harvesting
            
        Returns:
            Process results and statistics
        """
        # Default URL if none provided
        if start_url is None:
            from dotenv import load_dotenv
            load_dotenv()
            start_url = os.getenv("INITIAL_CHAPTER_URL", 
                                "https://en.wikisource.org/wiki/The_Gates_of_Morning/Book_1/Chapter_1")
        
        # Step 1: Harvest content
        print(f"Harvesting content from: {start_url}")
        content_items = self.harvester.harvest_content_sequence(start_url)
        
        if not content_items:
            print("No content found. Process ending.")
            return {"status": "failed", "error": "No content found"}
        
        print(f"Found {len(content_items)} content items.")
        
        # Step 2: Process each content item
        processing_tasks = []
        for item in content_items:
            task = self.process_content_item(item)
            processing_tasks.append(task)
        
        results = await asyncio.gather(*processing_tasks)
        
        # Step 3: Compile process results
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        
        process_results = {
            "process_id": self.process_id,
            "start_time": self.start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": duration,
            "content_count": len(content_items),
            "processing_results": results,
            "metrics": self.metrics
        }
        
        # Store process metadata
        self.version_manager.store_project_metadata(self.process_id, process_results)
        
        print(f"Publication process completed in {duration:.2f} seconds.")
        print(f"Processed {self.metrics['chapters_processed']} chapters with {self.metrics['total_characters']} characters.")
        
        return {
            "status": "success",
            "process_id": self.process_id,
            "content_count": len(content_items),
            "results": results,
            "metrics": self.metrics
        }
        
    async def refine_content(self, content_id: str, feedback: str) -> Dict[str, Any]:
        """
        Refine content based on feedback.
        
        Args:
            content_id: ID of the content to refine
            feedback: Feedback for refinement
            
        Returns:
            Refinement results
        """
        # Get the most recent transformed version
        latest_transformed = self.version_manager.get_latest_version(content_id, "transformed")
        if not latest_transformed:
            return {"status": "failed", "error": "No transformed version found"}
        
        # Get original content
        original = self.version_manager.get_content(content_id)
        if not original:
            return {"status": "failed", "error": "Original content not found"}
        
        # Prepare refinement parameters
        refine_params = {
            "chapter_title": original["metadata"].get("title"),
            "chapter_number": original["metadata"].get("chapter_number"),
            "previous_version": latest_transformed["content"],
            "feedback": feedback
        }
        
        # Process with transformer for refinement
        refine_result = await self.transformer.transform_content(latest_transformed["content"], refine_params)
        
        # Store the refined version
        if "error" not in refine_result:
            refined_version_id = self.version_manager.store_content_version(
                content_id,
                refine_result["transformed_content"],
                "refined",
                {
                    "model": refine_result["model"],
                    "based_on_version": latest_transformed["id"],
                    "human_feedback": feedback
                }
            )
        else:
            return {"status": "failed", "error": refine_result["error"]}
        
        return {
            "status": "success",
            "content_id": content_id,
            "refined_version_id": refined_version_id
        }
