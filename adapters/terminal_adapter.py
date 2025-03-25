
"""
Terminal adapter for the AI Coding Agent with async support
"""
import asyncio
from typing import Dict, List, Optional, Any
from utils.logger import get_logger  # Updated import

class TerminalAdapter:
    def __init__(self):
        self.logger = get_logger(__name__)  # Updated logger retrieval
    
    async def execute(self, command: str, cwd: Optional[str] = None) -> Dict[str, Any]:
        """Execute a terminal command asynchronously and return the result."""
        self.logger.info(f"Executing terminal command: {command}")
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd
            )
            stdout, stderr = await process.communicate()
            
            # Convert bytes to string
            stdout_str = stdout.decode('utf-8', errors='replace')
            stderr_str = stderr.decode('utf-8', errors='replace')
            
            result = {
                "success": process.returncode == 0,
                "return_code": process.returncode,
                "stdout": stdout_str,
                "stderr": stderr_str
            }
            
            if process.returncode != 0:
                self.logger.warning(f"Command failed with return code {process.returncode}: {stderr_str}")
            
            return result
        except Exception as e:
            self.logger.error(f"Error executing command: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "stdout": "",
                "stderr": str(e)
            }