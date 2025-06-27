# run_minimal.py
import os
os.environ["CHROMA_IGNORE_VERSION"] = "True"

from fastapi import FastAPI
import uvicorn
import logging

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("minimal_test")

# Create FastAPI app
app = FastAPI(title="Minimal Test App")

@app.get("/")
async def root():
    return {"message": "Hello from minimal test app"}

@app.get("/test-db")
async def test_db():
    try:
        # Only import here to avoid initialization errors
        from storage.version_manager import VersionManager
        vm = VersionManager()
        logger.info("Successfully created VersionManager")
        return {"status": "ok", "message": "Database connection successful"}
    except Exception as e:
        logger.error(f"Database error: {e}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    print("Starting minimal test app on port 9000...")
    print("Once started, access the app at: http://localhost:9000")
    uvicorn.run(app, host="0.0.0.0", port=9000, log_level="debug")
