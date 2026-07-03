import os
from pathlib import Path
from dotenv import load_dotenv

# Load env variables from .env file
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# API Keys
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Models
# Default to gemini-2.0-flash-001 for speed and cost-efficiency
LLM_MODEL = os.getenv("LLM_MODEL", "google/gemini-2.5-flash")
# Default to gemini-embedding-2 for embeddings
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "models/gemini-embedding-2")

# Directories
STORAGE_DIR = os.getenv("STORAGE_DIR", str(BASE_DIR / "storage"))
UPLOAD_DIR = os.getenv("UPLOAD_DIR", str(BASE_DIR / "uploads"))

# Ensure directories exist
os.makedirs(STORAGE_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)
