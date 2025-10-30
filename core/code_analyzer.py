# """
# Code analyzer for the AI Coding Agent with async support and Redis integration
# """
# import json
# import hashlib
# from typing import Dict, List, Any, Optional
# from adapters.llm_adapter import LLMAdapter
# from adapters.redis_adapter import RedisAdapter
# from config.prompts import PROMPTS
# from utils.schema import CodeAnalysis
# from utils.helpers import extract_language_from_path
# from utils.logger import get_logger
# import time

# class CodeAnalyzer:
#     def __init__(self, llm_adapter: LLMAdapter, redis_adapter: Optional[RedisAdapter] = None):
#         self.llm = llm_adapter
#         self.redis = redis_adapter
#         self.logger = get_logger(__name__)
        
#     async def analyze(self, code: str, file_path: str = None) -> CodeAnalysis:
#         """Analyze code with Redis caching and context"""
#         # Get language from file path
#         language = "unknown"
#         if file_path:
#             language = extract_language_from_path(file_path)
            
#         # Check Redis for cached analysis
#         cached_analysis = None
#         if self.redis and file_path:
#             file_metadata = await self.redis.get_file_metadata(file_path)
#             if file_metadata and 'analysis' in file_metadata:
#                 current_hash = hashlib.sha256(code.encode()).hexdigest()
#                 if file_metadata.get('hash') == current_hash:
#                     cached_analysis = file_metadata['analysis']
        
#         if cached_analysis:
#             self.logger.debug(f"Using cached analysis for {file_path}")
#             return CodeAnalysis(**cached_analysis)
        
#         # Get similar code analysis from Redis
#         similar_analysis = []
#         if self.redis:
#             similar_analysis = await self._find_similar_code_analysis(code, language)
        
#         prompt = PROMPTS["code_analyzer"]["analyze"].format(
#             code=code,
#             language=language,
#             similar_analysis=json.dumps(similar_analysis) if similar_analysis else ""
#         )
        
#         analysis_dict = await self.llm.generate(prompt, formated_output="json")
        
#         # Validate and convert to CodeAnalysis object
#         analysis = self._validate_analysis(analysis_dict, language)
        
#         # Store analysis in Redis if we have a file path
#         if self.redis and file_path:
#             await self._store_analysis_in_redis(file_path, code, analysis)
            
#         return analysis
    
#     async def _find_similar_code_analysis(self, code: str, language: str) -> List[Dict]:
#         """Find similar code analysis from Redis"""
#         if not self.redis:
#             return []
            
#         # Search by language
#         similar_files = await self.redis.search_context(f"language:{language}")
#         analyses = []
        
#         for file_key in similar_files:
#             file_metadata = await self.redis.get_file_metadata(file_key)
#             if file_metadata and 'analysis' in file_metadata:
#                 analyses.append(file_metadata['analysis'])
                
#         return analyses[:3]  # Return top 3 most similar
    
#     async def _store_analysis_in_redis(self, file_path: str, code: str, analysis: CodeAnalysis):
#         """Store analysis results in Redis with proper indexing"""
#         file_hash = hashlib.sha256(code.encode()).hexdigest()
        
#         # Convert analysis to serializable dict
#         analysis_dict = {
#             "language": analysis.language,
#             "imports": analysis.imports,
#             "functions": analysis.functions,
#             "classes": analysis.classes,
#             "main_flow": analysis.main_flow,
#             "issues": analysis.issues,
#             "uses_async": analysis.uses_async
#         }
        
#         # Store full file metadata
#         await self.redis.track_file(file_path, {
#             'analysis': analysis_dict,
#             'hash': file_hash,
#             'language': analysis.language,
#             'timestamp': int(time.time())
#         })
        
#         # Index by language for similarity search
#         await self.redis.store_context(
#             f"language:{analysis.language}:{file_path}",
#             {"path": file_path, "language": analysis.language}
#         )
        
#         # Store code snippet with analysis
#         snippet_hash = hashlib.sha256(code.encode()).hexdigest()
#         await self.redis.track_code_snippet(snippet_hash, {
#             'code': code,
#             'analysis': analysis_dict,
#             'file_path': file_path,
#             'language': analysis.language
#         })
    
#     def _validate_analysis(self, analysis_dict: Dict, language: str) -> CodeAnalysis:
#         """Validate and convert analysis dictionary to CodeAnalysis object"""
#         if not isinstance(analysis_dict, dict):
#             self.logger.warning("Invalid analysis format, returning default")
#             return CodeAnalysis(
#                 language=language,
#                 imports=[],
#                 functions=[],
#                 classes=[],
#                 main_flow="unknown",
#                 issues=["Invalid analysis format"],
#                 uses_async=False
#             )
        
#         # Ensure required fields with proper types
#         validated = {
#             "language": language,  # Use the detected language, not from analysis_dict
#             "imports": analysis_dict.get("imports") or [],
#             "functions": analysis_dict.get("functions") or [],
#             "classes": analysis_dict.get("classes") or [],
#             "main_flow": analysis_dict.get("main_flow", "unknown"),
#             "issues": analysis_dict.get("issues") or [],
#             "uses_async": analysis_dict.get("uses_async", False)
#         }
        
#         return CodeAnalysis(**validated)
    
#     async def compare_analysis(self, old_analysis: CodeAnalysis, new_analysis: CodeAnalysis) -> Dict:
#         """Compare two analyses and return differences"""
#         comparison = {
#             "added_imports": list(set(new_analysis.imports) - set(old_analysis.imports)),
#             "removed_imports": list(set(old_analysis.imports) - set(new_analysis.imports)),
#             "added_functions": [],
#             "removed_functions": [],
#             "changed_functions": [],
#             "structural_changes": False
#         }
        
#         # Compare functions
#         old_funcs = {f['name']: f for f in old_analysis.functions}
#         new_funcs = {f['name']: f for f in new_analysis.functions}
        
#         for name, func in new_funcs.items():
#             if name not in old_funcs:
#                 comparison["added_functions"].append(func)
#             elif func != old_funcs[name]:
#                 comparison["changed_functions"].append({
#                     "old": old_funcs[name],
#                     "new": func
#                 })
        
#         for name, func in old_funcs.items():
#             if name not in new_funcs:
#                 comparison["removed_functions"].append(func)
        
#         # Check for structural changes
#         comparison["structural_changes"] = (
#             len(comparison["added_imports"]) > 0 or
#             len(comparison["removed_imports"]) > 0 or
#             len(comparison["added_functions"]) > 0 or
#             len(comparison["removed_functions"]) > 0 or
#             len(comparison["changed_functions"]) > 0
#         )
        
#         return comparison



# core/code_analyzer.py
"""
Code analyzer for the AI Coding Agent with async support and Redis integration
"""
import json
import hashlib
from typing import Dict, List, Any, Optional
from adapters.llm_adapter import LLMAdapter
from adapters.redis_adapter import RedisAdapter
from config.prompts import PROMPTS
from utils.schema import CodeAnalysis # Ensure schema is imported
from utils.helpers import extract_language_from_path
from utils.logger import get_logger
import time
import os # Import os for path operations

class CodeAnalyzer:
    def __init__(self, llm_adapter: LLMAdapter, redis_adapter: Optional[RedisAdapter] = None):
        self.llm = llm_adapter
        self.redis = redis_adapter
        self.logger = get_logger(__name__)

    # **** UPDATED Method Signature ****
    async def analyze(self, code: str, file_path: Optional[str] = None, analysis_focus: str = "general") -> CodeAnalysis:
        """
        Analyze code with Redis caching, context, and specific focus.
        Args:
            code (str): The code content to analyze.
            file_path (Optional[str]): The relative path of the file for context (language detection, caching).
            analysis_focus (str): The specific focus for the analysis (e.g., 'general', 'dependencies').
        Returns:
            CodeAnalysis: Dataclass containing the analysis results.
        """
        language = "unknown"
        relative_file_path = file_path # Use the provided path directly (should be relative)

        if relative_file_path:
            language = extract_language_from_path(relative_file_path)

        # --- Caching Logic ---
        cached_analysis = None
        if self.redis and relative_file_path:
            # Cache key incorporates code hash and focus for more specific caching
            code_hash = hashlib.sha256(code.encode()).hexdigest()
            cache_key = f"analysis_cache:{relative_file_path}:{code_hash}:{analysis_focus}"
            try:
                 cached_data = await self.redis.get_context(cache_key)
                 if cached_data and isinstance(cached_data, dict):
                     self.logger.debug(f"Using cached analysis for {relative_file_path}, Focus: {analysis_focus}")
                     # Ensure the cached data can be used to create a CodeAnalysis object
                     try:
                         cached_analysis = CodeAnalysis(**cached_data)
                         return cached_analysis # Return cached result
                     except TypeError as te:
                          self.logger.warning(f"Cached analysis data mismatch for {cache_key}: {te}. Re-analyzing.")
                          cached_analysis = None # Invalidate cache if schema mismatch
            except Exception as e:
                 self.logger.error(f"Error retrieving cached analysis for {cache_key}: {e}")
                 cached_analysis = None # Proceed without cache on error

        # --- LLM Analysis ---
        self.logger.debug(f"Performing LLM analysis for {relative_file_path or 'code snippet'}, Focus: {analysis_focus}")
        prompt = PROMPTS["code_analyzer"]["analyze"].format(
            code=code,
            language=language,
            analysis_focus=analysis_focus,
        )

        analysis_dict_from_llm = await self.llm.generate(prompt, formated_output="json")

        # Handle potential LLM errors or invalid responses
        if isinstance(analysis_dict_from_llm, dict) and 'error' in analysis_dict_from_llm:
             self.logger.error(f"LLM analysis failed: {analysis_dict_from_llm['error']}")
             return CodeAnalysis(language=language, analysis_focus=analysis_focus, issues=[f"LLM Error: {analysis_dict_from_llm['error']}"]) # Return default error object
        elif not isinstance(analysis_dict_from_llm, dict):
             self.logger.error(f"LLM analysis returned unexpected type: {type(analysis_dict_from_llm)}")
             return CodeAnalysis(language=language, analysis_focus=analysis_focus, issues=["LLM returned non-dict response"]) # Return default error object

        # Validate and convert LLM response to CodeAnalysis object
        validated_analysis = self._validate_analysis(analysis_dict_from_llm, language, requested_focus=analysis_focus)

        # Store validated analysis in Redis if possible
        if self.redis and relative_file_path and cache_key:
            await self._store_analysis_in_redis(cache_key, relative_file_path, code, validated_analysis)

        return validated_analysis

    async def _store_analysis_in_redis(self, cache_key: str, file_path: str, code: str, analysis: CodeAnalysis):
        """Store analysis results in Redis with proper indexing using relative path."""
        if not self.redis: return
        try:
            analysis_dict = analysis.__dict__ # Convert dataclass to dict for storage
            # Store using the specific cache key (includes hash and focus)
            await self.redis.store_context(cache_key, analysis_dict, ttl=3600) # Cache for 1 hour example

            # Optionally, update general file metadata (without focus) if needed
            file_hash = hashlib.sha256(code.encode()).hexdigest()
            general_metadata = {
                'analysis': analysis_dict, # Store the latest analysis here
                'hash': file_hash,
                'language': analysis.language,
                'timestamp': int(time.time())
            }
            await self.redis.track_file(file_path, general_metadata) # Update general file tracking

            # Store code snippet (consider size implications)
            # snippet_hash = hashlib.sha256(code.encode()).hexdigest()
            # snippet_data = { ... }
            # await self.redis.track_code_snippet(snippet_hash, snippet_data)

            self.logger.debug(f"Stored analysis in Redis cache key {cache_key} for {file_path}")

        except Exception as e:
            self.logger.error(f"Failed to store analysis in Redis for {file_path}: {e}", exc_info=True)


    def _validate_analysis(self, analysis_dict: Dict, detected_language: str, requested_focus: str = "general") -> CodeAnalysis:
        """Validate and convert analysis dictionary to CodeAnalysis object."""
        if not isinstance(analysis_dict, dict):
            self.logger.warning(f"Invalid analysis format received (not a dict), returning default. Type: {type(analysis_dict)}")
            return CodeAnalysis(language=detected_language, analysis_focus=requested_focus, issues=["Invalid analysis format from LLM"])

        # Ensure required fields exist with proper types, using defaults from schema
        validated_data = {
            "language": analysis_dict.get("language", detected_language) or detected_language,
            "analysis_focus": analysis_dict.get("analysis_focus", requested_focus),
            "imports": analysis_dict.get("imports", []),
            "functions": analysis_dict.get("functions", []),
            "classes": analysis_dict.get("classes", []),
            "main_flow": analysis_dict.get("main_flow"), # Allow None
            "issues": analysis_dict.get("issues", []),
            "uses_async": bool(analysis_dict.get("uses_async", False)),
            "specific_focus_details": analysis_dict.get("specific_focus_details", {})
        }

        # Basic type validation (ensure lists/dicts are correct type, fallback to empty)
        if not isinstance(validated_data["imports"], list): validated_data["imports"] = []
        if not isinstance(validated_data["functions"], list): validated_data["functions"] = []
        if not isinstance(validated_data["classes"], list): validated_data["classes"] = []
        if not isinstance(validated_data["issues"], list): validated_data["issues"] = []
        if not isinstance(validated_data["specific_focus_details"], dict): validated_data["specific_focus_details"] = {}

        try:
            # Create the CodeAnalysis object using the validated dictionary
            return CodeAnalysis(**validated_data)
        except TypeError as te:
             self.logger.error(f"Schema mismatch when creating CodeAnalysis object: {te}. Data: {validated_data}", exc_info=True)
             # Fallback to default if schema mismatch, include error in issues
             return CodeAnalysis(
                 language=detected_language, analysis_focus=requested_focus,
                 issues=[f"Schema mismatch error: {te}"]
             )

    async def compare_analysis(self, old_analysis: CodeAnalysis, new_analysis: CodeAnalysis) -> Dict:
        """Compare two analyses and return differences (remains the same)."""
        # Logic from previous version is kept
        comparison = {
            "added_imports": list(set(new_analysis.imports) - set(old_analysis.imports)),
            "removed_imports": list(set(old_analysis.imports) - set(new_analysis.imports)),
            "added_functions": [],
            "removed_functions": [],
            "changed_functions": [],
            "structural_changes": False
        }
        old_funcs = {f.get('name'): f for f in old_analysis.functions if isinstance(f, dict)}
        new_funcs = {f.get('name'): f for f in new_analysis.functions if isinstance(f, dict)}
        for name, func in new_funcs.items():
            if name not in old_funcs: comparison["added_functions"].append(func)
            elif func != old_funcs.get(name): comparison["changed_functions"].append({"name": name,"old": old_funcs.get(name),"new": func})
        for name, func in old_funcs.items():
            if name not in new_funcs: comparison["removed_functions"].append(func)
        comparison["structural_changes"] = any([comparison["added_imports"], comparison["removed_imports"], comparison["added_functions"], comparison["removed_functions"], comparison["changed_functions"]])
        return comparison