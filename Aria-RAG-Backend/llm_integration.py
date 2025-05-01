import google.generativeai as genai
from typing import List, Dict, Any

class GeminiLLM:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
    
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