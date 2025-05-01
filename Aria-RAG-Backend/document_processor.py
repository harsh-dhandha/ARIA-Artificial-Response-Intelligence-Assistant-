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