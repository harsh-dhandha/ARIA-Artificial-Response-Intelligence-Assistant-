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