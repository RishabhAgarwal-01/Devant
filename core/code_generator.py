"""
Code generator for the AI Coding Agent with async support
"""
from typing import Dict, List, Optional, Any
from adapters.llm_adapter import LLMAdapter
from adapters.redis_adapter import RedisAdapter
from config.prompts import PROMPTS
from utils.helpers import format_code, extract_language_from_path
from utils.schema import CodeAnalysis
import json

class CodeGenerator:
    def __init__(self, llm_adapter: LLMAdapter, redis_adapter: Optional[RedisAdapter] = None):
        self.llm = llm_adapter
        self.redis = redis_adapter
        
    async def generate(self, requirements: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Generate code with enhanced context awareness"""
        # Get additional context from Redis if available
        redis_context = {}
        if self.redis and context and context.get("task_id"):
            # Get task context
            task_context = await self.redis.get_context(f"task:{context['task_id']}")
            if task_context:
                redis_context["task"] = task_context
            
            # Get similar code snippets
            if "file_path" in context:
                similar_snippets = await self.redis.get_related_snippets(context["file_path"])
                if similar_snippets:
                    redis_context["similar_code"] = similar_snippets
        
        full_context = {
            **(context or {}),
            **redis_context
        }
        
        prompt = PROMPTS["code_generator"]["generate"].format(
            requirements=requirements,
            context=json.dumps(full_context, indent=2) if full_context else "No additional context"
        )
        
        code = await self.llm.generate(prompt, formated_output="code")
        
        # Determine the language from context or requirements
        language = "unknown"
        if context and "file_path" in context:
            language = extract_language_from_path(context["file_path"])
        
        # Format the code according to language conventions
        return format_code(code, language)
    
    async def modify(self, existing_code: str, modifications: str, analysis: Optional[CodeAnalysis] = None, context: Optional[Dict[str, Any]] = None) -> str:
        """Modify existing code with full context awareness"""
        # Get additional context from Redis if available
        redis_context = {}
        if self.redis and isinstance(analysis, CodeAnalysis) and hasattr(analysis, "file_path"):
            # Get file history
            file_history = await self.redis.get_file_metadata(analysis.file_path)
            if file_history:
                redis_context["file_history"] = file_history
            
            # Get related snippets
            related_snippets = await self.redis.get_related_snippets(analysis.file_path)
            if related_snippets:
                redis_context["related_code"] = related_snippets
        
            # Now handle context here if available
        if context:
            redis_context.update(context)
        
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
                    "uses_async": analysis.uses_async,
                    **redis_context
                }
                analysis_str = f"Code Analysis: {json.dumps(analysis_dict, indent=2)}"
            else:
                analysis_str = f"Code Analysis: {analysis}"
        
        prompt = PROMPTS["code_generator"]["modify"].format(
            existing_code=existing_code,
            modifications=modifications,
            analysis=analysis_str,
            language=analysis.language if isinstance(analysis, CodeAnalysis) else "unknown",
            context=context if context else "No additional context"
        )
        
        modified_code = await self.llm.generate(prompt, formated_output="code")
        
        # Format the code according to language conventions
        language = "unknown"
        if analysis and hasattr(analysis, "language"):
            language = analysis.language
        
        return format_code(modified_code, language)