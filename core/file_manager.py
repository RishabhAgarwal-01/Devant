"""
File manager for the AI Coding Agent with async support
"""
import os
import aiofiles
from typing import List, Optional, Dict, Any
from utils.helpers import sanitize_path, compute_file_hash
from utils.logger import get_logger  # Updated import

class FileManager:
    def __init__(self, working_directory="."):
        self.logger = get_logger(__name__)  # Updated logger retrieval
        self.working_directory = working_directory

    def _resolve_path(self, file_path: str) -> str:
        """Resolve a file path relative to the working directory."""
        # Use sanitize_path for security
        safe_path = sanitize_path(file_path)
        return os.path.join(self.working_directory, safe_path)
        
    async def read_file(self, file_path: str) -> str:
        """Read the contents of a file asynchronously."""
        # Use sanitize_path for security
        safe_path = sanitize_path(file_path)
        
        try:
            async with aiofiles.open(safe_path, 'r', encoding='utf-8') as file:
                return await file.read()
        except Exception as e:
            self.logger.error(f"Error reading file {safe_path}: {str(e)}")
            raise
            
    async def write_file(self, file_path: str, content: str) -> bool:
        """Write content to a file asynchronously."""
        safe_path = self._resolve_path(file_path)
        
        try:
            # Ensure directory exists
            directory = os.path.dirname(os.path.abspath(safe_path))
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
            
            async with aiofiles.open(safe_path, 'w', encoding='utf-8') as file:
                await file.write(content)
            
            # Compute and log the file hash for verification
            file_hash = compute_file_hash(safe_path)
            self.logger.info(f"Successfully wrote file: {safe_path} (hash: {file_hash})")
            return True
        except Exception as e:
            self.logger.error(f"Error writing file {safe_path}: {str(e)}")
            raise
            
    async def list_files(self, directory: str, pattern: Optional[str] = None) -> List[str]:
        """List files in a directory asynchronously, optionally filtered by pattern."""
        import glob
        import asyncio
        
        # Use sanitize_path for security
        safe_directory = sanitize_path(directory)
        
        # Run the file listing in a thread to avoid blocking
        loop = asyncio.get_event_loop()
        if pattern:
            return await loop.run_in_executor(None, lambda: glob.glob(os.path.join(safe_directory, pattern)))
        else:
            def list_files_in_dir():
                return [os.path.join(safe_directory, f) for f in os.listdir(safe_directory) 
                       if os.path.isfile(os.path.join(safe_directory, f))]
            return await loop.run_in_executor(None, list_files_in_dir)
                   
    async def ensure_directory(self, directory: str) -> bool:
        """Ensure a directory exists asynchronously."""
        # Use sanitize_path for security
        safe_directory = sanitize_path(directory)
        
        try:
            # This is quite fast, so we can just run it directly
            os.makedirs(safe_directory, exist_ok=True)
            return True
        except Exception as e:
            self.logger.error(f"Error creating directory {safe_directory}: {str(e)}")
            raise
            
    async def file_exists(self, file_path: str) -> bool:
        """Check if a file exists asynchronously."""
        import asyncio
        
        # Use sanitize_path for security
        safe_path = sanitize_path(file_path)
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: os.path.exists(safe_path) and os.path.isfile(safe_path))
    
    async def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """Get information about a file asynchronously."""
        import asyncio
        
        # Use sanitize_path for security
        safe_path = sanitize_path(file_path)
        
        loop = asyncio.get_event_loop()
        
        try:
            exists = await self.file_exists(safe_path)
            if not exists:
                return {"exists": False}
            
            # Get file stats in a non-blocking way
            stat_info = await loop.run_in_executor(None, os.stat, safe_path)
            
            # Compute file hash
            file_hash = await loop.run_in_executor(None, compute_file_hash, safe_path)
            
            return {
                "exists": True,
                "size": stat_info.st_size,
                "modified": stat_info.st_mtime,
                "created": stat_info.st_ctime,
                "hash": file_hash
            }
        except Exception as e:
            self.logger.error(f"Error getting file info for {safe_path}: {str(e)}")
            return {"exists": False, "error": str(e)}