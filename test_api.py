# test_api.py
from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}

if __name__ == "__main__":
    print("Starting test FastAPI app...")
    uvicorn.run(app, host="0.0.0.0", port=8080)
