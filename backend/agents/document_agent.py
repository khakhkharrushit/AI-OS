import os
from typing import Optional
from agents.base import BaseAgent
from tools.base import Tool
from ai_core import generate_response

class DocumentAgent(BaseAgent):
    def __init__(self):
        super().__init__("DocumentAgent")
        self.register_tool(Tool("open_document", "Open a specific document, presentation, spreadsheet, or text file by name, keyword, or document type", self.open_document))
        self.register_tool(Tool("open_latest_document", "Find and open the most recently created or modified Word document (.docx), PDF, or spreadsheet", self.open_latest_document))
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

    def _kill_headless_process(self, proc_name: str):
        """Terminates any background instances of an application that have no visible window."""
        try:
            import psutil, ctypes
            from ctypes import wintypes
            user32 = ctypes.windll.user32
            WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
            for p in psutil.process_iter(['pid', 'name']):
                if p.info['name'] and p.info['name'].lower() == proc_name.lower():
                    pid = p.info['pid']
                    has_window = []
                    def enum_proc(hwnd, lparam):
                        w_pid = wintypes.DWORD()
                        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(w_pid))
                        if w_pid.value == pid and user32.IsWindowVisible(hwnd):
                            length = user32.GetWindowTextLengthW(hwnd)
                            if length > 0:
                                has_window.append(hwnd)
                        return True
                    user32.EnumWindows(WNDENUMPROC(enum_proc), 0)
                    if not has_window:
                        try:
                            p.kill()
                        except Exception:
                            pass
        except Exception:
            pass

    def _get_app_registry_path(self, exe_name: str) -> Optional[str]:
        """Resolves full executable path from Windows App Paths registry."""
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{exe_name}")
            val, _ = winreg.QueryValueEx(key, "")
            if os.path.exists(val):
                return val
        except Exception:
            pass
        return None

    def _bring_window_to_front(self, filename: str):
        """Asynchronously waits for application window to appear and brings it to top foreground."""
        import threading
        def worker():
            import time, ctypes
            from ctypes import wintypes
            user32 = ctypes.windll.user32
            WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
            base_keyword = os.path.splitext(os.path.basename(filename))[0].lower()
            for _ in range(8):
                time.sleep(0.5)
                found = []
                def enum_proc(hwnd, lparam):
                    class_buff = ctypes.create_unicode_buffer(256)
                    user32.GetClassNameW(hwnd, class_buff, 256)
                    c_name = class_buff.value.lower()
                    if 'opusapp' in c_name or 'nuidialog' in c_name or 'xlmain' in c_name or 'pptframeclass' in c_name:
                        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                        user32.SetForegroundWindow(hwnd)
                        found.append(hwnd)
                        return True
                    if user32.IsWindowVisible(hwnd):
                        length = user32.GetWindowTextLengthW(hwnd)
                        if length > 0:
                            buff = ctypes.create_unicode_buffer(length + 1)
                            user32.GetWindowTextW(hwnd, buff, length + 1)
                            t = buff.value.lower()
                            if base_keyword in t or "word" in t or "excel" in t or "acrobat" in t:
                                user32.ShowWindow(hwnd, 9)
                                user32.SetForegroundWindow(hwnd)
                                found.append(hwnd)
                    return True
                user32.EnumWindows(WNDENUMPROC(enum_proc), 0)
                if found:
                    break
        threading.Thread(target=worker, daemon=True).start()

    def open_document(self, query: str = "", doc_type: str = "", **kwargs) -> str:
        """
        Intelligently opens a document by filename, topic keyword (e.g. 'resume', 'report', 'notes'),
        or document type (e.g. 'word', 'ppt', 'text', 'excel', 'pdf').
        Searches Desktop, Documents, Downloads, and Workspace for exact or partial matches.
        """
        import glob
        q_clean = (query or "").strip().lower()
        dt_clean = (doc_type or "").strip().lower().replace(".", "")

        # 1. Route general keywords to open_latest_document or app launcher
        if q_clean in ["word", "doc", "docx", "word document", "word doc", "word file"] or dt_clean in ["word", "doc", "docx"]:
            return self.open_latest_document("docx")
        if q_clean in ["ppt", "pptx", "powerpoint", "presentation", "slides", "slide"] or dt_clean in ["ppt", "pptx", "powerpoint"]:
            return self.open_latest_document("pptx")
        if q_clean in ["excel", "sheet", "spreadsheet", "csv", "xlsx", "xls"] or dt_clean in ["excel", "xlsx", "sheet"]:
            return self.open_latest_document("excel")
        if q_clean in ["text", "txt", "note", "notes", "text file", "notepad"] or dt_clean in ["txt", "text"]:
            return self.open_latest_document("txt")
        if q_clean in ["pdf", "pdf document", "pdf file"] or dt_clean == "pdf":
            return self.open_latest_document("pdf")
        if q_clean in ["document", "latest document", "recent document", "file"]:
            return self.open_latest_document(dt_clean or "docx")

        # 2. Search for specific named file across the laptop
        home = os.path.expanduser("~")
        search_dirs = [
            os.path.join(home, "Desktop"),
            os.path.join(home, "OneDrive", "Desktop"),
            os.path.join(home, "Downloads"),
            os.path.join(home, "Documents"),
            os.path.join(home, "OneDrive", "Documents"),
            r"C:\Users\khakh\Downloads\Project-1",
            os.getcwd(),
        ]

        # Candidate extensions
        exts = [".docx", ".pdf", ".txt", ".pptx", ".xlsx", ".doc", ".ppt", ".xls", ".md", ".csv", ".html", ""]
        found_matches = []

        # Check exact paths first
        for s_dir in search_dirs:
            if not os.path.exists(s_dir):
                continue
            for ext in exts:
                candidate = os.path.join(s_dir, q_clean + ext if ext else q_clean)
                if os.path.isfile(candidate):
                    mtime = os.path.getmtime(candidate)
                    base_score = 100
                    # Prioritize .docx over .pdf for report/document queries unless user explicitly asked for pdf
                    if ext == ".docx" and "pdf" not in q_clean:
                        base_score = 110
                    found_matches.append((candidate, base_score, mtime))

        # Check recursive pattern matching
        if not found_matches:
            keyword_clean = q_clean.replace("open", "").replace("the", "").replace("document", "").replace("file", "").strip()
            if not keyword_clean:
                keyword_clean = q_clean

            for s_dir in search_dirs:
                if not os.path.exists(s_dir):
                    continue
                try:
                    for root, dirs, files in os.walk(s_dir):
                        dirs[:] = [d for d in dirs if not d.startswith(".") and d.lower() not in ["node_modules", "venv", "__pycache__", "appdata"]]
                        for f in files:
                            if f.startswith("~$"):
                                continue
                            f_lower = f.lower()
                            if keyword_clean in f_lower:
                                full_p = os.path.join(root, f)
                                is_exact = (keyword_clean == os.path.splitext(f_lower)[0] or keyword_clean == f_lower)
                                score = 90 if is_exact else 50
                                try:
                                    mtime = os.path.getmtime(full_p)
                                    found_matches.append((full_p, score, mtime))
                                except Exception:
                                    pass
                        # Limit depth to 3 levels
                        if root.count(os.sep) - s_dir.count(os.sep) >= 3:
                            del dirs[:]
                except Exception:
                    pass

        if found_matches:
            # Sort by score descending, then mtime descending
            found_matches.sort(key=lambda x: (x[1], x[2]), reverse=True)
            chosen_file = found_matches[0][0]
            import subprocess
            ext = os.path.splitext(chosen_file)[1].lower()
            try:
                if ext in [".docx", ".doc"]:
                    winword = r"C:\Program Files\Microsoft Office\Root\Office16\WINWORD.EXE"
                    if os.path.exists(winword):
                        subprocess.Popen([winword, chosen_file])
                    else:
                        subprocess.Popen(f'powershell -WindowStyle Normal -Command "Start-Process \"{chosen_file}\""', shell=True)
                elif ext in [".pptx", ".ppt"]:
                    ppt = r"C:\Program Files\Microsoft Office\Root\Office16\POWERPNT.EXE"
                    if os.path.exists(ppt):
                        subprocess.Popen([ppt, chosen_file])
                    else:
                        subprocess.Popen(f'powershell -WindowStyle Normal -Command "Start-Process \"{chosen_file}\""', shell=True)
                elif ext in [".xlsx", ".xls"]:
                    excel = r"C:\Program Files\Microsoft Office\Root\Office16\EXCEL.EXE"
                    if os.path.exists(excel):
                        subprocess.Popen([excel, chosen_file])
                    else:
                        subprocess.Popen(f'powershell -WindowStyle Normal -Command "Start-Process \"{chosen_file}\""', shell=True)
                elif ext == ".pdf":
                    subprocess.Popen(f'powershell -WindowStyle Normal -Command "Start-Process msedge.exe -ArgumentList \"{chosen_file}\""', shell=True)
                elif ext in [".txt", ".md", ".json", ".log"]:
                    subprocess.Popen(["notepad.exe", chosen_file])
                else:
                    subprocess.Popen(f'powershell -WindowStyle Normal -Command "Start-Process \"{chosen_file}\""', shell=True)
            except Exception:
                try:
                    os.startfile(chosen_file)
                except Exception:
                    subprocess.Popen(f'cmd.exe /c start "" "{chosen_file}"', shell=True)

            self._bring_window_to_front(chosen_file)
            return f"Successfully opened '{os.path.basename(chosen_file)}' (Path: {chosen_file})"

        # Fallback to opening latest document of requested or detected type
        return self.open_latest_document(dt_clean or "docx")

    def open_latest_document(self, doc_type: str = "docx", **kwargs) -> str:
        """
        Finds the most recently created or modified document (Word .docx, PDF, Excel, etc.)
        across Desktop, Documents, Downloads, and current workspace,
        and opens it directly in the foreground. If none found, launches the app.
        """
        import glob
        import subprocess
        home = os.path.expanduser("~")
        search_dirs = [
            os.path.join(home, "Desktop"),
            os.path.join(home, "OneDrive", "Desktop"),
            os.path.join(home, "Documents"),
            os.path.join(home, "OneDrive", "Documents"),
            os.path.join(home, "Downloads"),
            os.path.join(home, "Downloads", "Project-1"),
            os.getcwd(),
        ]
        
        doc_type_clean = (doc_type or "docx").lower().strip().replace('.', '')
        if doc_type_clean in ["word", "doc", "docx", "word document", "word doc", "word file"]:
            patterns = ["*.docx", "*.doc", "*.rtf"]
            fallback_app = r"C:\Program Files\Microsoft Office\Root\Office16\WINWORD.EXE"
            fallback_cmd = "winword"
        elif doc_type_clean in ["pdf", "pdf document", "pdf file"]:
            patterns = ["*.pdf"]
            fallback_app = None
            fallback_cmd = None
        elif doc_type_clean in ["excel", "xlsx", "xls", "spreadsheet", "sheet", "csv"]:
            patterns = ["*.xlsx", "*.xls", "*.csv"]
            fallback_app = r"C:\Program Files\Microsoft Office\Root\Office16\EXCEL.EXE"
            fallback_cmd = "excel"
        elif doc_type_clean in ["powerpoint", "ppt", "pptx", "presentation", "slides", "slide"]:
            patterns = ["*.pptx", "*.ppt", "*.ppsx"]
            fallback_app = r"C:\Program Files\Microsoft Office\Root\Office16\POWERPNT.EXE"
            fallback_cmd = "powerpnt"
        elif doc_type_clean in ["bitmap", "bmp", "image", "photo", "picture", "pic", "img", "png", "jpg", "jpeg"]:
            patterns = ["*.bmp", "*.png", "*.jpg", "*.jpeg", "*.gif", "*.webp", "*.ico"]
            fallback_app = "mspaint.exe"
            fallback_cmd = "mspaint"
        elif doc_type_clean in ["text", "txt", "note", "notes", "test", "log"]:
            patterns = ["*.txt", "*.md", "*.log", "*.json"]
            fallback_app = "notepad.exe"
            fallback_cmd = "notepad"
        else:
            patterns = [f"*.{doc_type_clean}", "*.docx", "*.pdf", "*.txt", "*.xlsx", "*.pptx"]
            fallback_app = None
            fallback_cmd = None

        found_files = []
        for s_dir in search_dirs:
            if os.path.exists(s_dir):
                for pat in patterns:
                    try:
                        matches = glob.glob(os.path.join(s_dir, pat))
                        matches += glob.glob(os.path.join(s_dir, "*", pat))
                        for m in matches:
                            if not os.path.basename(m).startswith("~$") and os.path.isfile(m):
                                try:
                                    mtime = os.path.getmtime(m)
                                    found_files.append((m, mtime))
                                except Exception:
                                    pass
                    except Exception:
                        pass

        if not found_files:
            # If no file exists, launch the application itself so user is never blocked
            if fallback_app and os.path.exists(fallback_app):
                subprocess.Popen([fallback_app])
                return f"No recent {doc_type} files found. Launched {os.path.basename(fallback_app)} application for you."
            elif fallback_cmd:
                subprocess.Popen(f'cmd.exe /c start "" "{fallback_cmd}"', shell=True)
                return f"No recent {doc_type} files found. Launched {fallback_cmd} application for you."
            return f"No recent {doc_type} files found in Desktop, Documents, or Downloads."

        # Sort by modification timestamp descending
        found_files.sort(key=lambda x: x[1], reverse=True)
        latest_file = found_files[0][0]
        ext = os.path.splitext(latest_file)[1].lower()

        # Primary launch via os.startfile
        try:
            os.startfile(latest_file)
            self._bring_window_to_front(latest_file)
            app_desc = "Microsoft Word" if ext in [".docx", ".doc"] else ("Microsoft Excel" if ext in [".xlsx", ".xls", ".csv"] else ("PowerPoint" if ext in [".pptx", ".ppt"] else "default viewer"))
            return f"Successfully opened '{os.path.basename(latest_file)}' in {app_desc} (Path: {latest_file})"
        except Exception as e:
            try:
                subprocess.Popen(f'cmd.exe /c start "" "{latest_file}"', shell=True)
                self._bring_window_to_front(latest_file)
                return f"Successfully opened '{os.path.basename(latest_file)}' (Path: {latest_file})"
            except Exception:
                pass
            raise Exception(f"Failed to open '{latest_file}': {e}")