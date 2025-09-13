import PyPDF2
import pdfplumber
import re

class PDFProcessor:
    @staticmethod
    def extract_text_pypdf2(pdf_path):
        text = ""
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    text += page.extract_text()
        except Exception as e:
            print(f"PyPDF2 extraction failed: {e}")
        return text
    
    @staticmethod
    def extract_text_pdfplumber(pdf_path):
        text = ""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            print(f"pdfplumber extraction failed: {e}")
        return text
    
    @staticmethod
    def clean_text(text):
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters that might cause issues
        text = re.sub(r'[^\w\s\.\,\!\?\-\']', '', text)
        # Remove multiple periods
        text = re.sub(r'\.{2,}', '.', text)
        return text.strip()
    
    @staticmethod
    def extract_text(pdf_path, max_chars=None):
        # Try pdfplumber first (usually better)
        text = PDFProcessor.extract_text_pdfplumber(pdf_path)
        
        # Fallback to PyPDF2 if pdfplumber fails
        if not text:
            text = PDFProcessor.extract_text_pypdf2(pdf_path)
        
        # Clean the text
        text = PDFProcessor.clean_text(text)
        
        # Limit text length if specified
        if max_chars and len(text) > max_chars:
            text = text[:max_chars] + "..."
        
        return text
    
    @staticmethod
    def split_into_chunks(text, chunk_size=500):
        # Split text into smaller chunks for processing
        words = text.split()
        chunks = []
        current_chunk = []
        current_length = 0
        
        for word in words:
            current_chunk.append(word)
            current_length += len(word) + 1
            
            if current_length >= chunk_size:
                chunks.append(' '.join(current_chunk))
                current_chunk = []
                current_length = 0
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks