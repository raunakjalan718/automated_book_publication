import chromadb
import os
import json
import hashlib
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import time

class VersionManager:
    """Content versioning system using ChromaDB."""
    
    def __init__(self, db_path: str = None):
        """
        Initialize the version manager with ChromaDB.
        
        Args:
            db_path: Path to the ChromaDB directory
        """
        # Get database path from environment if not provided
        if db_path is None:
            from dotenv import load_dotenv
            load_dotenv()
            db_path = os.getenv("CHROMA_DB_DIRECTORY", "./chroma_db")
        
        # Create directory if it doesn't exist
        os.makedirs(db_path, exist_ok=True)
        
        # Initialize ChromaDB
        try:
            self.db = chromadb.PersistentClient(path=db_path)
            
            # Create collections
            self.content_collection = self._get_or_create_collection("content_items")
            self.version_collection = self._get_or_create_collection("content_versions")
            self.metadata_collection = self._get_or_create_collection("project_metadata")
            
            print(f"Successfully initialized ChromaDB at {db_path}")
        except Exception as e:
            print(f"Error initializing ChromaDB: {str(e)}")
            raise
    
    def _get_or_create_collection(self, name: str):
        """Get a collection or create if it doesn't exist."""
        try:
            return self.db.get_collection(name=name)
        except:
            return self.db.create_collection(name=name)
            
    def _generate_content_fingerprint(self, content: str) -> str:
        """Generate a unique fingerprint for content."""
        # Create a unique hash for the content
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:12]
        timestamp = int(time.time())
        return f"content_{timestamp}_{content_hash}"
    
    def _generate_version_id(self, content_id: str, version_type: str) -> str:
        """Generate a version ID for a content item."""
        timestamp = int(time.time())
        return f"{content_id}_{version_type}_{timestamp}"
        
    def store_source_content(self, content_data: Dict[str, Any]) -> str:
        """
        Store source content with metadata.
        
        Args:
            content_data: Dictionary containing content and metadata
            
        Returns:
            ID of the stored content
        """
        # Extract content and generate ID
        content = content_data.get("content", "")
        content_id = self._generate_content_fingerprint(content)
        
        # Prepare metadata
        metadata = {
            "title": content_data.get("title", "Untitled"),
            "chapter_number": content_data.get("chapter_number"),
            "source_url": content_data.get("url", ""),
            "screenshot_path": content_data.get("screenshot_path", ""),
            "timestamp": datetime.now().isoformat(),
            "content_type": "source"
        }
        
        # Store in ChromaDB
        self.content_collection.upsert(
            ids=[content_id],
            documents=[content],
            metadatas=[metadata]
        )
        
        return content_id
    
    def store_content_version(self, 
                            content_id: str,
                            version_content: str,
                            version_type: str,
                            version_metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Store a version of content.
        
        Args:
            content_id: ID of the source content
            version_content: Content of this version
            version_type: Type of version (transform, review, etc.)
            version_metadata: Additional metadata for this version
            
        Returns:
            ID of the stored version
        """
        if version_metadata is None:
            version_metadata = {}
            
        # Generate version ID
        version_id = self._generate_version_id(content_id, version_type)
        
        # Get source content metadata
        source_results = self.content_collection.get(ids=[content_id])
        source_metadata = source_results["metadatas"][0] if source_results["metadatas"] else {}
        
        # Create combined metadata
        metadata = {
            "content_id": content_id,
            "version_type": version_type,
            "timestamp": datetime.now().isoformat(),
            "chapter_number": source_metadata.get("chapter_number"),
            "title": source_metadata.get("title"),
        }
        metadata.update(version_metadata)
        
        # Store the version
        self.version_collection.upsert(
            ids=[version_id],
            documents=[version_content],
            metadatas=[metadata]
        )
        
        return version_id
    
    def get_content(self, content_id: str) -> Dict[str, Any]:
        """Get content by ID."""
        results = self.content_collection.get(ids=[content_id])
        if not results["documents"]:
            return None
        
        return {
            "id": content_id,
            "content": results["documents"][0],
            "metadata": results["metadatas"][0] if results["metadatas"] else {}
        }
    
    def get_version(self, version_id: str) -> Dict[str, Any]:
        """Get a specific version."""
        results = self.version_collection.get(ids=[version_id])
        if not results["documents"]:
            return None
        
        return {
            "id": version_id,
            "content": results["documents"][0],
            "metadata": results["metadatas"][0] if results["metadatas"] else {}
        }
    
    def get_latest_version(self, content_id: str, version_type: str) -> Optional[Dict[str, Any]]:
        """Get the latest version of a specific type."""
        results = self.version_collection.query(
            query_texts=[version_type],
            where={"content_id": content_id, "version_type": version_type},
            n_results=1
        )
        
        if not results["documents"] or len(results["documents"][0]) == 0:
            return None
        
        return {
            "id": results["ids"][0][0],
            "content": results["documents"][0][0],
            "metadata": results["metadatas"][0][0]
        }
    
    def get_all_content(self, content_type: Optional[str] = "source") -> List[Dict[str, Any]]:
        """Get all content items of a specific type."""
        where_clause = {}
        if content_type:
            where_clause["content_type"] = content_type
            
        results = self.content_collection.query(
            query_texts=[""],  # Empty string matches everything
            where=where_clause,
            n_results=100  # Adjust as needed
        )
        
        content_items = []
        if not results["ids"]:
            return content_items
            
        for i in range(len(results["ids"][0])):
            content_items.append({
                "id": results["ids"][0][i],
                "content": results["documents"][0][i],
                "metadata": results["metadatas"][0][i]
            })
            
        return content_items
    
    def get_all_versions(self, content_id: str) -> List[Dict[str, Any]]:
        """Get all versions for a content item."""
        results = self.version_collection.query(
            query_texts=[""],  # Empty string matches everything
            where={"content_id": content_id},
            n_results=100  # Adjust as needed
        )
        
        versions = []
        if not results["ids"]:
            return versions
            
        for i in range(len(results["ids"][0])):
            versions.append({
                "id": results["ids"][0][i],
                "content": results["documents"][0][i],
                "metadata": results["metadatas"][0][i]
            })
            
        return versions
    
    def store_project_metadata(self, metadata_id: str, data: Dict[str, Any]) -> None:
        """Store project metadata."""
        self.metadata_collection.upsert(
            ids=[metadata_id],
            documents=[json.dumps(data)],
            metadatas=[{"timestamp": datetime.now().isoformat()}]
        )
    
    def get_project_metadata(self, metadata_id: str) -> Optional[Dict[str, Any]]:
        """Get project metadata."""
        results = self.metadata_collection.get(ids=[metadata_id])
        if not results["documents"]:
            return None
            
        return {
            "id": metadata_id,
            "data": json.loads(results["documents"][0]),
            "metadata": results["metadatas"][0] if results["metadatas"] else {}
        }
