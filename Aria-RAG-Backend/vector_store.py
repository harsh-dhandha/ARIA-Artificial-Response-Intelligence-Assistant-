from typing import List, Dict, Any
import chromadb
import os
import uuid

class VectorStore:
    def __init__(self):
        # Create a persistent client
        os.makedirs("chroma_db", exist_ok=True)
        self.client = chromadb.PersistentClient(path="chroma_db")
        
        # Create or get collection with default embedding function
        self.collection = self.client.get_or_create_collection(
            name="documents"
        )
        
        # Store documents for later reference
        self.documents = []
    
    def add_documents(self, documents: List[Dict[str, Any]]):
        """Add documents to the vector store."""
        if not documents:
            return
            
        self.documents.extend(documents)
        
        # Prepare data for Chroma
        ids = [str(uuid.uuid4()) for _ in documents]
        texts = [doc["text"] for doc in documents]
        metadatas = [doc["metadata"] for doc in documents]
        
        # Add to collection
        self.collection.add(
            ids=ids,
            documents=texts,
            metadatas=metadatas
        )
    
    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Search for similar documents."""
        if self.collection.count() == 0:
            return []
            
        # Query the collection
        results = self.collection.query(
            query_texts=[query],
            n_results=k
        )
        
        # Format results
        formatted_results = []
        if results and results["documents"]:
            for i, (doc_text, metadata, distance) in enumerate(zip(
                results["documents"][0], 
                results["metadatas"][0],
                results["distances"][0] if "distances" in results else [0] * len(results["documents"][0])
            )):
                score = 1.0 - (distance if distance else 0)  # Convert distance to similarity score
                formatted_results.append({
                    "text": doc_text,
                    "metadata": metadata,
                    "score": score
                })
                
        return formatted_results