import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Base URLs for scraping
WIKISOURCE_BASE_URL = "https://en.wikisource.org/wiki/The_Gates_of_Morning"
INITIAL_CHAPTER_URL = f"{WIKISOURCE_BASE_URL}/Book_1/Chapter_1"

# Output directories
SCREENSHOTS_DIR = "./screenshots"
CHROMA_DB_DIRECTORY = os.getenv("CHROMA_DB_DIRECTORY", "./chroma_db")

# Ensure necessary directories exist
for directory in [SCREENSHOTS_DIR, CHROMA_DB_DIRECTORY]:
    os.makedirs(directory, exist_ok=True)
