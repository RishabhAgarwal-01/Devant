# """
# File manager for the AI Coding Agent with async support
# """

# import os
# import aiofiles
# from typing import List, Optional, Dict, Any
# from utils.helpers import sanitize_path, compute_file_hash, normalize_line_endings
# from utils.logger import get_logger
# import asyncio
# import json

# class FileManager:
#     def __init__(self, working_directory="."):
#         self.logger = get_logger(__name__)
#         self.working_directory = os.path.abspath(working_directory)
#         self._ensure_working_dir()

#     def _ensure_working_dir(self):
#         """Ensure working directory exists"""
#         try:
#             os.makedirs(self.working_directory, exist_ok=True)
#         except Exception as e:
#             self.logger.error(f"Error creating working directory: {str(e)}")
#             raise

#     def _resolve_path(self, file_path: str) -> str:
#         """Resolve a file path relative to the working directory."""
#         if not file_path.strip():
#             raise ValueError("File path cannot be empty or whitespace")
        
#         # Normalize path separators
#         file_path = file_path.replace('\\', '/')
        
#         # Remove any duplicate working directory prefixes
#         if file_path.startswith(self.working_directory):
#             file_path = file_path[len(self.working_directory):]
#             if file_path.startswith(('\\', '/')):
#                 file_path = file_path[1:]
        
#         # Join and normalize the final path
#         full_path = os.path.join(self.working_directory, file_path)
#         return os.path.normpath(full_path)
            
#     async def read_file(self, file_path: str) -> str:
#         """Read file content asynchronously"""
#         self.logger.debug(f"Resolving path. Original: {file_path}, Working dir: {self.working_directory}")
#         safe_path = self._resolve_path(file_path)
#         try:
#             async with aiofiles.open(safe_path, 'r', encoding='utf-8') as file:
#                 return await file.read()
#         except Exception as e:
#             self.logger.error(f"Error reading file {safe_path}: {str(e)}")
#             raise
            
#     async def write_file(self, file_path: str, content: str, max_retries: int = 3) -> bool:
#         """Atomic file write with proper path handling"""
#         if isinstance(content, dict):
#             content = json.dumps(content, indent=2)
#             content = normalize_line_endings(content)

#         self.logger.debug(f"Resolving path. Original: {file_path}, Working dir: {self.working_directory}")
#         safe_path = self._resolve_path(file_path)
#         self.logger.debug(f"Writing file to: {safe_path}")
        
#         # Ensure parent directory exists
#         parent_dir = os.path.dirname(safe_path)
#         if parent_dir:
#             os.makedirs(parent_dir, exist_ok=True)

        
#         for attempt in range(max_retries):
#             try:
#                 # Write to temporary file first
#                 temp_path = f"{safe_path}.tmp"
#                 async with aiofiles.open(temp_path, 'w', encoding='utf-8') as file:
#                     await file.write(content)
                
#                 # Verify write
#                 async with aiofiles.open(temp_path, 'r', encoding='utf-8') as file:
#                     written_content = await file.read()
#                     if written_content != content:
#                         raise IOError("Content mismatch during verification")
                
#                 # Atomic rename
#                 if os.path.exists(safe_path):
#                     os.replace(temp_path, safe_path)
#                 else:
#                     os.rename(temp_path, safe_path)
                
#                 return True
#             except Exception as e:
#                 if attempt == max_retries - 1:
#                     self.logger.error(f"Failed after {max_retries} attempts: {str(e)}")
#                     raise
#                 await asyncio.sleep(0.5 * (attempt + 1))
                
#     async def _verify_write(self, path: str, expected_content: str) -> bool:
#         """Verify file was written correctly"""
#         try:
#             actual_content = await self.read_file(path)
#             return actual_content == expected_content
#         except Exception:
#             return False
            
#     async def list_files(self, directory: str, pattern: Optional[str] = None) -> List[str]:
#         """List files in a directory asynchronously, optionally filtered by pattern."""
#         import glob
#         import asyncio
        
#         # Use sanitize_path for security
#         safe_directory = sanitize_path(directory)
        
#         # Run the file listing in a thread to avoid blocking
#         loop = asyncio.get_event_loop()
#         if pattern:
#             return await loop.run_in_executor(None, lambda: glob.glob(os.path.join(safe_directory, pattern)))
#         else:
#             def list_files_in_dir():
#                 return [os.path.join(safe_directory, f) for f in os.listdir(safe_directory) 
#                        if os.path.isfile(os.path.join(safe_directory, f))]
#             return await loop.run_in_executor(None, list_files_in_dir)
                   
#     async def ensure_directory(self, directory: str) -> bool:
#         """Ensure a directory exists asynchronously."""
#         safe_directory = sanitize_path(directory)
        
#         try:
#             os.makedirs(safe_directory, exist_ok=True)
#             return True
#         except Exception as e:
#             self.logger.error(f"Error creating directory {safe_directory}: {str(e)}")
#             raise
            
#     async def file_exists(self, file_path: str) -> bool:
#         """Check if a file exists asynchronously."""
#         import asyncio
        
#         # Use sanitize_path for security
#         safe_path = sanitize_path(file_path)
        
#         loop = asyncio.get_event_loop()
#         return await loop.run_in_executor(None, lambda: os.path.exists(safe_path) and os.path.isfile(safe_path))
    
#     async def get_file_info(self, file_path: str) -> Dict[str, Any]:
#         """Get information about a file asynchronously."""
#         import asyncio
        
#         # Use sanitize_path for security
#         safe_path = sanitize_path(file_path)
        
#         loop = asyncio.get_event_loop()
        
#         try:
#             exists = await self.file_exists(safe_path)
#             if not exists:
#                 return {"exists": False}
            
#             # Get file stats in a non-blocking way
#             stat_info = await loop.run_in_executor(None, os.stat, safe_path)
            
#             # Compute file hash
#             file_hash = await loop.run_in_executor(None, compute_file_hash, safe_path)
            
#             return {
#                 "exists": True,
#                 "size": stat_info.st_size,
#                 "modified": stat_info.st_mtime,
#                 "created": stat_info.st_ctime,
#                 "hash": file_hash
#             }
#         except Exception as e:
#             self.logger.error(f"Error getting file info for {safe_path}: {str(e)}")
#             return {"exists": False, "error": str(e)}


# core/file_manager.py
"""
File manager for the AI Coding Agent with async support
"""

import os
import aiofiles
from typing import List, Optional, Dict, Any, Union
from utils.helpers import compute_file_hash, normalize_line_endings # Removed sanitize_path import as Agent handles validation primarily
from utils.logger import get_logger
import asyncio
import json
import pathlib # Use pathlib for more robust path handling
import time

class FileManager:
    def __init__(self, working_directory="."):
        self.logger = get_logger(__name__)
        # Ensure working directory is absolute and exists
        self.working_directory = os.path.abspath(working_directory)
        self._ensure_working_dir()
        self.logger.info(f"FileManager initialized with working directory: {self.working_directory}")

    def _ensure_working_dir(self):
        """Ensure working directory exists"""
        try:
            # Use pathlib for potentially more robust directory creation
            pathlib.Path(self.working_directory).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self.logger.error(f"Error creating working directory '{self.working_directory}': {e}", exc_info=True)
            raise RuntimeError(f"Cannot create working directory: {e}") from e

    def _resolve_path(self, file_path: str) -> str:
        """
        Resolves a potentially relative file path against the working directory.
        Returns an absolute, normalized path.
        Security Note: Final check to ensure the path is within the working directory
        MUST be done by the calling code (Agent).
        """
        if not file_path or not file_path.strip():
            raise ValueError("File path cannot be empty or just whitespace.")

        # Clean the input path first (handle potential mixed separators, expand ~)
        cleaned_path_str = os.path.expanduser(str(pathlib.PurePath(file_path)))

        # Use os.path.join which handles separators correctly on the current OS
        # os.path.abspath ensures the result is absolute
        abs_path = os.path.abspath(os.path.join(self.working_directory, cleaned_path_str))

        # Although normpath is often implicitly handled by abspath/join, applying it ensures collapsed '..' etc.
        normalized_path = os.path.normpath(abs_path)

        # Basic check: Log if resolved path seems outside working dir - Agent enforces this.
        # Use os.path.commonpath (more reliable than startswith for edge cases)
        # common = os.path.commonpath([self.working_directory, normalized_path])
        # if common != self.working_directory:
        #      self.logger.warning(f"Resolved path '{normalized_path}' may be outside working directory '{self.working_directory}'. Agent must verify.")

        return normalized_path

    async def read_file(self, abs_safe_path: str) -> str:
        """Read file content asynchronously using a validated absolute path."""
        # Expects abs_safe_path to be ALREADY RESOLVED and VALIDATED by the Agent.
        self.logger.debug(f"Reading file: {abs_safe_path}")
        try:
            async with aiofiles.open(abs_safe_path, 'r', encoding='utf-8', errors='ignore') as file:
                return await file.read()
        except FileNotFoundError:
            self.logger.error(f"File not found during read: {abs_safe_path}")
            raise # Re-raise specific error
        except PermissionError:
             self.logger.error(f"Permission denied reading file: {abs_safe_path}")
             raise
        except Exception as e:
            self.logger.error(f"Error reading file {abs_safe_path}: {e}", exc_info=True)
            raise # Re-raise other errors

    async def write_file(self, abs_safe_path: str, content: Union[str, dict, list], max_retries: int = 3) -> bool:
        """Atomic file write using a validated absolute path, ensuring parent directories exist."""
        # Expects abs_safe_path to be ALREADY RESOLVED and VALIDATED by the Agent.
        self.logger.debug(f"Attempting to write file: {abs_safe_path}")

        content_str: str
        if isinstance(content, (dict, list)): # Handle JSON data
            try:
                content_str = json.dumps(content, indent=2) + "\n" # Add trailing newline for JSON
            except TypeError as e:
                 self.logger.error(f"Failed to serialize content to JSON for writing to {abs_safe_path}: {e}")
                 raise ValueError(f"Content for {abs_safe_path} is not JSON serializable.") from e
        elif isinstance(content, str):
             content_str = content
        else:
             content_str = str(content) # Convert other types to string
             self.logger.warning(f"Content for {abs_safe_path} was not string or JSON, converting to string.")

        # Optional: Normalize line endings (consider if this is desired)
        # content_str = normalize_line_endings(content_str)

        try:
            parent_dir = os.path.dirname(abs_safe_path)
            if parent_dir:
                pathlib.Path(parent_dir).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self.logger.error(f"Error creating parent directory for {abs_safe_path}: {e}", exc_info=True)
            raise IOError(f"Cannot create directory for file: {e}") from e

        # Atomic write using temporary file and rename/replace
        temp_path = f"{abs_safe_path}.{os.getpid()}.{int(time.time())}.tmp" # More unique temp name
        for attempt in range(max_retries):
            try:
                async with aiofiles.open(temp_path, 'w', encoding='utf-8') as file:
                    await file.write(content_str)

                # Verify write (optional, maybe only for critical files or based on config)
                # async with aiofiles.open(temp_path, 'r', encoding='utf-8') as file:
                #     written_content = await file.read()
                # if written_content != content_str: raise IOError("Content mismatch during verification")

                os.replace(temp_path, abs_safe_path) # Atomic replace/rename
                self.logger.info(f"Successfully wrote {len(content_str)} bytes to {abs_safe_path}")
                return True

            except Exception as e:
                self.logger.warning(f"Write attempt {attempt + 1} failed for {abs_safe_path}: {e}")
                if attempt == max_retries - 1:
                    self.logger.error(f"Failed to write file {abs_safe_path} after {max_retries} attempts: {e}", exc_info=True)
                    # Clean up temp file if write ultimately fails
                    if os.path.exists(temp_path):
                        try: os.remove(temp_path)
                        except OSError as rm_err: self.logger.error(f"Failed to remove temp file {temp_path}: {rm_err}")
                    raise IOError(f"Failed to write file after retries: {e}") from e # Raise specific error type
                await asyncio.sleep(0.1 * (attempt + 1)) # Small exponential backoff

        return False # Should only be reached if loop completes unexpectedly


    async def list_files(self, directory: str = ".", pattern: Optional[str] = None) -> List[str]:
        """
        List files relative to the working directory asynchronously.
        Args:
            directory (str): Subdirectory relative to working dir (e.g., ".", "src/components").
            pattern (Optional[str]): Glob pattern (e.g., "*.py", "**/*.js").
        Returns:
            List[str]: List of relative file paths.
        """
        try:
             abs_target_dir = self._resolve_path(directory)
             # Security Check
             if not abs_target_dir.startswith(os.path.abspath(self.working_directory)):
                 self.logger.error(f"Attempted to list files outside workspace: {abs_target_dir}")
                 raise ValueError("Cannot list files outside the working directory.")
        except ValueError as e:
             self.logger.error(f"Invalid directory for list_files: {e}")
             return []

        self.logger.debug(f"Listing files in: {abs_target_dir} (Pattern: {pattern})")
        target_path = pathlib.Path(abs_target_dir)
        results = []
        loop = asyncio.get_event_loop()

        try:
            def _perform_glob():
                if not target_path.is_dir(): return [] # Check if dir exists before globbing
                glob_pattern = pattern if pattern else "*" # Default to list all if no pattern
                # Use rglob for recursive if pattern suggests it, else glob
                glob_method = target_path.rglob if '**' in glob_pattern else target_path.glob
                try:
                     return [p for p in glob_method(glob_pattern) if p.is_file()]
                except Exception as glob_e:
                     self.logger.error(f"Error during glob operation in {abs_target_dir} with pattern '{pattern}': {glob_e}")
                     return []

            abs_paths = await loop.run_in_executor(None, _perform_glob)
            # Convert absolute paths back to relative paths based on the working directory
            results = [os.path.relpath(p, self.working_directory) for p in abs_paths]
            return results
        except Exception as e:
            self.logger.error(f"Error listing files in '{abs_target_dir}': {e}", exc_info=True)
            return []


    async def file_exists(self, abs_safe_path: str) -> bool:
        """Check if a file exists using a validated absolute path."""
        # Expects abs_safe_path to be ALREADY RESOLVED and VALIDATED by the Agent.
        loop = asyncio.get_event_loop()
        try:
            exists = await loop.run_in_executor(None, lambda: pathlib.Path(abs_safe_path).is_file())
            return exists
        except Exception as e:
            self.logger.error(f"Error checking file existence for {abs_safe_path}: {e}", exc_info=True)
            return False


    async def get_file_info(self, abs_safe_path: str) -> Optional[Dict[str, Any]]:
        """Get information about a file using a validated absolute path."""
         # Expects abs_safe_path to be ALREADY RESOLVED and VALIDATED by the Agent.
        loop = asyncio.get_event_loop()
        try:
            # Use run_in_executor for potentially blocking file system calls
            def _get_info():
                p = pathlib.Path(abs_safe_path)
                if not p.is_file(): return None # Check inside executor too

                stat_info = p.stat()
                try:
                     # Compute hash only if file exists and is readable
                     file_hash = compute_file_hash(abs_safe_path) # Assumes sync hash function
                except Exception as hash_e:
                     self.logger.warning(f"Could not compute hash for {abs_safe_path}: {hash_e}")
                     file_hash = None # Indicate hash computation failed

                return {
                    "exists": True,
                    "size": stat_info.st_size,
                    "modified": stat_info.st_mtime,
                    "created": stat_info.st_ctime,
                    "hash": file_hash,
                    "absolute_path": abs_safe_path,
                    "relative_path": os.path.relpath(abs_safe_path, self.working_directory)
                }

            info = await loop.run_in_executor(None, _get_info)
            return info # Returns None if file doesn't exist or stat fails

        except Exception as e:
            self.logger.error(f"Error getting file info for {abs_safe_path}: {e}", exc_info=True)
            return None # Return None on other errors