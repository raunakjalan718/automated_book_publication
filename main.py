import asyncio
import argparse
import os
from typing import Dict, List, Optional

from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel

from workflow.publication_process import PublicationProcess
from storage.version_manager import VersionManager

# Create FastAPI app
app = FastAPI(title="Automated Book Publisher")

# Create version manager for storage access
version_manager = VersionManager()

# Dictionary to store active processes
active_processes = {}

# Models for API requests/responses
class ProcessStart(BaseModel):
    start_url: Optional[str] = None

class ContentFeedback(BaseModel):
    feedback: str

async def run_process(process_id: str, start_url: Optional[str] = None):
    """Run a publication process in the background."""
    process = PublicationProcess()
    active_processes[process_id] = {"status": "running", "process": process}
    
    try:
        result = await process.run_publication_process(start_url)
        active_processes[process_id]["status"] = "completed"
        active_processes[process_id]["result"] = result
    except Exception as e:
        active_processes[process_id]["status"] = "failed"
        active_processes[process_id]["error"] = str(e)

@app.post("/process/start")
async def start_process(
    process_request: ProcessStart,
    background_tasks: BackgroundTasks
):
    """Start a new publication process."""
    process = PublicationProcess()
    process_id = process.process_id
    
    # Start the process in the background
    background_tasks.add_task(run_process, process_id, process_request.start_url)
    
    return {"process_id": process_id, "status": "started"}

@app.get("/process/{process_id}")
async def get_process_status(process_id: str):
    """Get the status of a publication process."""
    if process_id not in active_processes:
        # Try to get from storage
        process_data = version_manager.get_project_metadata(process_id)
        if not process_data:
            raise HTTPException(status_code=404, detail="Process not found")
        return {"process_id": process_id, "status": "completed", "data": process_data["data"]}
    
    process_info = active_processes[process_id]
    return {
        "process_id": process_id,
        "status": process_info["status"],
        "result": process_info.get("result"),
        "error": process_info.get("error")
    }

@app.get("/content")
async def list_content():
    """List all available content items."""
    content_items = version_manager.get_all_content()
    simplified_items = [
        {
            "id": item["id"], 
            "title": item["metadata"].get("title"), 
            "chapter": item["metadata"].get("chapter_number")
        }
        for item in content_items
    ]
    return {"content_items": simplified_items}

@app.get("/content/{content_id}")
async def get_content(content_id: str, version_type: Optional[str] = None):
    """Get a specific content item or its versions."""
    content = version_manager.get_content(content_id)
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    
    if version_type:
        latest_version = version_manager.get_latest_version(content_id, version_type)
        if not latest_version:
            raise HTTPException(status_code=404, detail=f"No {version_type} version found")
        return {
            "content": content,
            "version": latest_version
        }
    
    # Get all versions
    versions = version_manager.get_all_versions(content_id)
    
    return {
        "content": content,
        "versions": versions
    }

@app.post("/content/{content_id}/refine")
async def refine_content(
    content_id: str,
    feedback: ContentFeedback
):
    """Refine content with human feedback."""
    content = version_manager.get_content(content_id)
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    
    # Create a new process for refinement
    process = PublicationProcess()
    result = await process.refine_content(content_id, feedback.feedback)
    
    if result["status"] == "failed":
        raise HTTPException(status_code=400, detail=result["error"])
        
    return result

@app.get("/version/{version_id}")
async def get_version(version_id: str):
    """Get a specific version of content."""
    version = version_manager.get_version(version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    
    return version

def start_api():
    """Start the FastAPI server."""
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

async def run_cli():
    """Run the publication process from the command line."""
    parser = argparse.ArgumentParser(description="Automated Book Publisher")
    parser.add_argument("--start-url", help="URL to start harvesting from")
    parser.add_argument("--content-id", help="Process a specific content ID")
    parser.add_argument("--list-content", action="store_true", help="List all available content")
    parser.add_argument("--api", action="store_true", help="Start the API server")
    
    args = parser.parse_args()
    
    if args.api:
        start_api()
        return
    
    if args.list_content:
        vm = VersionManager()
        content_items = vm.get_all_content()
        print(f"Found {len(content_items)} content items:")
        for item in content_items:
            print(f"- {item['id']}: {item['metadata'].get('title')}")
        return
    
    if args.content_id:
        vm = VersionManager()
        content = vm.get_content(args.content_id)
        if not content:
            print(f"Content {args.content_id} not found.")
            return
        
        print(f"Processing content: {content['metadata'].get('title')}")
        process = PublicationProcess()
        result = await process.refine_content(args.content_id, "Please refine this content for improved readability")
        print(f"Refinement result: {result}")
        return
    
    # Default: run full process
    process = PublicationProcess()
    result = await process.run_publication_process(args.start_url)
    print(f"Process completed: {result}")

if __name__ == "__main__":
    asyncio.run(run_cli())
