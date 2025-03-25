"""Helper utilities for the AI coding agent"""
import json
from typing import Any, Dict
import hashlib
import os

def load_json(file_path:str) -> Dict[str, Any]:
    """Load the JSON file with the training data"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(data: Dict[str, Any], file_path: str) -> None:
    """Save JSON data to a file."""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

def compute_file_hash(file_path: str) -> str:
    """Compute a hash of a file's contents."""
    if not os.path.exists(file_path):
        return ""
    
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()

def format_code(code: str, language: str) -> str:
    """Format code according to standard style guides.
    
    Note: This is a placeholder. In a real implementation, 
    this would use language-specific formatters like black for Python.
    """
    # For now, just return the code as-is
    return code

def extract_language_from_path(file_path: str) -> str:
    """Extract the programming language from a file path."""
    extension = os.path.splitext(file_path)[1].lower()
    
    language_map = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".html": "html",
        ".css": "css",
        ".json": "json",
        ".md": "markdown",
        ".sh": "bash",
        ".rs": "rust",
        ".go": "go",
        ".java": "java",
        ".cpp": "cpp",
        ".c": "c",
        ".rb": "ruby",
        ".php": "php",
    }
    
    return language_map.get(extension, "unknown")

def sanitize_path(path: str) -> str:
    """Sanitize a file path for security."""
    # Remove potentially dangerous path components
    path = os.path.normpath(path)
    
    # Ensure the path doesn't try to navigate up directories
    if '..' in path:
        parts = [p for p in path.split(os.sep) if p != '..']
        path = os.sep.join(parts)
    
    return path