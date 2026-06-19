import os
import json
import logging
from typing import List, Dict, Any, Tuple
from datetime import datetime
from pathlib import Path

from llama_index.core import (
    VectorStoreIndex,
    SimpleDirectoryReader,
    StorageContext,
    load_index_from_storage,
    Settings,
)
from llama_index.core.prompts import PromptTemplate
from llama_index.llms.google_genai import GoogleGenAI
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
from llama_index.core.postprocessor import SimilarityPostprocessor

from app import config

logger = logging.getLogger(__name__)

# Metadata registry file path
META_FILE_PATH = Path(config.STORAGE_DIR) / "documents_meta.json"

def get_metadata() -> Dict[str, Any]:
    """Load documents metadata registry."""
    if not META_FILE_PATH.exists():
        return {}
    try:
        with open(META_FILE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error reading metadata file: {e}")
        return {}

def save_metadata(meta: Dict[str, Any]):
    """Save documents metadata registry."""
    try:
        with open(META_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error writing metadata file: {e}")

class RAGManager:
    def __init__(self):
        self.index = None
        self.initialized = False
        self.api_key = config.GEMINI_API_KEY
        self.initialize_models()

    def initialize_models(self, api_key: str = None):
        """Initialize LLM and Embedding models with the provided API key."""
        is_startup = api_key is None
        if api_key:
            self.api_key = api_key
        
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            logger.warning("No valid Gemini API key provided. RAG Manager will require setup.")
            self.initialized = False
            return

        try:
            # Configure LlamaIndex to use Gemini LLM and Embeddings
            Settings.llm = GoogleGenAI(
                model=config.LLM_MODEL, 
                api_key=self.api_key,
                temperature=0.2
            )
            Settings.embed_model = GoogleGenAIEmbedding(
                model_name=config.EMBEDDING_MODEL, 
                api_key=self.api_key,
                embed_batch_size=16
            )
            
            # Load or create Vector Store Index
            self._load_or_create_index()
            self.initialized = True
        except Exception as e:
            logger.error(f"Failed to initialize models or index: {e}")
            self.initialized = False
            if not is_startup:
                # If explicitly set by user, raise the error to show in the UI
                raise e

    def _load_or_create_index(self):
        """Load the index from storage, or create a new empty one if it doesn't exist."""
        if os.path.exists(os.path.join(config.STORAGE_DIR, "docstore.json")):
            logger.info("Loading existing index from storage...")
            storage_context = StorageContext.from_defaults(persist_dir=config.STORAGE_DIR)
            self.index = load_index_from_storage(storage_context)
        else:
            logger.info("Creating a new vector index...")
            # Initialize with an empty index
            self.index = VectorStoreIndex([])
            self.index.storage_context.persist(persist_dir=config.STORAGE_DIR)

    def add_document(self, file_path: str, filename: str, doc_id: str) -> Dict[str, Any]:
        """Parse a document and insert it into the Vector Store Index."""
        if not self.initialized:
            raise ValueError("RAG Engine is not initialized. Please set a valid Gemini API Key.")

        # Read the document using SimpleDirectoryReader
        reader = SimpleDirectoryReader(input_files=[file_path])
        documents = reader.load_data()

        if not documents:
            raise ValueError("Could not extract any content from the document.")

        # Associate all loaded pages/chunks with the same document metadata and doc_id
        for doc in documents:
            doc.doc_id = doc_id
            doc.metadata["file_name"] = filename
            doc.metadata["doc_id"] = doc_id
            # Keep track of page label for PDFs
            if "page_label" in doc.metadata:
                doc.metadata["page_label"] = doc.metadata["page_label"]

        # Parse documents into nodes using a node parser to control batching
        from llama_index.core.node_parser import SimpleNodeParser
        parser = SimpleNodeParser.from_defaults(chunk_size=512, chunk_overlap=64)
        nodes = parser.get_nodes_from_documents(documents)

        # Insert nodes in a single batch call to leverage embed_batch_size rate limiting
        self.index.insert_nodes(nodes)
            
        self.index.storage_context.persist(persist_dir=config.STORAGE_DIR)

        # Update metadata registry
        meta = get_metadata()
        file_stats = os.stat(file_path)
        meta[doc_id] = {
            "id": doc_id,
            "filename": filename,
            "size_bytes": file_stats.st_size,
            "uploaded_at": datetime.now().isoformat(),
            "pages": len(documents),
        }
        save_metadata(meta)
        
        return meta[doc_id]

    def delete_document(self, doc_id: str):
        """Delete a document from the index and metadata registry."""
        if not self.initialized:
            raise ValueError("RAG Engine is not initialized.")

        # Check if exists in metadata
        meta = get_metadata()
        if doc_id not in meta:
            raise ValueError(f"Document with ID {doc_id} not found.")

        # Delete from index
        try:
            self.index.delete_ref_doc(doc_id, delete_from_docstore=True)
            self.index.storage_context.persist(persist_dir=config.STORAGE_DIR)
        except Exception as e:
            logger.error(f"Error deleting from vector index: {e}")
            # Continue to cleanup files and metadata even if index deletion has issues

        # Delete physical file if it exists
        meta_info = meta[doc_id]
        filename = meta_info["filename"]
        file_path = Path(config.UPLOAD_DIR) / f"{doc_id}_{filename}"
        if file_path.exists():
            try:
                os.remove(file_path)
            except Exception as e:
                logger.error(f"Error deleting physical file: {e}")

        # Update metadata file
        del meta[doc_id]
        save_metadata(meta)

    async def aquery(self, query_text: str, similarity_threshold: float = 0.5, top_k: int = 5) -> Dict[str, Any]:
        """Query the index and return the answer along with source citations."""
        if not self.initialized:
            return {
                "answer": "RAG Engine is not initialized. Please set a valid Gemini API Key in the settings.",
                "citations": []
            }

        # Check if there are any documents indexed
        meta = get_metadata()
        if not meta:
            return {
                "answer": "No documents uploaded yet. Please upload a PDF or DOCX file to get started.",
                "citations": []
            }

        # Create query engine
        # We'll use a postprocessor to filter nodes with low similarity scores
        query_engine = self.index.as_query_engine(
            similarity_top_k=top_k,
            node_postprocessors=[SimilarityPostprocessor(similarity_cutoff=similarity_threshold)]
        )

        # Set custom system prompt to guide the LLM to cite correctly
        custom_prompt = (
            "You are a highly precise Q&A assistant. Your task is to answer the query based ONLY on the provided context.\n"
            "For every claim or piece of information in your answer, you MUST cite the source by using the citation number, e.g. [1], [2], etc., corresponding to the source context provided.\n"
            "If multiple sources support a claim, list them all, e.g. [1][3].\n"
            "Ensure your citations are accurate and directly reference the provided context.\n"
            "If the context does not contain the answer, politely state that you cannot answer based on the provided documents.\n\n"
            "Context Information:\n"
            "---------------------\n"
            "{context_str}\n"
            "---------------------\n"
            "Query: {query_str}\n"
            "Answer: "
        )
        query_engine.update_prompts(
            {"response_synthesizer:text_qa_template": PromptTemplate(custom_prompt)}
        )

        # Execute query
        response = await query_engine.aquery(query_text)

        # Format citations
        citations = []
        for idx, source_node in enumerate(response.source_nodes, 1):
            node_meta = source_node.node.metadata
            citation_info = {
                "citation_number": idx,
                "file_name": node_meta.get("file_name", "Unknown Document"),
                "doc_id": node_meta.get("doc_id", ""),
                "page_label": node_meta.get("page_label", None),
                "text_snippet": source_node.node.get_content(),
                "similarity_score": float(source_node.score) if source_node.score is not None else 0.0
            }
            citations.append(citation_info)

        return {
            "answer": response.response,
            "citations": citations
        }

# Global instance of RAGManager
rag_manager = RAGManager()
