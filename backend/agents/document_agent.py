import os
from typing import Optional
from agents.base import BaseAgent
from tools.base import Tool
from ai_core import generate_response

class DocumentAgent(BaseAgent):
    def __init__(self):
        super().__init__("DocumentAgent")
        self.register_tool(Tool("read_pdf", "Extract text content from a PDF document", self.read_pdf))
        self.register_tool(Tool("read_docx", "Extract text content from a Word .docx document", self.read_docx))
        self.register_tool(Tool("summarize_document", "Read and generate an AI summary of a document (PDF, Word, TXT, MD)", self.summarize_document))
        self.register_tool(Tool("search_document_text", "Search for a specific keyword or phrase inside a document file", self.search_document_text))
        self.register_tool(Tool("create_markdown_report", "Create a structured markdown document or report file", self.create_markdown_report))

    def _normalize_path(self, filepath: str) -> str:
        filepath = os.path.expanduser(filepath)
        lower_path = filepath.lower()
        if lower_path.startswith('/home/user') or lower_path.startswith('\\home\\user'):
            filepath = os.path.join(os.path.expanduser('~'), filepath[11:])
            lower_path = filepath.lower()
        if lower_path.startswith('desktop\\') or lower_path.startswith('desktop/'):
            filepath = os.path.join(os.path.expanduser('~'), 'Desktop', filepath[8:])
        elif lower_path == 'desktop':
            filepath = os.path.expanduser('~/Desktop')
        filepath = os.path.normpath(filepath)
        
        desktop_path = os.path.normpath(os.path.expanduser("~/Desktop"))
        onedrive_desktop = os.path.normpath(os.path.expanduser("~/OneDrive/Desktop"))
        if filepath.startswith(desktop_path):
            onedrive_filepath = filepath.replace(desktop_path, onedrive_desktop, 1)
            if not os.path.exists(filepath) and os.path.exists(onedrive_filepath):
                filepath = onedrive_filepath
        return filepath

    def read_pdf(self, filepath: str, max_pages: int = 15, **kwargs) -> str:
        filepath = self._normalize_path(filepath)
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"PDF file '{filepath}' not found.")
            
        try:
            from pypdf import PdfReader
            reader = PdfReader(filepath)
            num_pages = len(reader.pages)
            pages_to_read = min(num_pages, int(max_pages))
            
            text_chunks = []
            for i in range(pages_to_read):
                page_text = reader.pages[i].extract_text() or ""
                if page_text.strip():
                    text_chunks.append(f"--- Page {i+1} ---\n{page_text.strip()}")
                    
            full_text = "\n\n".join(text_chunks)
            if not full_text:
                return f"PDF '{filepath}' has {num_pages} pages, but no extractable text was found (it may be a scanned image)."
            return f"Extracted text from '{filepath}' ({pages_to_read}/{num_pages} pages):\n\n{full_text}"
        except ImportError:
            # Fallback basic binary text extractor if pypdf is not yet installed
            try:
                with open(filepath, 'rb') as f:
                    content = f.read(5000).decode('utf-8', errors='ignore')
                return f"PDF content preview (Raw Text):\n{content}"
            except Exception as e:
                raise Exception(f"Failed to read PDF '{filepath}': {e}. Please install pypdf.")
        except Exception as e:
            raise Exception(f"Error reading PDF '{filepath}': {e}")

    def read_docx(self, filepath: str, max_paragraphs: int = 50, **kwargs) -> str:
        filepath = self._normalize_path(filepath)
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Document file '{filepath}' not found.")
            
        try:
            import docx
            doc = docx.Document(filepath)
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            selected = paragraphs[:int(max_paragraphs)]
            if not selected:
                return f"Word document '{filepath}' is empty."
            text = "\n\n".join(selected)
            return f"Extracted text from '{filepath}' ({len(selected)} paragraphs):\n\n{text}"
        except ImportError:
            raise Exception("python-docx is required to read .docx files.")
        except Exception as e:
            raise Exception(f"Error reading .docx file '{filepath}': {e}")

    def summarize_document(self, filepath: str, max_chars: int = 4000, **kwargs) -> str:
        filepath = self._normalize_path(filepath)
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Document file '{filepath}' not found.")

        # Extract text based on extension
        ext = os.path.splitext(filepath)[1].lower()
        if ext == ".pdf":
            raw_text = self.read_pdf(filepath)
        elif ext in [".docx", ".doc"]:
            raw_text = self.read_docx(filepath)
        else:
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                raw_text = f.read(max_chars)

        if not raw_text.strip():
            return f"Document '{filepath}' appears to be empty."

        prompt = f"""
You are the AI OS Document Agent. Provide a comprehensive summary of the following document content:

File: {filepath}
Content:
{raw_text[:max_chars]}

Format your response with:
1. Executive Summary (2-3 sentences)
2. Key Points / Takeaways (bullet points)
3. Action Items or Important Entities Mentioned
"""
        try:
            summary = generate_response(prompt)
            return f"AI Summary for '{os.path.basename(filepath)}':\n\n{summary}"
        except Exception as e:
            return f"Document Content Preview ({len(raw_text)} chars):\n\n{raw_text[:1000]}...\n(Summarization failed: {e})"

    def search_document_text(self, filepath: str, query: str, **kwargs) -> str:
        filepath = self._normalize_path(filepath)
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Document file '{filepath}' not found.")
        if not query:
            raise ValueError("Query string is required.")

        ext = os.path.splitext(filepath)[1].lower()
        if ext == ".pdf":
            text = self.read_pdf(filepath)
        elif ext in [".docx", ".doc"]:
            text = self.read_docx(filepath)
        else:
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                text = f.read()

        lines = text.split('\n')
        matches = []
        for idx, line in enumerate(lines, 1):
            if query.lower() in line.lower():
                matches.append(f"Line {idx}: {line.strip()}")

        if not matches:
            return f"No occurrences of '{query}' found in '{filepath}'."
        return f"Found {len(matches)} occurrences of '{query}' in '{filepath}':\n" + "\n".join(matches[:15])

    def create_markdown_report(self, filepath: str, title: str, content: str, **kwargs) -> str:
        filepath = self._normalize_path(filepath)
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
        
        md_content = f"# {title}\n\n*Generated by AI OS Document Agent*\n\n{content}\n"
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(md_content)
        return f"Successfully created Markdown report at '{filepath}' ({len(md_content)} characters)."
