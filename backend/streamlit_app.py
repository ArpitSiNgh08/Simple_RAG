import os
import sys
import asyncio
import uuid
import streamlit as st
from pathlib import Path
from datetime import datetime

# Ensure the backend directory is in the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.rag import rag_manager, get_metadata
from app import config


# Page configuration with premium title and icon
st.set_page_config(
    page_title="DocuMind AI - PDF & Document RAG",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom premium styling
st.markdown("""
<style>
    /* Main container and background */
    .main {
        background-color: #0d1117;
        color: #c9d1d9;
    }
    
    /* Headings */
    h1, h2, h3 {
        font-family: 'Outfit', 'Inter', sans-serif;
        font-weight: 700;
        background: linear-gradient(45deg, #4f46e5, #06b6d4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    /* Styled cards for document list */
    .doc-card {
        background: rgba(22, 27, 34, 0.8);
        border: 1px solid rgba(48, 54, 61, 0.8);
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
        transition: all 0.3s ease;
    }
    .doc-card:hover {
        border-color: #4f46e5;
        box-shadow: 0 4px 12px rgba(79, 70, 229, 0.1);
        transform: translateY(-2px);
    }
    
    /* Citation container */
    .citation-box {
        background: rgba(30, 41, 59, 0.5);
        border-left: 4px solid #06b6d4;
        border-radius: 4px;
        padding: 10px 15px;
        margin-top: 8px;
        font-size: 0.9em;
    }
    
    /* Score badges */
    .badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.75em;
        font-weight: 600;
        margin-left: 8px;
    }
    .badge-high {
        background-color: rgba(16, 185, 129, 0.2);
        color: #10b981;
        border: 1px solid rgba(16, 185, 129, 0.3);
    }
    .badge-med {
        background-color: rgba(245, 158, 11, 0.2);
        color: #f59e0b;
        border: 1px solid rgba(245, 158, 11, 0.3);
    }
</style>
""", unsafe_allow_html=True)

# Helper function to run async methods synchronously in Streamlit
def run_async(coro):
    return asyncio.run(coro)

# State initialization
if "messages" not in st.session_state:
    st.session_state.messages = []

# Title Section
st.title("🧠 DocuMind AI")
st.markdown("##### Chat with your documents using advanced Retrieval-Augmented Generation (RAG)")

# Sidebar Configuration
with st.sidebar:
    st.image("https://img.icons8.com/isometric/512/brain.png", width=80)
    st.markdown("### ⚙️ System Control Panel")
    
    # Setup Status
    if rag_manager.initialized:
        st.success("🟢 RAG Engine Online")
    else:
        st.error("🔴 RAG Engine Offline")
        st.info("Please verify the GEMINI_API_KEY in the `.env` file.")
        
    st.markdown("---")
    
    # Model parameters
    st.markdown("### 🛠️ Model Parameters")
    similarity_threshold = st.slider(
        "Similarity Cutoff",
        min_value=0.0,
        max_value=1.0,
        value=0.4,
        step=0.05,
        help="Higher values return only highly relevant results, lower values allow broader matching."
    )
    
    top_k = st.slider(
        "Context Chunk Count (Top K)",
        min_value=1,
        max_value=10,
        value=5,
        step=1,
        help="Number of document chunks to retrieve and feed into the LLM context."
    )
    
    st.markdown("---")
    st.markdown("🤖 **LLM Model:** `" + config.LLM_MODEL + "`")
    st.markdown("🔮 **Embedding:** `" + config.EMBEDDING_MODEL + "`")

# Main Page Layout (Two Columns: Documents and Chat)
col_docs, col_chat = st.columns([1, 2], gap="large")

with col_docs:
    st.subheader("📁 Documents Manager")
    
    # File Uploader
    uploaded_files = st.file_uploader(
        "Upload PDF or DOCX documents",
        type=["pdf", "docx"],
        accept_multiple_files=True,
        key="uploader"
    )
    
    if uploaded_files:
        for file in uploaded_files:
            # Check if file has already been uploaded and indexed to prevent redundant work
            meta = get_metadata()
            already_indexed = any(info["filename"] == file.name for info in meta.values())
            
            if not already_indexed:
                with st.spinner(f"Indexing {file.name}..."):
                    try:
                        doc_id = str(uuid.uuid4())
                        stored_filename = f"{doc_id}_{file.name}"
                        file_path = Path(config.UPLOAD_DIR) / stored_filename
                        
                        # Save file
                        with open(file_path, "wb") as f:
                            f.write(file.getvalue())
                        
                        # Add to index
                        rag_manager.add_document(str(file_path), file.name, doc_id)
                        st.toast(f"✅ Successfully indexed {file.name}", icon="🎉")
                    except Exception as e:
                        st.error(f"Failed to process {file.name}: {str(e)}")
        
        # Clear uploader state to allow re-uploads
        st.rerun()

    # Document Registry List
    st.markdown("### 📚 Indexed Documents")
    meta = get_metadata()
    if not meta:
        st.info("No documents uploaded yet. Drag & drop files above to start indexing.")
    else:
        for doc_id, doc_info in list(meta.items()):
            # Beautiful card for each document with a delete button
            size_kb = round(doc_info["size_bytes"] / 1024, 1)
            uploaded_time = datetime.fromisoformat(doc_info["uploaded_at"]).strftime("%b %d, %H:%M")
            
            with st.container():
                st.markdown(
                    f"""
                    <div class="doc-card">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div style="font-weight: 600; font-size: 1.05em; color: #e6edf3; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 80%;">
                                📄 {doc_info['filename']}
                            </div>
                        </div>
                        <div style="font-size: 0.85em; color: #8b949e; margin-top: 6px;">
                            <span>💾 {size_kb} KB</span> &nbsp;|&nbsp; 
                            <span>📖 {doc_info.get('pages', 'N/A')} pages</span> &nbsp;|&nbsp;
                            <span>📅 {uploaded_time}</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                # Small separate delete button just under card to keep it clean and interactive
                if st.button(f"🗑️ Delete Document", key=f"del_{doc_id}", use_container_width=True):
                    with st.spinner(f"Deleting {doc_info['filename']}..."):
                        try:
                            rag_manager.delete_document(doc_id)
                            st.toast(f"Deleted {doc_info['filename']}", icon="🗑️")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to delete: {e}")

with col_chat:
    st.subheader("💬 Chat Assistant")
    
    # Reset chat button
    if st.button("🧹 Clear Chat History", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
        
    st.markdown("---")

    # Render previous messages
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            # Display citations if available
            if "citations" in msg and msg["citations"]:
                with st.expander("🔍 Citations & Sources", expanded=False):
                    for cit in msg["citations"]:
                        score = cit.get("similarity_score", 0.0)
                        badge_class = "badge-high" if score >= 0.6 else "badge-med"
                        badge_html = f'<span class="badge {badge_class}">Match: {score:.2f}</span>'
                        page_str = f"Page {cit['page_label']}" if cit.get("page_label") else "Document details"
                        
                        st.markdown(
                            f"""
                            <div class="citation-box">
                                <strong>[{cit['citation_number']}] {cit['file_name']}</strong> ({page_str}) {badge_html}
                                <div style="margin-top: 5px; font-style: italic; color: #8b949e; line-height: 1.4;">
                                    "{cit['text_snippet']}"
                                </div>
                            </div>
                            """, 
                            unsafe_allow_html=True
                        )

    # Chat Input
    if query_text := st.chat_input("Ask a question about the uploaded documents..."):
        if not rag_manager.initialized:
            st.error("RAG Engine is not initialized. Please verify your Gemini API key.")
        else:
            # Append and display user message
            st.session_state.messages.append({"role": "user", "content": query_text})
            with st.chat_message("user"):
                st.markdown(query_text)
                
            # Query the RAG engine and get response
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                with st.spinner("Analyzing documents & generating answer..."):
                    try:
                        # Call query async
                        res = run_async(
                            rag_manager.aquery(
                                query_text=query_text,
                                similarity_threshold=similarity_threshold,
                                top_k=top_k
                            )
                        )
                        
                        answer = res.get("answer", "No answer could be generated.")
                        citations = res.get("citations", [])
                        
                        # Display answer
                        message_placeholder.markdown(answer)
                        
                        # Display citations if any
                        if citations:
                            with st.expander("🔍 Citations & Sources", expanded=False):
                                for cit in citations:
                                    score = cit.get("similarity_score", 0.0)
                                    badge_class = "badge-high" if score >= 0.6 else "badge-med"
                                    badge_html = f'<span class="badge {badge_class}">Match: {score:.2f}</span>'
                                    page_str = f"Page {cit['page_label']}" if cit.get("page_label") else "Document details"
                                    
                                    st.markdown(
                                        f"""
                                        <div class="citation-box">
                                            <strong>[{cit['citation_number']}] {cit['file_name']}</strong> ({page_str}) {badge_html}
                                            <div style="margin-top: 5px; font-style: italic; color: #8b949e; line-height: 1.4;">
                                                "{cit['text_snippet']}"
                                            </div>
                                        </div>
                                        """, 
                                        unsafe_allow_html=True
                                    )
                                    
                        # Store in history
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": answer,
                            "citations": citations
                        })
                    except Exception as e:
                        st.error(f"Error querying: {str(e)}")
