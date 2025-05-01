# ARIA HR Assistant - RAG Chatbot Implementation

This document outlines the implementation details for the backend RAG (Retrieval-Augmented Generation) chatbot that powers the ARIA HR and organizational assistant.

## Architecture Overview

The ARIA HR Assistant uses a RAG architecture to provide accurate responses based on uploaded documents. The system consists of:

1. **Front-end UI**: A Next.js application with a chat interface
2. **API Endpoints**: Next.js API routes for chat and document management
3. **RAG Backend**: A Python backend that processes documents and answers queries
4. **Document Storage**: A system to store and retrieve uploaded PDFs
5. **Vector Database**: For storing document embeddings and enabling semantic search

## Implementation Details

### Document Processing Pipeline

Based on the [rag-chatbot](https://github.com/umbertogriffo/rag-chatbot) repository, our implementation will:

1. **Document Ingestion**:
   - Extract text from uploaded PDF documents using PyPDF2 or PDFMiner
   - Split text into smaller chunks (paragraphs or semantically meaningful sections)
   - Clean and preprocess text to remove irrelevant content

2. **Embedding Generation**:
   - Generate embeddings for each text chunk using a language model (e.g., BERT or Sentence Transformers)
   - Store embeddings in a vector database like FAISS, Pinecone, or Chroma
   - Index documents with metadata for efficient retrieval

3. **Retrieval System**:
   - Implement semantic search to find relevant document chunks
   - Use techniques like Maximal Marginal Relevance (MMR) to ensure diverse results
   - Rank retrieved passages by relevance to the query

### LLM Integration

Based on the [smartchat](https://github.com/linghong/smartchat) repository:

1. **Query Processing**:
   - Parse and understand user queries
   - Generate embeddings for user queries
   - Retrieve relevant document chunks using vector similarity search

2. **Response Generation**:
   - Use Gemini 2.0-flash as the Language Model
   - Construct a prompt that includes:
     - System instructions for HR assistant behavior
     - Retrieved document context
     - Conversation history
     - Current user query
   - Generate a response that faithfully represents the document content

3. **Conversational Context Management**:
   - Maintain conversation history
   - Use previous context to improve response relevance
   - Implement a sliding window approach for long conversations

## Backend Implementation Plan

### 1. Set up Python Backend

```bash
# Create a new directory for the backend
mkdir aria-rag-backend
cd aria-rag-backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install fastapi uvicorn pydantic python-multipart langchain sentence-transformers pypdf2 faiss-cpu google-generativeai
```

### 2. Document Processing Module

```python
# document_processor.py
import re
import PyPDF2
from typing import List, Dict, Any
from langchain.text_splitter import RecursiveCharacterTextSplitter

class DocumentProcessor:
    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
    
    def extract_text_from_pdf(self, pdf_file) -> str:
        """Extract text from a PDF file."""
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    
    def clean_text(self, text: str) -> str:
        """Clean extracted text."""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        # Additional cleaning as needed
        return text
    
    def split_text(self, text: str) -> List[str]:
        """Split text into chunks."""
        return self.text_splitter.split_text(text)
    
    def process_document(self, pdf_file) -> List[Dict[str, Any]]:
        """Process a PDF document into chunks with metadata."""
        text = self.extract_text_from_pdf(pdf_file)
        clean_text = self.clean_text(text)
        chunks = self.split_text(clean_text)
        
        # Create document chunks with metadata
        document_chunks = []
        for i, chunk in enumerate(chunks):
            document_chunks.append({
                "text": chunk,
                "metadata": {
                    "source": pdf_file.filename,
                    "chunk_id": i
                }
            })
        
        return document_chunks
```

### 3. Vector Store Module

```python
# vector_store.py
import numpy as np
from typing import List, Dict, Any
import faiss
from sentence_transformers import SentenceTransformer

class VectorStore:
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.index = None
        self.documents = []
    
    def add_documents(self, documents: List[Dict[str, Any]]):
        """Add documents to the vector store."""
        self.documents.extend(documents)
        texts = [doc["text"] for doc in documents]
        embeddings = self.model.encode(texts)
        
        if self.index is None:
            # Initialize FAISS index
            dimension = embeddings.shape[1]
            self.index = faiss.IndexFlatL2(dimension)
        
        # Add embeddings to index
        self.index.add(np.array(embeddings).astype('float32'))
    
    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Search for similar documents."""
        query_embedding = self.model.encode([query])
        scores, indices = self.index.search(np.array(query_embedding).astype('float32'), k)
        
        results = []
        for i, idx in enumerate(indices[0]):
            if idx < len(self.documents):
                result = self.documents[idx].copy()
                result["score"] = float(scores[0][i])
                results.append(result)
        
        return results
```

### 4. LLM Integration Module

```python
# llm_integration.py
import google.generativeai as genai
from typing import List, Dict, Any

class GeminiLLM:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro')
    
    def generate_response(self, query: str, context: List[Dict[str, Any]], history: List[Dict[str, str]]) -> str:
        """Generate response using Gemini."""
        # Prepare context from retrieved documents
        context_text = ""
        for doc in context:
            context_text += f"Source: {doc['metadata']['source']}\n{doc['text']}\n\n"
        
        # Prepare conversation history
        history_text = ""
        for msg in history:
            if msg["role"] == "user":
                history_text += f"User: {msg['content']}\n"
            elif msg["role"] == "assistant":
                history_text += f"Assistant: {msg['content']}\n"
        
        # Create the prompt
        prompt = f"""You are ARIA, an advanced HR and organizational assistant designed to provide helpful, accurate, and concise information to employees. 
        
Based on the following information from company documents:

{context_text}

And considering this conversation history:

{history_text}

Answer the following question from an employee. If the information isn't available in the provided context, acknowledge that and offer to help with related queries that you can answer.

User question: {query}

ARIA:"""
        
        # Generate response
        response = self.model.generate_content(prompt)
        return response.text
```

### 5. FastAPI Backend Service

```python
# main.py
import os
from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any
import uvicorn
from pydantic import BaseModel

from document_processor import DocumentProcessor
from vector_store import VectorStore
from llm_integration import GeminiLLM

app = FastAPI(title="ARIA RAG Backend")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Set this to your front-end URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
document_processor = DocumentProcessor()
vector_store = VectorStore()
llm = GeminiLLM(api_key=os.environ.get("GEMINI_API_KEY"))

# User document store (in-memory for now)
user_documents = {}

class ChatRequest(BaseModel):
    message: str
    history: List[Dict[str, str]]
    user: str

@app.post("/process")
async def process_documents(files: List[UploadFile] = File(...), user_email: str = Form(...)):
    """Process uploaded PDF documents."""
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")
    
    processed_docs = []
    for file in files:
        if not file.filename.endswith('.pdf'):
            continue
        
        try:
            # Process document
            document_chunks = document_processor.process_document(file.file)
            processed_docs.extend(document_chunks)
            
            # Store document reference
            if user_email not in user_documents:
                user_documents[user_email] = []
            user_documents[user_email].append(file.filename)
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error processing {file.filename}: {str(e)}")
    
    # Add documents to vector store
    vector_store.add_documents(processed_docs)
    
    return {"status": "success", "processed": len(processed_docs), "files": [f.filename for f in files]}

@app.get("/documents")
async def get_documents(user: str):
    """Get list of documents for a user."""
    if user not in user_documents:
        return {"documents": []}
    
    return {"documents": user_documents[user]}

@app.post("/chat")
async def chat(request: ChatRequest):
    """Chat with the RAG system."""
    try:
        # Search for relevant document chunks
        relevant_docs = vector_store.search(request.message, k=3)
        
        # Generate response
        response = llm.generate_response(
            query=request.message,
            context=relevant_docs,
            history=request.history
        )
        
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating response: {str(e)}")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
```

## Integration with Frontend

The frontend chat UI that you've already created will integrate with this backend through:

1. Document upload in the Files tab
2. Chat API calls to `/api/chat`
3. Document listing via `/api/documents`

## Deployment Considerations

For a production deployment:

1. **API Integration**: Update the frontend to point to your backend API
2. **Environment Variables**: Set up proper environment variables for API keys
3. **Storage**: Implement persistent storage for documents and vector database
4. **Authentication**: Add proper authentication between frontend and backend
5. **Caching**: Implement caching strategies for frequent queries
6. **Load Balancing**: For handling multiple concurrent requests

## References

- [umbertogriffo/rag-chatbot](https://github.com/umbertogriffo/rag-chatbot)
- [linghong/smartchat](https://github.com/linghong/smartchat)
- [Gemini API Documentation](https://ai.google.dev/docs/gemini_api)
- [FAISS Documentation](https://github.com/facebookresearch/faiss)
- [Sentence Transformers](https://www.sbert.net/) 