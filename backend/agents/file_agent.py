import os
import shutil
from agents.base import BaseAgent
from tools.base import Tool

class FileAgent(BaseAgent):
    def __init__(self):
        super().__init__("FileAgent")
        self.register_tool(Tool("search_file", "Search for a file", self.search_file))
        self.register_tool(Tool("read_file", "Read text content from a file", self.read_file))
        self.register_tool(Tool("write_file", "Write text content to a file", self.write_file))
        self.register_tool(Tool("append_file", "Append text content to a file", self.append_file))
        self.register_tool(Tool("create_file", "Create an empty file", self.create_file))
        self.register_tool(Tool("copy_file", "Copy a file from src to dest", self.copy_file))
        self.register_tool(Tool("move_file", "Move or rename a file", self.move_file))
        self.register_tool(Tool("delete_file", "Delete a file", self.delete_file, high_risk=True))
        self.register_tool(Tool("delete_folder", "Delete a folder and all its contents", self.delete_folder, high_risk=True))
        self.register_tool(Tool("find_and_delete", "Find any file or folder by name anywhere on laptop and delete it with confirmation", self.find_and_delete, high_risk=True))
        self.register_tool(Tool("create_folder", "Create a directory folder", self.create_folder))
        self.register_tool(Tool("list_directory", "List files and folders in a directory", self.list_directory))
        self.register_tool(Tool("open_file", "Open any file, document, or folder on the laptop by name or path", self.open_file))
        
    def _normalize_path(self, filepath: str, default_to_desktop: bool = True) -> str:
        if not filepath:
            filepath = "document.txt"
            
        filepath = os.path.expanduser(filepath.strip())
        lower_path = filepath.lower()
        
        # Replace hallucinated unix home directories with real home directory
        if lower_path.startswith('/home/user') or lower_path.startswith('\\home\\user'):
            filepath = os.path.join(os.path.expanduser('~'), filepath[11:])
            lower_path = filepath.lower()
            
        # Handle bare filename or 'desktop' prefix
        if lower_path.startswith('desktop\\') or lower_path.startswith('desktop/'):
            filepath = os.path.join(os.path.expanduser('~'), 'Desktop', filepath[8:])
        elif lower_path == 'desktop':
            filepath = os.path.expanduser('~/Desktop')
        elif default_to_desktop and not os.path.isabs(filepath) and not filepath.startswith(".") and not ("\\" in filepath or "/" in filepath):
            # Bare filename like "rk.txt" -> Save on Desktop so user sees it immediately
            filepath = os.path.join(os.path.expanduser('~'), 'Desktop', filepath)
            
        filepath = os.path.abspath(os.path.normpath(filepath))
        
        # Handle Windows OneDrive Desktop Sync
        desktop_path = os.path.normpath(os.path.expanduser("~/Desktop"))
        onedrive_desktop = os.path.normpath(os.path.expanduser("~/OneDrive/Desktop"))
        
        if filepath.startswith(desktop_path) and os.path.exists(onedrive_desktop):
            onedrive_filepath = filepath.replace(desktop_path, onedrive_desktop, 1)
            # Use OneDrive Desktop if existing or primary
            if os.path.exists(onedrive_filepath) or not os.path.exists(filepath):
                filepath = onedrive_filepath
                
        return filepath

    def create_file(self, filepath: str) -> str:
        filepath = self._normalize_path(filepath)
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            pass
        return f"Created empty file '{filepath}'"

    def search_file(self, filename: str, directory: str = ".") -> str:
        directory = self._normalize_path(directory, default_to_desktop=False)
        found = []
        for root, _, files in os.walk(directory):
            for file in files:
                if filename.lower() in file.lower():
                    found.append(os.path.join(root, file))
        if not found:
            return f"No files found matching '{filename}'."
        return f"Found {len(found)} files: " + ", ".join(found)

    def move_file(self, src: str, dest: str) -> str:
        src = self._normalize_path(src, default_to_desktop=False)
        dest = self._normalize_path(dest, default_to_desktop=True)
        if not os.path.exists(src):
            raise FileNotFoundError(f"Source file '{src}' not found.")
        shutil.move(src, dest)
        return f"Moved '{src}' to '{dest}'"
        
    def delete_file(self, filepath: str) -> str:
        filepath = self._normalize_path(filepath, default_to_desktop=False)
        if not os.path.exists(filepath):
            # Try searching laptop if path not found directly
            matches = self._find_item_on_laptop(os.path.basename(filepath))
            if matches:
                filepath = matches[0][0]
            else:
                raise FileNotFoundError(f"File '{filepath}' not found.")
        os.remove(filepath)
        return f"Successfully deleted file '{filepath}'"

    def delete_folder(self, folderpath: str) -> str:
        folderpath = self._normalize_path(folderpath, default_to_desktop=False)
        if not os.path.exists(folderpath):
            matches = self._find_item_on_laptop(os.path.basename(folderpath))
            dir_matches = [m for m in matches if m[1]]
            if dir_matches:
                folderpath = dir_matches[0][0]
            else:
                raise FileNotFoundError(f"Folder '{folderpath}' not found.")
        shutil.rmtree(folderpath)
        return f"Successfully deleted folder and its contents: '{folderpath}'"

    def _find_item_on_laptop(self, target_name: str) -> list[tuple[str, bool]]:
        """
        Fast deep search across user's laptop for a matching file or directory.
        Returns list of (full_path, is_directory) tuples sorted by exact match and recency.
        """
        home = os.path.expanduser("~")
        search_roots = [
            os.path.join(home, "Desktop"),
            os.path.join(home, "OneDrive", "Desktop"),
            os.path.join(home, "Downloads"),
            os.path.join(home, "Documents"),
            os.path.join(home, "OneDrive", "Documents"),
            os.path.join(home, "Pictures"),
            os.path.join(home, "Videos"),
            os.path.join(home, "Music"),
            os.getcwd(),
        ]
        target_clean = target_name.lower().strip().replace('"', '').replace("'", "")
        matches = []
        for root_dir in search_roots:
            if not os.path.exists(root_dir):
                continue
            base_depth = root_dir.count(os.sep)
            for root, dirs, files in os.walk(root_dir):
                dirs[:] = [d for d in dirs if not d.startswith('.') and d.lower() not in ['node_modules', 'venv', '__pycache__', 'site-packages', 'appdata']]
                if root.count(os.sep) - base_depth > 4:
                    continue
                for f in files:
                    f_name = f.lower()
                    if target_clean == f_name or target_clean in f_name or target_clean == os.path.splitext(f_name)[0]:
                        full_p = os.path.join(root, f)
                        try:
                            mtime = os.path.getmtime(full_p)
                        except Exception:
                            mtime = 0
                        is_exact = (target_clean == f_name or target_clean == os.path.splitext(f_name)[0])
                        matches.append((full_p, False, is_exact, mtime))
                for d in dirs:
                    d_name = d.lower()
                    if target_clean == d_name or target_clean in d_name:
                        full_p = os.path.join(root, d)
                        try:
                            mtime = os.path.getmtime(full_p)
                        except Exception:
                            mtime = 0
                        is_exact = (target_clean == d_name)
                        matches.append((full_p, True, is_exact, mtime))

        # Sort: exact matches first, then newest modified timestamp
        matches.sort(key=lambda x: (1 if x[2] else 0, x[3]), reverse=True)
        return [(m[0], m[1]) for m in matches]

    def find_and_delete(self, target_name: str, **kwargs) -> str:
        """
        Locates a file or folder by name anywhere on the laptop and deletes it after human confirmation.
        """
        if not target_name:
            raise ValueError("Target file or folder name is required for deletion.")
        
        matches = self._find_item_on_laptop(target_name)
        if not matches:
            raise FileNotFoundError(f"Target '{target_name}' was not found anywhere across Desktop, Documents, Downloads, or Workspace.")
        
        target_path, is_dir = matches[0]
        if is_dir:
            shutil.rmtree(target_path)
            return f"Successfully deleted folder: '{target_path}'"
        else:
            os.remove(target_path)
            return f"Successfully deleted file: '{target_path}'"

    def read_file(self, filepath: str, max_chars: int = 5000) -> str:
        filepath = self._normalize_path(filepath, default_to_desktop=False)
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File '{filepath}' not found.")
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read(max_chars)
        truncated_msg = " [Truncated]" if len(content) >= max_chars else ""
        return f"Content of '{filepath}':\n{content}{truncated_msg}"

    def write_file(self, filepath: str, content: str) -> str:
        filepath = self._normalize_path(filepath, default_to_desktop=True)
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully wrote '{content}' to '{filepath}'"

    def append_file(self, filepath: str, content: str) -> str:
        filepath = self._normalize_path(filepath, default_to_desktop=True)
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
        with open(filepath, 'a', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully appended content to '{filepath}'"

    def copy_file(self, src: str, dest: str) -> str:
        src = self._normalize_path(src, default_to_desktop=False)
        dest = self._normalize_path(dest, default_to_desktop=True)
        if not os.path.exists(src):
            raise FileNotFoundError(f"Source file '{src}' not found.")
        dest_dir = os.path.dirname(dest)
        if dest_dir:
            os.makedirs(dest_dir, exist_ok=True)
        shutil.copy2(src, dest)
        return f"Copied '{src}' to '{dest}'"

    def create_folder(self, folderpath: str) -> str:
        folderpath = self._normalize_path(folderpath, default_to_desktop=True)
        os.makedirs(folderpath, exist_ok=True)
        return f"Created folder '{folderpath}'"

    def list_directory(self, directory: str = ".") -> str:
        directory = self._normalize_path(directory, default_to_desktop=False)
        if not os.path.exists(directory):
            raise FileNotFoundError(f"Directory '{directory}' does not exist.")
        entries = []
        for entry in os.scandir(directory):
            prefix = "[DIR]" if entry.is_dir() else "[FILE]"
            entries.append(f"{prefix} {entry.name}")
        if not entries:
            return f"Directory '{directory}' is empty."
        return f"Directory contents of '{directory}':\n" + "\n".join(entries[:50])

    def open_file(self, filename: str, **kwargs) -> str:
        """
        Locates any file on the laptop and opens it directly in its default desktop application.
        """
        if not filename:
            raise ValueError("Filename is required.")
        matches = self._find_item_on_laptop(filename)
        if matches:
            target_path = matches[0][0]
            try:
                os.startfile(target_path)
                return f"Successfully opened '{os.path.basename(target_path)}' (Path: {target_path})"
            except Exception as e:
                import subprocess
                subprocess.Popen(f'cmd.exe /c start "" "{target_path}"', shell=True)
                return f"Launched '{os.path.basename(target_path)}' (Path: {target_path})"
        raise FileNotFoundError(f"File '{filename}' was not found on your system.")
