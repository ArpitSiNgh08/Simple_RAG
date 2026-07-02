import os
import uuid
import logging
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional

from app.config import UPLOAD_DIR
from app.rag import rag_manager, get_metadata

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Simple RAG API",
    description="Backend API for Document Q&A with Citations",
    version="1.0.0"
)

# CORS middleware config to allow separate frontend during dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    query: str
    similarity_threshold: Optional[float] = 0.4
    top_k: Optional[int] = 5

class SettingsRequest(BaseModel):
    api_key: str

@app.get("/api/status")
async def get_status():
    """Check if OpenRouter API Key is configured and the system is initialized."""
    return {
        "initialized": rag_manager.initialized,
        "has_api_key": bool(rag_manager.api_key),
    }

@app.post("/api/settings")
async def save_settings(payload: SettingsRequest):
    """Set the API key dynamically and re-initialize RAG engine."""
    api_key = payload.api_key.strip()
    if not api_key:
        raise HTTPException(status_code=400, detail="API key cannot be empty")
    
    try:
        rag_manager.initialize_models(api_key=api_key)
        
        # Save API key to .env file for persistence across restarts
        from dotenv import set_key
        env_path = Path(__file__).resolve().parent.parent / ".env"
        set_key(str(env_path), "OPENROUTER_API_KEY", api_key)
            
        return {"status": "success", "initialized": rag_manager.initialized}
    except Exception as e:
        logger.error(f"Error configuring API Key: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to initialize models with provided key: {str(e)}")

@app.get("/api/documents")
async def list_documents():
    """List all uploaded documents."""
    meta = get_metadata()
    return list(meta.values())

@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload PDF or DOCX document and index it."""
    if not rag_manager.initialized:
        raise HTTPException(
            status_code=400, 
            detail="RAG Engine not initialized. Please configure a valid OpenRouter API Key first."
        )

    filename = file.filename
    ext = Path(filename).suffix.lower()
    
    if ext not in [".pdf", ".docx"]:
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files are supported.")

    doc_id = str(uuid.uuid4())
    stored_filename = f"{doc_id}_{filename}"
    file_path = Path(UPLOAD_DIR) / stored_filename

    try:
        # Save file to uploads folder
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
            
        # Index document in RAG engine
        doc_info = rag_manager.add_document(str(file_path), filename, doc_id)
        return {"status": "success", "document": doc_info}
    except Exception as e:
        logger.error(f"Error indexing document {filename}: {e}")
        # Clean up file if it exists and failed to index
        if file_path.exists():
            try:
                os.remove(file_path)
            except Exception:
                pass
        raise HTTPException(status_code=500, detail=f"Failed to process document: {str(e)}")

@app.delete("/api/documents/{doc_id}")
async def delete_document(doc_id: str):
    """Delete a document and clean it up from index and storage."""
    if not rag_manager.initialized:
        raise HTTPException(status_code=400, detail="RAG Engine not initialized.")

    try:
        rag_manager.delete_document(doc_id)
        return {"status": "success", "message": "Document deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting document {doc_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")

@app.post("/api/query")
async def query_documents(payload: QueryRequest):
    """Query the RAG engine."""
    if not rag_manager.initialized:
        raise HTTPException(
            status_code=400, 
            detail="RAG Engine not initialized. Please configure an OpenRouter API Key."
        )

    try:
        result = await rag_manager.aquery(
            query_text=payload.query,
            similarity_threshold=payload.similarity_threshold,
            top_k=payload.top_k
        )
        return result
    except Exception as e:
        logger.error(f"Error querying: {e}")
        raise HTTPException(status_code=500, detail=f"Error querying documents: {str(e)}")

# Mount static files directory if it exists
static_dir = Path(__file__).resolve().parent.parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
