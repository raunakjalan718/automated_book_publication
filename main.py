import os
os.environ["CHROMA_IGNORE_VERSION"] = "True"  # Bypass ChromaDB version checks

import logging
import sys
import asyncio
import argparse
from datetime import datetime
import uuid
from typing import Dict, List, Optional

from fastapi import FastAPI, BackgroundTasks, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Setup detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("book_publisher")

# Create FastAPI app with detailed configuration
app = FastAPI(
    title="Automated Book Publisher",
    description="API for book content transformation and publication workflow",
    version="1.0.0",
    debug=True
)

# Add CORS middleware to allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import components with proper error handling
try:
    logger.info("Initializing storage...")
    from storage.version_manager import VersionManager
    version_manager = VersionManager()
    
    logger.info("Importing workflow components...")
    from workflow.publication_process import PublicationProcess
    from scrapers.content_harvester import ContentHarvester
except Exception as e:
    logger.error(f"Import error during initialization: {e}")
    import traceback
    logger.error(traceback.format_exc())

# Dictionary to store active processes
active_processes = {}

# Models for API requests/responses
class ProcessStart(BaseModel):
    start_url: Optional[str] = None
    max_chapters: Optional[int] = 10

class ContentFeedback(BaseModel):
    feedback: str
    reviewer_name: Optional[str] = "anonymous"

class ContentTransform(BaseModel):
    content: str
    style: Optional[str] = "creative"
    intensity: Optional[int] = 7  # Scale 1-10

# API Status response model
class StatusResponse(BaseModel):
    status: str
    service: str
    version: str
    timestamp: str

# Helper Functions
def get_process_manager():
    """Dependency to get version manager instance."""
    return version_manager

async def run_process_with_logging(process_id: str, start_url: Optional[str] = None, max_chapters: int = 10):
    """Run a publication process with comprehensive logging."""
    logger.info(f"Background task started for process {process_id}")
    process = PublicationProcess()
    active_processes[process_id] = {
        "status": "running", 
        "process": process,
        "start_time": datetime.now().isoformat(),
        "progress": {"total": 0, "processed": 0}
    }
    
    try:
        logger.info(f"Running publication process {process_id} with URL: {start_url}")
        result = await process.run_publication_process(start_url)
        
        logger.info(f"Process {process_id} completed successfully")
        active_processes[process_id]["status"] = "completed"
        active_processes[process_id]["result"] = result
        active_processes[process_id]["end_time"] = datetime.now().isoformat()
    except Exception as e:
        logger.error(f"Process {process_id} failed: {e}")
        active_processes[process_id]["status"] = "failed"
        active_processes[process_id]["error"] = str(e)
        active_processes[process_id]["end_time"] = datetime.now().isoformat()
        import traceback
        logger.error(traceback.format_exc())

# API Endpoints
@app.get("/", response_model=StatusResponse)
async def root():
    """Root endpoint providing basic API information."""
    return {
        "status": "online",
        "service": "Automated Book Publisher",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check(vm: VersionManager = Depends(get_process_manager)):
    """Health check endpoint to verify system components."""
    try:
        # Check database connection by getting content
        content_items = vm.get_all_content()
        
        # Check file system access
        screenshots_dir = os.path.join(os.getcwd(), "screenshots")
        os.makedirs(screenshots_dir, exist_ok=True)
        fs_access = os.access(screenshots_dir, os.W_OK)
        
        return {
            "status": "healthy",
            "database": "connected",
            "content_count": len(content_items) if content_items else 0,
            "file_system_access": fs_access,
            "api_version": "1.0.0",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.post("/process/start")
async def start_process(
    process_request: ProcessStart, 
    background_tasks: BackgroundTasks
):
    """Start a new book publication process."""
    try:
        logger.info(f"Creating new process with URL: {process_request.start_url}")
        process = PublicationProcess()
        process_id = process.process_id
        
        logger.info(f"Starting process {process_id}")
        # Add to background tasks
        background_tasks.add_task(
            run_process_with_logging, 
            process_id=process_id,
            start_url=process_request.start_url,
            max_chapters=process_request.max_chapters or 10
        )
        
        return {
            "process_id": process_id, 
            "status": "started",
            "start_time": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error starting process: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/process/{process_id}")
async def get_process_status(
    process_id: str,
    vm: VersionManager = Depends(get_process_manager)
):
    """Get the status of a publication process."""
    if process_id in active_processes:
        process_info = active_processes[process_id]
        return {
            "process_id": process_id,
            "status": process_info["status"],
            "start_time": process_info.get("start_time"),
            "end_time": process_info.get("end_time"),
            "progress": process_info.get("progress"),
            "result": process_info.get("result"),
            "error": process_info.get("error")
        }
    
    # If not in active processes, try to get from storage
    try:
        process_data = vm.get_project_metadata(process_id)
        if not process_data:
            raise HTTPException(status_code=404, detail="Process not found")
        
        return {
            "process_id": process_id, 
            "status": "completed", 
            "data": process_data["data"]
        }
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        logger.error(f"Error retrieving process {process_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/content")
async def list_content(
    limit: int = 100,
    content_type: Optional[str] = "source",
    vm: VersionManager = Depends(get_process_manager)
):
    """List all available content items."""
    try:
        content_items = vm.get_all_content(content_type)
        
        simplified_items = []
        for item in content_items[:limit]:
            simplified_items.append({
                "id": item["id"], 
                "title": item["metadata"].get("title", "Untitled"), 
                "chapter": item["metadata"].get("chapter_number"),
                "timestamp": item["metadata"].get("timestamp"),
                "content_length": len(item["content"]) if "content" in item else 0
            })
        
        return {
            "content_items": simplified_items,
            "total_count": len(content_items),
            "returned_count": len(simplified_items)
        }
    except Exception as e:
        logger.error(f"Error listing content: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/content/{content_id}")
async def get_content(
    content_id: str, 
    version_type: Optional[str] = None,
    include_content: bool = True,
    vm: VersionManager = Depends(get_process_manager)
):
    """Get a specific content item or its versions."""
    try:
        content = vm.get_content(content_id)
        if not content:
            raise HTTPException(status_code=404, detail="Content not found")
        
        # Prepare response with or without full content text
        content_response = {
            "id": content["id"],
            "metadata": content["metadata"]
        }
        if include_content:
            content_response["content"] = content["content"]
        
        if version_type:
            latest_version = vm.get_latest_version(content_id, version_type)
            if not latest_version:
                raise HTTPException(status_code=404, detail=f"No {version_type} version found")
            
            version_response = {
                "id": latest_version["id"],
                "metadata": latest_version["metadata"]
            }
            if include_content:
                version_response["content"] = latest_version["content"]
            
            return {
                "content": content_response,
                "version": version_response
            }
        
        # Get all versions
        versions = vm.get_all_versions(content_id)
        
        # Prepare versions responses
        version_responses = []
        for version in versions:
            version_response = {
                "id": version["id"],
                "metadata": version["metadata"]
            }
            if include_content:
                version_response["content"] = version["content"]
            version_responses.append(version_response)
        
        return {
            "content": content_response,
            "versions": version_responses
        }
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        logger.error(f"Error retrieving content {content_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/content/{content_id}/refine")
async def refine_content(
    content_id: str,
    feedback: ContentFeedback,
    vm: VersionManager = Depends(get_process_manager)
):
    """Refine content with human feedback."""
    try:
        content = vm.get_content(content_id)
        if not content:
            raise HTTPException(status_code=404, detail="Content not found")
        
        logger.info(f"Refining content {content_id} based on feedback")
        
        # Create a new process for refinement
        process = PublicationProcess()
        
        # Add reviewer information to feedback
        enriched_feedback = f"Feedback from {feedback.reviewer_name}:\n\n{feedback.feedback}"
        
        # Process refinement
        result = await process.refine_content(content_id, enriched_feedback)
        
        if result["status"] == "failed":
            raise HTTPException(status_code=400, detail=result["error"])
        
        return {
            "status": "success",
            "content_id": content_id,
            "refined_version_id": result["refined_version_id"],
            "reviewer": feedback.reviewer_name,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        logger.error(f"Error refining content {content_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/version/{version_id}")
async def get_version(
    version_id: str,
    vm: VersionManager = Depends(get_process_manager)
):
    """Get a specific version of content."""
    try:
        version = vm.get_version(version_id)
        if not version:
            raise HTTPException(status_code=404, detail="Version not found")
        
        return version
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        logger.error(f"Error retrieving version {version_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/test/transform")
async def test_transform(
    transform_request: ContentTransform
):
    """Test content transformation without storing results."""
    try:
        from ai_agents.gemini_transformer import GeminiTransformer
        
        transformer = GeminiTransformer(transform_request.style)
        
        result = await transformer.transform_content(
            transform_request.content,
            {
                "intensity": transform_request.intensity,
                "test_mode": True
            }
        )
        
        return {
            "original": transform_request.content,
            "transformed": result.get("transformed_content", ""),
            "error": result.get("error"),
            "stats": {
                "original_length": len(transform_request.content),
                "transformed_length": len(result.get("transformed_content", "")),
                "processing_time": result.get("processing_time")
            }
        }
    except Exception as e:
        logger.error(f"Error in test transform: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def start_api(port=9000):
    """Start the FastAPI server with customizable port."""
    import uvicorn
    try:
        logger.info(f"Starting API server on port {port}...")
        # Use reload=False in production for stability
        uvicorn.run("main:app", host="0.0.0.0", port=port, log_level="info")
    except Exception as e:
        logger.error(f"Error starting server: {e}")
        import traceback
        traceback.print_exc()

async def run_cli():
    """Run the application from command line with various options."""
    parser = argparse.ArgumentParser(description="Automated Book Publisher")
    parser.add_argument("--start-url", help="URL to start harvesting from")
    parser.add_argument("--content-id", help="Process a specific content ID")
    parser.add_argument("--list-content", action="store_true", help="List all available content")
    parser.add_argument("--api", action="store_true", help="Start the API server")
    parser.add_argument("--port", type=int, default=9000, help="Port for the API server")
    parser.add_argument("--feedback", help="Feedback for content refinement (use with --content-id)")
    
    args = parser.parse_args()
    
    if args.api:
        start_api(args.port)
        return
    
    if args.list_content:
        try:
            content_items = version_manager.get_all_content()
            print(f"Found {len(content_items)} content items:")
            for item in content_items:
                print(f"- {item['id']}: {item['metadata'].get('title', 'Untitled')}")
        except Exception as e:
            print(f"Error listing content: {e}")
        return
    
    if args.content_id:
        try:
            content = version_manager.get_content(args.content_id)
            if not content:
                print(f"Content {args.content_id} not found.")
                return
            
            print(f"Processing content: {content['metadata'].get('title', 'Untitled')}")
            
            if args.feedback:
                process = PublicationProcess()
                result = await process.refine_content(args.content_id, args.feedback)
                print(f"Refinement result: {result}")
            else:
                # Just display content info if no feedback provided
                print(f"Content ID: {content['id']}")
                print(f"Title: {content['metadata'].get('title', 'Untitled')}")
                print(f"Chapter: {content['metadata'].get('chapter_number', 'Unknown')}")
                print(f"Length: {len(content['content'])} characters")
                print("\nFirst 100 characters:")
                print(content['content'][:100] + "...")
        except Exception as e:
            print(f"Error processing content: {e}")
        return
    
    if args.start_url:
        try:
            process = PublicationProcess()
            print(f"Starting publication process with URL: {args.start_url}")
            result = await process.run_publication_process(args.start_url)
            print(f"Process completed: {result}")
        except Exception as e:
            print(f"Error running process: {e}")
        return
    
    # Default: run API server
    logger.info("No specific command given. Starting API server...")
    start_api(args.port)

if __name__ == "__main__":
    logger.info("Application starting...")
    try:
        asyncio.run(run_cli())
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    except Exception as e:
        logger.error(f"Application crashed: {e}")
        import traceback
        logger.error(traceback.format_exc())
