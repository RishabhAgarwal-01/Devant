"""
Code analyzer for the AI Coding Agent with async support
"""
import os
from typing import Dict, List, Any
from adapters.llm_adapter import LLMAdapter
from config.prompts import PROMPTS
from utils.schema import CodeAnalysis  # Import schema class
from utils.helpers import extract_language_from_path  # Import helper function

class CodeAnalyzer:
    def __init__(self, llm_adapter: LLMAdapter):
        self.llm = llm_adapter
        
    async def analyze(self, code: str, file_path: str = None) -> CodeAnalysis:  # Updated return type and added parameter
        """Analyze code to extract structure, dependencies, and functions asynchronously."""
        # Use the helper to determine the language if a file path is provided
        language_hint = ""
        if file_path:
            language = extract_language_from_path(file_path)
            if language != "unknown":
                language_hint = f"\nNote: This appears to be {language} code based on the file extension."
        
        prompt = PROMPTS["code_analyzer"]["analyze"].format(code=code) + language_hint
        
        analysis_dict = await self.llm.generate(prompt, formated_output="json")
        
        # Validate the analysis
        if not isinstance(analysis_dict, dict):
            return CodeAnalysis(
                language="unknown",
                imports=[],
                functions=[],
                classes=[],
                main_flow="unknown",
                issues=["Invalid analysis format"],
                uses_async=False
            )
        
        # Convert dictionary to CodeAnalysis object
        return CodeAnalysis(
            language=analysis_dict.get("language", "unknown"),
            imports=analysis_dict.get("imports", []),
            functions=analysis_dict.get("functions", []),
            classes=analysis_dict.get("classes", []),
            main_flow=analysis_dict.get("main_flow", "unknown"),
            issues=analysis_dict.get("issues", []),
            uses_async=analysis_dict.get("uses_async", False)
        )