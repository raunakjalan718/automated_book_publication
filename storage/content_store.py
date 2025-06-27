import chromadb
import os
import json
from typing import Dict, List, Optional, Any
import numpy as np
from datetime import datetime
from config import CHROMA_DB_DIRECTORY

class ContentStore:
    """Storage class for managing content using ChromaDB."""
    
    def __init__(self):
        """Initialize the content store with ChromaDB."""
        self.client = chromadb.PersistentClient(path=CHROMA_DB_DIRECTORY)
        
        # Create collections if they don't exist
        self.chapters_collection = self._get_or_create_collection("chapters")
        self.versions_collection = self._get_or_create_collection("chapter_versions")
        self.metadata_collection = self._get_or_create_collection("metadata")
    
    def _get_or_create_collection(self, name: str):
        """Get a collection or create it if it doesn't exist."""
        try:
            return self.client.get_collection(name=name)
        except:
            return self.client.create_collection(name=name)
    
    def store_original_chapter(self, chapter_data: Dict[str, Any]) -> str:
        """
        Store an original chapter from the scraper.
        
        Args:
            chapter_data: Dictionary containing chapter information
            
        Returns:
            Document ID of the stored chapter
        """
        chapter_id = f"chapter_{chapter_data['chapter_number']}"
        
        # Store the main chapter content
        metadata = {
            "title": chapter_data["title"],
            "chapter_number": chapter_data["chapter_number"],
            "url": chapter_data["url"],
            "screenshot_path": chapter_data["screenshot_path"],
            "type": "original"
        }
        
        self.chapters_collection.upsert(
            ids=[chapter_id],
            documents=[chapter_data["content"]],
            metadatas=[metadata]
        )
        
        return chapter_id
    
    def store_chapter_version(self, 
                             chapter_id: str, 
                             content: str, 
                             version_type: str, 
                             metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Store a version of a chapter (rewritten, reviewed, edited).
        
        Args:
            chapter_id: The ID of the original chapter
            content: The content of this version
            version_type: Type of version (e.g., "rewritten", "reviewed", "edited")
            metadata: Additional metadata for the version
            
        Returns:
            Version ID of the stored version
        """
        if metadata is None:
            metadata = {}
            
        # Get chapter information
        chapter_results = self.chapters_collection.get(ids=[chapter_id])
        chapter_metadata = chapter_results["metadatas"][0] if chapter_results["metadatas"] else {}
        
        # Create version ID
        version_count = self.get_version_count(chapter_id, version_type)
        version_id = f"{chapter_id}_v{version_type}_{version_count + 1}"
        
        # Prepare version metadata
        version_metadata = {
            "chapter_id": chapter_id,
            "chapter_number": chapter_metadata.get("chapter_number"),
            "title": chapter_metadata.get("title"),
            "version_type": version_type,
            "version_number": version_count + 1,
            "timestamp": datetime.now().isoformat()
        }
        version_metadata.update(metadata)
        
        # Store the version
        self.versions_collection.upsert(
            ids=[version_id],
            documents=[content],
            metadatas=[version_metadata]
        )
        
        return version_id
    
    def get_version_count(self, chapter_id: str, version_type: str) -> int:
        """Get the count of versions for a chapter of a specific type."""
        results = self.versions_collection.query(
            query_texts=[version_type],
            where={"chapter_id": chapter_id, "version_type": version_type}
        )
        return len(results["ids"])
    
    def get_chapter(self, chapter_id: str) -> Dict[str, Any]:
        """Get a chapter by ID."""
        results = self.chapters_collection.get(ids=[chapter_id])
        if not results["documents"]:
            return None
            
        return {
            "id": chapter_id,
            "content": results["documents"][0],
            "metadata": results["metadatas"][0] if results["metadatas"] else {}
        }
    
    def get_chapter_version(self, version_id: str) -> Dict[str, Any]:
        """Get a specific version of a chapter."""
        results = self.versions_collection.get(ids=[version_id])
        if not results["documents"]:
            return None
            
        return {
            "id": version_id,
            "content": results["documents"][0],
            "metadata": results["metadatas"][0] if results["metadatas"] else {}
        }
    
    def get_latest_version(self, chapter_id: str, version_type: str) -> Optional[Dict[str, Any]]:
        """Get the latest version of a specific type for a chapter."""
        results = self.versions_collection.query(
            query_texts=[version_type],
            where={"chapter_id": chapter_id, "version_type": version_type},
            n_results=1
        )
        
        if not results["documents"] or len(results["documents"]) == 0:
            return None
            
        return {
            "id": results["ids"][0][0],
            "content": results["documents"][0][0],
            "metadata": results["metadatas"][0][0] if results["metadatas"] else {}
        }
    
    def get_all_versions(self, chapter_id: str, version_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all versions for a chapter, optionally filtered by type."""
        where_clause = {"chapter_id": chapter_id}
        if version_type:
            where_clause["version_type"] = version_type
            
        results = self.versions_collection.query(
            query_texts=[""],  # Empty query to match all
            where=where_clause,
            n_results=100
        )
        
        versions = []
        for i in range(len(results["ids"][0]) if results["ids"] else 0):
            versions.append({
                "id": results["ids"][0][i],
                "content": results["documents"][0][i],
                "metadata": results["metadatas"][0][i] if results["metadatas"] else {}
            })
            
        return versions
    
    def get_all_chapters(self) -> List[Dict[str, Any]]:
        """Get all original chapters."""
        results = self.chapters_collection.query(
            query_texts=[""],  # Empty query to match all
            where={"type": "original"},
            n_results=100
        )
        
        chapters = []
        for i in range(len(results["ids"][0]) if results["ids"] else 0):
            chapters.append({
                "id": results["ids"][0][i],
                "content": results["documents"][0][i],
                "metadata": results["metadatas"][0][i] if results["metadatas"] else {}
            })
            
        return chapters
    
    def store_workflow_metadata(self, workflow_id: str, metadata: Dict[str, Any]) -> None:
        """Store metadata about a workflow run."""
        self.metadata_collection.upsert(
            ids=[workflow_id],
            documents=[json.dumps(metadata)],
            metadatas=[{"type": "workflow", "timestamp": datetime.now().isoformat()}]
        )
    
    def get_workflow_metadata(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get metadata about a workflow run."""
        results = self.metadata_collection.get(ids=[workflow_id])
        if not results["documents"]:
            return None
            
        return {
            "id": workflow_id,
            "data": json.loads(results["documents"][0]),
            "metadata": results["metadatas"][0] if results["metadatas"] else {}
        }
