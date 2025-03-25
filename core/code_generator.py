"""
Code generator for the AI Coding Agent with async support
"""
from typing import Dict, List, Optional, Any
from adapters.llm_adapter import LLMAdapter
from config.prompts import PROMPTS
from utils.helpers import format_code, extract_language_from_path  # Import helper functions
from utils.schema import CodeAnalysis  # Import schema class

class CodeGenerator:
    def __init__(self, llm_adapter: LLMAdapter):
        self.llm = llm_adapter
        
    async def generate(self, requirements: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Generate code based on requirements and optional context asynchronously."""
        context_str = f"Context: {context}" if context else ""
        prompt = PROMPTS["code_generator"]["generate"].format(
            requirements=requirements,
            context=context_str
        )
        
        code = await self.llm.generate(prompt, formated_output="code")
        
        # Determine the language from context or requirements
        language = "unknown"
        if context and "file_path" in context:
            language = extract_language_from_path(context["file_path"])
        
        # Format the code according to language conventions
        return format_code(code, language)
    
    async def modify(self, existing_code: str, modifications: str, analysis: Optional[CodeAnalysis] = None) -> str:
        """Modify existing code based on required modifications and optional analysis asynchronously."""
        # Convert CodeAnalysis object to dictionary if needed
        analysis_str = ""
        if analysis:
            if isinstance(analysis, CodeAnalysis):
                analysis_dict = {
                    "language": analysis.language,
                    "imports": analysis.imports,
                    "functions": analysis.functions,
                    "classes": analysis.classes,
                    "main_flow": analysis.main_flow,
                    "issues": analysis.issues,
                    "uses_async": analysis.uses_async
                }
                analysis_str = f"Code Analysis: {analysis_dict}"
            else:
                analysis_str = f"Code Analysis: {analysis}"
        
        prompt = PROMPTS["code_generator"]["modify"].format(
            existing_code=existing_code,
            modifications=modifications,
            analysis=analysis_str
        )
        
        modified_code = await self.llm.generate(prompt, formated_output="code")
        
        # Format the code according to language conventions
        language = "unknown"
        if analysis and hasattr(analysis, "language"):
            language = analysis.language
        
        return format_code(modified_code, language)