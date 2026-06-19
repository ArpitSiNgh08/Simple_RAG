# Simple RAG: Document Q&A with Citations

A high-performance, premium web application that allows users to upload documents (PDF and DOCX), ask natural-language questions, and get precise answers with verified source citations.

Built with **FastAPI**, **React + Vite**, and **LlamaIndex** using **Google Gemini**.

---

## 🚀 How to Run

To run the entire application (both frontend and backend) with a single command:

1. Make sure you have **Node.js** and **Python 3.12+ (standard MSVC build)** installed.
2. In your terminal, run:
   ```bash
   python run.py
   ```
   *The launcher script will automatically create a virtual environment, install backend and frontend dependencies, compile the production frontend assets, and launch the backend server on `http://localhost:8000`.*
3. Open `http://localhost:8000` in your browser.
4. Paste your **Gemini API Key** in the settings modal to initialize the engine.

---

## 🛠️ Architecture Decisions & Alternatives

### 1. Vector Database: SimpleVectorStore (LlamaIndex)
- **Decision**: Used LlamaIndex's built-in disk-persisted `SimpleVectorStore`.
- **Reasoning**: It stores vector index matrices in lightweight JSON files on disk under the `backend/storage` directory. This requires **zero external services** (no Docker, no cloud DB subscription, no separate DB process), making local execution and evaluation seamless and extremely reliable.
- **Alternatives Considered**: 
  - *Chroma / Qdrant*: Excellent, but would require running a separate local database service or Docker container, which increases setup complexity for simple local runs.
  - *Pinecone*: Fully managed cloud service, but requires internet dependency, API key setup, and introduces network latency.

### 2. LLM & Embeddings: Google Gemini (gemini-1.5-flash & text-embedding-004)
- **Decision**: Integrated `gemini-1.5-flash` for generation and `text-embedding-004` for vector embeddings.
- **Reasoning**: Flash provides near-instantaneous response times, low latency, and is highly cost-effective while offering a large context window and strong reasoning.
- **Alternatives Considered**: 
  - *OpenAI GPT-4o-mini*: Comparable performance, but since this project runs inside the Google Gemini agent ecosystem, using Gemini provides native compatibility and keeps configurations clean.

### 3. Frontend/Backend Integration: Single-Server Deployment
- **Decision**: The Vite production bundle compiles directly into `backend/static/`, and FastAPI serves it as static files.
- **Reasoning**: Serves the entire application on a single port (`8000`), completely bypassing CORS issues, securing session calls, and simplifying deployment.

### 4. Citation Strategy
- **Decision**: Custom prompt-engineered retrieval synthesis mapping back to the retrieved source node metadata.
- **Reasoning**: By injecting explicit formatting rules in the LLM's system prompt (e.g., `"cite the source by using [1], [2], ..."`), we ensure the LLM outputs clear citation numbers. The frontend parses these tags and connects them to the metadata (file name, page label, snippet, similarity score) of the source nodes, making citations interactive and verifiable.

---

## ⚠️ Known Gaps & Future Improvements

1. **Document Page Navigation**: While the UI shows the page number where the answer was found, it doesn't display the PDF page visually. Integrating a PDF viewer that highlights matching sections would be the next step.
2. **Table Parsing**: Standard text extraction (`docx2txt` / `pypdf`) strips tables of structure. Using a parser like `LlamaParse` or `unstructured` would improve accuracy on financial reports.
3. **Hybrid Search**: Currently uses purely dense vector embeddings. Adding sparse BM25 retrieval (hybrid search) would improve accuracy for keyword-heavy queries.
4. **Security**: Storing the API Key in plain text in `.env` is suitable for local development but must be replaced by secret manager integrations in production.
