import React, { useState, useEffect, useRef } from "react";
import "./App.css";

const API_BASE = "http://localhost:8000/api";

function App() {
  const [initialized, setInitialized] = useState(false);
  const [hasApiKey, setHasApiKey] = useState(false);
  const [apiKeyInput, setApiKeyInput] = useState("");
  const [showApiKeyModal, setShowApiKeyModal] = useState(false);
  const [isSavingKey, setIsSavingKey] = useState(false);

  const [documents, setDocuments] = useState([]);
  const [isUploading, setIsUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [uploadError, setUploadError] = useState("");

  const [messages, setMessages] = useState([]);
  const [queryInput, setQueryInput] = useState("");
  const [isQuerying, setIsQuerying] = useState(false);
  const [activeCitationIndex, setActiveCitationIndex] = useState({}); // map of msgIndex -> citationNum
  const [similarityThreshold, setSimilarityThreshold] = useState(0.4);

  const fileInputRef = useRef(null);
  const messagesEndRef = useRef(null);

  // Check initialization status on load
  useEffect(() => {
    fetchStatus();
    fetchDocuments();
  }, []);

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isQuerying]);

  const fetchStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/status`);
      const data = await res.json();
      setInitialized(data.initialized);
      setHasApiKey(data.has_api_key);
      if (!data.has_api_key) {
        setShowApiKeyModal(true);
      }
    } catch (err) {
      console.error("Error checking backend status", err);
    }
  };

  const fetchDocuments = async () => {
    try {
      const res = await fetch(`${API_BASE}/documents`);
      const data = await res.json();
      setDocuments(data);
    } catch (err) {
      console.error("Error fetching documents list", err);
    }
  };

  const handleSaveApiKey = async (e) => {
    e.preventDefault();
    if (!apiKeyInput.trim()) return;

    setIsSavingKey(true);
    try {
      const res = await fetch(`${API_BASE}/settings`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ api_key: apiKeyInput }),
      });
      const data = await res.json();
      if (res.ok && data.status === "success") {
        setInitialized(data.initialized);
        setHasApiKey(true);
        setShowApiKeyModal(false);
        setApiKeyInput("");
      } else {
        alert(data.detail || "Failed to set API Key.");
      }
    } catch (err) {
      alert("Error contacting API: " + err.message);
    } finally {
      setIsSavingKey(false);
    }
  };

  // Upload handlers
  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    setUploadError("");

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      uploadFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e) => {
    setUploadError("");
    if (e.target.files && e.target.files[0]) {
      uploadFile(e.target.files[0]);
    }
  };

  const uploadFile = async (file) => {
    const ext = file.name.split(".").pop().toLowerCase();
    if (ext !== "pdf" && ext !== "docx") {
      setUploadError("Only PDF and DOCX files are supported.");
      return;
    }

    setIsUploading(true);
    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(`${API_BASE}/upload`, {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      if (res.ok && data.status === "success") {
        await fetchDocuments();
        setDocuments((prev) => {
          // Double check updates
          if (!prev.find((d) => d.id === data.document.id)) {
            return [...prev, data.document];
          }
          return prev;
        });
      } else {
        setUploadError(data.detail || "Failed to parse document.");
      }
    } catch (err) {
      setUploadError("Error uploading file: " + err.message);
    } finally {
      setIsUploading(false);
    }
  };

  const handleDeleteDoc = async (docId, e) => {
    e.stopPropagation();
    if (!confirm("Are you sure you want to delete this document?")) return;

    try {
      const res = await fetch(`${API_BASE}/documents/${docId}`, {
        method: "DELETE",
      });
      if (res.ok) {
        setDocuments((prev) => prev.filter((d) => d.id !== docId));
      } else {
        const data = await res.json();
        alert(data.detail || "Failed to delete document.");
      }
    } catch (err) {
      alert("Error deleting document: " + err.message);
    }
  };

  // Query handlers
  const handleQuery = async (e) => {
    e.preventDefault();
    if (!queryInput.trim() || isQuerying) return;

    const userMessage = { role: "user", content: queryInput };
    setMessages((prev) => [...prev, userMessage]);
    const currentQuery = queryInput;
    setQueryInput("");
    setIsQuerying(true);

    try {
      const res = await fetch(`${API_BASE}/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: currentQuery,
          similarity_threshold: similarityThreshold,
          top_k: 5,
        }),
      });
      const data = await res.json();
      if (res.ok) {
        const assistantMessage = {
          role: "assistant",
          content: data.answer,
          citations: data.citations || [],
        };
        setMessages((prev) => [...prev, assistantMessage]);
      } else {
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: `Error: ${data.detail || "Failed to process query."}`,
            isError: true,
          },
        ]);
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `Error contacting backend: ${err.message}`,
          isError: true,
        },
      ]);
    } finally {
      setIsQuerying(false);
    }
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  // Function to render text and make citations interactive
  const renderMessageContent = (msg, msgIdx) => {
    if (msg.role !== "assistant" || !msg.citations || msg.citations.length === 0) {
      return msg.content;
    }

    const citationRegex = /\[(\d+)\]/g;
    const parts = [];
    let lastIndex = 0;
    let match;

    while ((match = citationRegex.exec(msg.content)) !== null) {
      const textPart = msg.content.substring(lastIndex, match.index);
      if (textPart) {
        parts.push(textPart);
      }

      const citNumber = parseInt(match[1], 10);
      const citationExists = msg.citations.some((c) => c.citation_number === citNumber);

      if (citationExists) {
        parts.push(
          <span
            key={`cit-${match.index}`}
            className={`citation-tag ${
              activeCitationIndex[msgIdx] === citNumber ? "active" : ""
            }`}
            onClick={() => {
              setActiveCitationIndex((prev) => ({
                ...prev,
                [msgIdx]: prev[msgIdx] === citNumber ? null : citNumber,
              }));
            }}
          >
            {citNumber}
          </span>
        );
      } else {
        parts.push(match[0]); // keep the text version if not matching backend citations
      }

      lastIndex = citationRegex.lastIndex;
    }

    const remainingText = msg.content.substring(lastIndex);
    if (remainingText) {
      parts.push(remainingText);
    }

    return (
      <div>
        <div className="text-body">{parts.length > 0 ? parts : msg.content}</div>
        
        {/* Citations List Panel */}
        <div className="citations-panel">
          <div className="citations-header">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z"/>
              <path d="M12 16v-4"/>
              <path d="M12 8h.01"/>
            </svg>
            Sources & Citations:
          </div>
          <div className="citations-list">
            {msg.citations.map((c) => (
              <button
                key={`trigger-${c.citation_number}`}
                className={`citation-card-trigger ${
                  activeCitationIndex[msgIdx] === c.citation_number ? "active" : ""
                }`}
                onClick={() => {
                  setActiveCitationIndex((prev) => ({
                    ...prev,
                    [msgIdx]: prev[msgIdx] === c.citation_number ? null : c.citation_number,
                  }));
                }}
              >
                <span>[{c.citation_number}]</span>
                <span style={{ maxWidth: "120px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {c.file_name}
                </span>
                {c.page_label && <span>(p. {c.page_label})</span>}
                <span className="citation-score">{(c.similarity_score * 100).toFixed(0)}% Match</span>
              </button>
            ))}
          </div>

          {/* Active Citation Detail */}
          {activeCitationIndex[msgIdx] && (
            (() => {
              const activeCit = msg.citations.find(
                (c) => c.citation_number === activeCitationIndex[msgIdx]
              );
              if (!activeCit) return null;
              return (
                <div className="citation-detail-box">
                  <div className="citation-detail-meta">
                    <span>Source [{activeCit.citation_number}]: {activeCit.file_name} {activeCit.page_label ? `(Page ${activeCit.page_label})` : ""}</span>
                    <span className="citation-score">{(activeCit.similarity_score * 100).toFixed(1)}% relevance</span>
                  </div>
                  <div className="citation-detail-text">
                    "{activeCit.text_snippet}"
                  </div>
                </div>
              );
            })()
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="app-container">
      {/* Sidebar */}
      <div className="sidebar">
        <div className="sidebar-header">
          <div className="logo-icon">SR</div>
          <div className="logo-text">Simple RAG</div>
        </div>

        <div className="sidebar-content">
          {/* File Upload Section */}
          <div>
            <div className="section-title">Upload Documents</div>
            <div
              className={`upload-container ${dragActive ? "drag-active" : ""}`}
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current.click()}
            >
              <input
                ref={fileInputRef}
                type="file"
                className="file-input"
                accept=".pdf,.docx"
                onChange={handleFileChange}
              />
              <div className="upload-icon">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                  <polyline points="17 8 12 3 7 8" />
                  <line x1="12" y1="3" x2="12" y2="15" />
                </svg>
              </div>
              <div className="upload-text">
                {isUploading ? "Uploading..." : "Click or drag files here"}
              </div>
              <div className="upload-subtext">PDF, DOCX up to 10MB</div>
            </div>
            {uploadError && <div className="error-message" style={{ marginTop: "0.5rem" }}>{uploadError}</div>}
          </div>

          {/* Documents Registry Section */}
          <div style={{ flex: 1, display: "flex", flexDirection: "column", minHeight: 0 }}>
            <div className="section-title">Indexed Documents ({documents.length})</div>
            <div className="document-list" style={{ overflowY: "auto", flex: 1 }}>
              {documents.length === 0 ? (
                <div style={{ textAlign: "center", color: "var(--text-muted)", fontSize: "0.875rem", padding: "1rem" }}>
                  No files indexed. Upload a file above.
                </div>
              ) : (
                documents.map((doc) => (
                  <div key={doc.id} className="document-item">
                    <div className="doc-info">
                      <div className="doc-icon">
                        {doc.filename.endsWith(".pdf") ? (
                          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                            <polyline points="14 2 14 8 20 8"/>
                            <line x1="16" y1="13" x2="8" y2="13"/>
                            <line x1="16" y1="17" x2="8" y2="17"/>
                            <polyline points="10 9 9 9 8 9"/>
                          </svg>
                        ) : (
                          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                            <polyline points="14 2 14 8 20 8"/>
                            <path d="M8 13h8M8 17h8"/>
                          </svg>
                        )}
                      </div>
                      <div className="doc-meta">
                        <div className="doc-name" title={doc.filename}>{doc.filename}</div>
                        <div className="doc-details">
                          {doc.pages ? `${doc.pages} pgs` : "1 pg"} • {formatFileSize(doc.size_bytes)}
                        </div>
                      </div>
                    </div>
                    <button className="btn-delete" onClick={(e) => handleDeleteDoc(doc.id, e)} title="Delete document">
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <polyline points="3 6 5 6 21 6" />
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                        <line x1="10" y1="11" x2="10" y2="17" />
                        <line x1="14" y1="11" x2="14" y2="17" />
                      </svg>
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Main Area */}
      <div className="main-chat">
        {/* Header */}
        <div className="chat-header">
          <div className="chat-header-info">
            <h2>Document Conversation</h2>
            <p>{documents.length > 0 ? `Querying across ${documents.length} sources` : "No sources available"}</p>
          </div>
          <div className="header-actions">
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.8rem", color: "var(--text-secondary)" }}>
              <span>Confidence Cutoff:</span>
              <input
                type="range"
                min="0.1"
                max="0.8"
                step="0.05"
                value={similarityThreshold}
                onChange={(e) => setSimilarityThreshold(parseFloat(e.target.value))}
                style={{ width: "80px", accentColor: "var(--accent-color)" }}
              />
              <span>{Math.round(similarityThreshold * 100)}%</span>
            </div>
            <button className="btn-icon" onClick={() => setShowApiKeyModal(true)} title="Settings">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="3"/>
                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
              </svg>
            </button>
          </div>
        </div>

        {/* Message List */}
        <div className="messages-container">
          {messages.length === 0 ? (
            <div className="welcome-screen">
              <div className="welcome-logo">🤖</div>
              <h1>AI Document Q&A Partner</h1>
              <p>
                Upload your research papers, contracts, technical specifications, or documents, and ask complex questions. Get factual answers mapped directly to sources.
              </p>
              <div className="features-grid">
                <div className="feature-card">
                  <h3>Precise Citation System</h3>
                  <p>Answers refer directly to source texts with exact matches and page numbers.</p>
                </div>
                <div className="feature-card">
                  <h3>Dual-Format Parsing</h3>
                  <p>Supports Word (.docx) and PDF uploads using optimized parsers.</p>
                </div>
              </div>
            </div>
          ) : (
            messages.map((msg, idx) => (
              <div key={idx} className={`message-bubble ${msg.role}`}>
                <div className="avatar">
                  {msg.role === "user" ? "U" : "AI"}
                </div>
                <div className="message-content">
                  {renderMessageContent(msg, idx)}
                </div>
              </div>
            ))
          )}
          {isQuerying && (
            <div className="message-bubble assistant">
              <div className="avatar">AI</div>
              <div className="message-content">
                <div className="loading-indicator">
                  <div className="spinner-accent"></div>
                  <span>Synthesizing answer from context...</span>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Chat Input */}
        <div className="chat-input-container">
          <form className="chat-input-form" onSubmit={handleQuery}>
            <input
              type="text"
              className="chat-input"
              placeholder={documents.length > 0 ? "Ask a question about your documents..." : "Please upload a document to begin..."}
              value={queryInput}
              onChange={(e) => setQueryInput(e.target.value)}
              disabled={documents.length === 0 || isQuerying}
            />
            <button className="btn-send" type="submit" disabled={documents.length === 0 || !queryInput.trim() || isQuerying}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <line x1="22" y1="2" x2="11" y2="13"/>
                <polygon points="22 2 15 22 11 13 2 9 22 2"/>
              </svg>
            </button>
          </form>
        </div>
      </div>

      {/* Settings Modal */}
      {showApiKeyModal && (
        <div className="modal-overlay">
          <div className="modal-card">
            <h2>Welcome to Simple RAG</h2>
            <p>To power embeddings and text generation, paste your Google Gemini API Key. This will be stored locally in a .env file.</p>
            <form onSubmit={handleSaveApiKey}>
              <div className="form-group">
                <label>Gemini API Key</label>
                <input
                  type="password"
                  className="form-input"
                  placeholder="AIzaSy..."
                  value={apiKeyInput}
                  onChange={(e) => setApiKeyInput(e.target.value)}
                  required
                />
              </div>
              <button className="btn-primary" type="submit" disabled={isSavingKey || !apiKeyInput.trim()}>
                {isSavingKey ? (
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "0.5rem" }}>
                    <div className="spinner"></div>
                    <span>Initializing Engine...</span>
                  </div>
                ) : (
                  "Save and Continue"
                )}
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
