import asyncio
import argparse
import os
from typing import Dict, List, Optional

from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel

from workflow.publisher_workflow import PublisherWorkflow
from storage.content_store import ContentStore

# Create FastAPI app
app = FastAPI(title="Automated Book Publisher")

# Create content store
content_store = ContentStore()

# Dictionary to store workflow instances
active_workflows = {}

# Models for API requests/responses
class WorkflowStart(BaseModel):
    start_url: Optional[str] = None

class ChapterFeedback(BaseModel):
    feedback: str

async def run_workflow(workflow_id: str, start_url: Optional[str] = None):
    """Run a workflow in the background."""
    workflow = PublisherWorkflow()
    active_workflows[workflow_id] = {"status": "running", "workflow": workflow, "progress": {"total": 0, "processed": 0}}
    
    try:
        result = await workflow.run_workflow(start_url)
        active_workflows[workflow_id]["status"] = "completed"
        active_workflows[workflow_id]["result"] = result
    except Exception as e:
        active_workflows[workflow_id]["status"] = "failed"
        active_workflows[workflow_id]["error"] = str(e)

@app.post("/workflow/start")
async def start_workflow(
    workflow_request: WorkflowStart,
    background_tasks: BackgroundTasks
):
    """Start a new workflow."""
    workflow = PublisherWorkflow()
    workflow_id = workflow.workflow_id
    
    # Start the workflow in the background
    background_tasks.add_task(run_workflow, workflow_id, workflow_request.start_url)
    
    return {"workflow_id": workflow_id, "status": "started"}

@app.get("/workflow/{workflow_id}")
async def get_workflow_status(workflow_id: str):
    """Get the status of a workflow."""
    if workflow_id not in active_workflows:
        # Try to get from storage
        workflow_data = content_store.get_workflow_metadata(workflow_id)
        if not workflow_data:
            raise HTTPException(status_code=404, detail="Workflow not found")
        return {"workflow_id": workflow_id, "status": "completed", "data": workflow_data["data"]}
    
    workflow_info = active_workflows[workflow_id]
    return {
        "workflow_id": workflow_id,
        "status": workflow_info["status"],
        "progress": workflow_info.get("progress", {}),
        "result": workflow_info.get("result"),
        "error": workflow_info.get("error")
    }

@app.get("/chapters")
async def list_chapters():
    """List all available chapters."""
    chapters = content_store.get_all_chapters()
    return {"chapters": chapters}

@app.get("/chapter/{chapter_id}")
async def get_chapter(chapter_id: str, version_type: Optional[str] = None):
    """Get a specific chapter or its versions."""
    chapter = content_store.get_chapter(chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    
    if version_type:
        latest_version = content_store.get_latest_version(chapter_id, version_type)
        if not latest_version:
            raise HTTPException(status_code=404, detail=f"No {version_type} version found")
        return {
            "chapter": chapter,
            "version": latest_version
        }
    
    # Get all versions
    versions = content_store.get_all_versions(chapter_id)
    
    return {
        "chapter": chapter,
        "versions": versions
    }

@app.post("/chapter/{chapter_id}/refine")
async def refine_chapter(
    chapter_id: str,
    feedback: ChapterFeedback
):
    """Refine a chapter with human feedback."""
    chapter = content_store.get_chapter(chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    
    # Create a new workflow for refinement
    workflow = PublisherWorkflow()
    result = await workflow.iterative_refinement(chapter_id, feedback.feedback)
    
    if result["status"] == "failed":
        raise HTTPException(status_code=400, detail=result["error"])
        
    return result

@app.get("/version/{version_id}")
async def get_version(version_id: str):
    """Get a specific version of a chapter."""
    version = content_store.get_chapter_version(version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    
    return version

def start_api():
    """Start the FastAPI server."""
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

async def run_cli():
    """Run the workflow from the command line."""
    parser = argparse.ArgumentParser(description="Automated Book Publisher")
    parser.add_argument("--start-url", help="URL to start scraping from")
    parser.add_argument("--chapter", help="Process a specific chapter ID")
    parser.add_argument("--list-chapters", action="store_true", help="List all available chapters")
    parser.add_argument("--api", action="store_true", help="Start the API server")
    
    args = parser.parse_args()
    
    if args.api:
        start_api()
        return
    
    if args.list_chapters:
        store = ContentStore()
        chapters = store.get_all_chapters()
        print(f"Found {len(chapters)} chapters:")
        for ch in chapters:
            print(f"- {ch['id']}: {ch['metadata'].get('title')}")
        return
    
    if args.chapter:
        store = ContentStore()
        chapter = store.get_chapter(args.chapter)
        if not chapter:
            print(f"Chapter {args.chapter} not found.")
            return
        
        print(f"Processing single chapter: {chapter['metadata'].get('title')}")
        workflow = PublisherWorkflow()
        result = await workflow.iterative_refinement(args.chapter, "Please refine this chapter")
        print(f"Refinement result: {result}")
        return
    
    # Default: run full workflow
    workflow = PublisherWorkflow()
    result = await workflow.run_workflow(args.start_url)
    print(f"Workflow completed: {result}")

if __name__ == "__main__":
    asyncio.run(run_cli())
