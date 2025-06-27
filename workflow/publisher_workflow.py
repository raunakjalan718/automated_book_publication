from typing import Dict, List, Any, Optional
import asyncio
import uuid
import time
from datetime import datetime

from scrapers.wiki_scraper import WikiSourceScraper
from ai_agents.writer_agent import WriterAgent
from ai_agents.reviewer_agent import ReviewerAgent
from ai_agents.editor_agent import EditorAgent
from storage.content_store import ContentStore

class PublisherWorkflow:
    """Main workflow orchestrator for the book publication process."""
    
    def __init__(self):
        """Initialize the workflow components."""
        self.scraper = WikiSourceScraper()
        self.writer = WriterAgent(use_gemini=True)
        self.reviewer = ReviewerAgent(use_openai=True)
        self.editor = EditorAgent()
        self.storage = ContentStore()
        self.workflow_id = f"workflow_{int(time.time())}_{uuid.uuid4().hex[:8]}"
    
    async def process_chapter(self, chapter_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single chapter through the AI pipeline.
        
        Args:
            chapter_data: Dictionary containing chapter information
            
        Returns:
            Dictionary with processing results and version IDs
        """
        # Store the original chapter
        chapter_id = self.storage.store_original_chapter(chapter_data)
        
        print(f"Processing chapter: {chapter_data['title']} (ID: {chapter_id})")
        
        # Context for AI processing
        context = {
            "chapter_title": chapter_data["title"],
            "chapter_number": chapter_data["chapter_number"]
        }
        
        # Step 1: Writer agent rewrites the content
        print("Rewriting chapter...")
        writer_result = await self.writer.process(chapter_data["content"], context)
        writer_version_id = self.storage.store_chapter_version(
            chapter_id, 
            writer_result["processed_content"], 
            "rewritten",
            {"model": writer_result["model"]}
        )
        
        # Step 2: Reviewer agent reviews the rewritten content
        print("Reviewing rewritten chapter...")
        review_context = {
            **context,
            "previous_versions": [chapter_data["content"]],
            "rewritten_version": writer_result["processed_content"]
        }
        reviewer_result = await self.reviewer.process(writer_result["processed_content"], review_context)
        reviewer_version_id = self.storage.store_chapter_version(
            chapter_id, 
            reviewer_result["processed_content"], 
            "reviewed",
            {"model": reviewer_result["model"]}
        )
        
        # Step 3: Editor agent finalizes the content with feedback
        print("Editing chapter with review feedback...")
        editor_context = {
            **context,
            "previous_versions": [writer_result["processed_content"]],
            "feedback": reviewer_result["processed_content"]
        }
        editor_result = await self.editor.process(writer_result["processed_content"], editor_context)
        editor_version_id = self.storage.store_chapter_version(
            chapter_id, 
            editor_result["processed_content"], 
            "edited",
            {"model": editor_result["model"]}
        )
        
        return {
            "chapter_id": chapter_id,
            "writer_version_id": writer_version_id,
            "reviewer_version_id": reviewer_version_id,
            "editor_version_id": editor_version_id
        }
    
    async def run_workflow(self, start_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Run the full book publication workflow.
        
        Args:
            start_url: Optional starting URL for scraping
            
        Returns:
            Dictionary with workflow results
        """
        start_time = datetime.now()
        
        # Step 1: Scrape all chapters
        print("Scraping chapters...")
        chapters = self.scraper.scrape_book(start_url)
        
        if not chapters:
            print("No chapters found. Workflow ending.")
            return {"status": "failed", "error": "No chapters found"}
        
        print(f"Found {len(chapters)} chapters.")
        
        # Step 2: Process each chapter concurrently
        tasks = []
        for chapter in chapters:
            tasks.append(self.process_chapter(chapter))
        
        results = await asyncio.gather(*tasks)
        
        # Step 3: Save workflow metadata
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        workflow_metadata = {
            "workflow_id": self.workflow_id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": duration,
            "chapter_count": len(chapters),
            "chapter_results": results
        }
        
        self.storage.store_workflow_metadata(self.workflow_id, workflow_metadata)
        
        print(f"Workflow completed in {duration:.2f} seconds.")
        return {
            "status": "success",
            "workflow_id": self.workflow_id,
            "chapter_count": len(chapters),
            "results": results
        }
    
    async def iterative_refinement(self, chapter_id: str, feedback: str) -> Dict[str, Any]:
        """
        Perform iterative refinement on a chapter based on human feedback.
        
        Args:
            chapter_id: ID of the chapter to refine
            feedback: Human feedback for refinement
            
        Returns:
            Dictionary with refinement results
        """
        # Get the latest edited version
        latest_edited = self.storage.get_latest_version(chapter_id, "edited")
        if not latest_edited:
            return {"status": "failed", "error": "No edited version found"}
        
        # Get chapter metadata
        chapter = self.storage.get_chapter(chapter_id)
        if not chapter:
            return {"status": "failed", "error": "Chapter not found"}
        
        context = {
            "chapter_title": chapter["metadata"].get("title"),
            "chapter_number": chapter["metadata"].get("chapter_number"),
            "previous_versions": [latest_edited["content"]],
            "feedback": feedback
        }
        
        # Process with editor agent
        editor_result = await self.editor.process(latest_edited["content"], context)
        
        # Store the refined version
        refined_version_id = self.storage.store_chapter_version(
            chapter_id, 
            editor_result["processed_content"], 
            "refined",
            {
                "model": editor_result["model"],
                "based_on_version": latest_edited["id"],
                "human_feedback": feedback
            }
        )
        
        return {
            "status": "success",
            "chapter_id": chapter_id,
            "refined_version_id": refined_version_id
        }
