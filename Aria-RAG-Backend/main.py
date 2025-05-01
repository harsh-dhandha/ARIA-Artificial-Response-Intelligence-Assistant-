import os
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any
import uvicorn
from pydantic import BaseModel
from dotenv import load_dotenv

from document_processor import DocumentProcessor
from vector_store import VectorStore
from llm_integration import GeminiLLM

# Load environment variables
load_dotenv()

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