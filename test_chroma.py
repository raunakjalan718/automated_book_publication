import os
os.environ["CHROMA_IGNORE_VERSION"] = "True"  # Add this to bypass version checks

import chromadb
import sqlite3

print(f"SQLite version: {sqlite3.sqlite_version}")

# Test connection
try:
    client = chromadb.PersistentClient(path="./chroma_db")
    print("ChromaDB client created successfully")
    
    # Create a test collection
    collection = client.get_or_create_collection(name="test_collection")
    print("Test collection created")
    
    # Add some data
    collection.add(
        documents=["This is a test document"],
        metadatas=[{"source": "test"}],
        ids=["test1"]
    )
    print("Data added successfully")
    
    # Query the data
    results = collection.query(query_texts=["test"], n_results=1)
    print(f"Query results: {results}")
    
    print("ChromaDB test completed successfully")
except Exception as e:
    print(f"ChromaDB test failed: {str(e)}")
