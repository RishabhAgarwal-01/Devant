# """
# Agent orchestrator for the AI Coding Agent with async support
# Enhanced Agent with autonomous capabilities
# """
# import logging
# import asyncio
# from typing import Dict, List, Optional, Any
# import os
# from core.planner import Planner
# from core.code_generator import CodeGenerator
# from core.code_analyzer import CodeAnalyzer
# from core.file_manager import FileManager
# from core.dependency_manager import DependencyManager
# from core.improvement_engine import ImprovementEngine
# from adapters.terminal_adapter import TerminalAdapter
# from adapters.llm_adapter import LLMAdapter
# from adapters.redis_adapter import RedisAdapter
# from utils.schema import Plan, Step, StepResult, CodeAnalysis
# from utils.helpers import save_json, compute_file_hash, extract_language_from_path
# from utils.ast_parser import ASTParser
# import hashlib
# import time
# import json

# class Agent:
#     def __init__(self, config: Dict[str, Any]):
#         self.logger = logging.getLogger(__name__)
#         self.config = config
        
#         # Initialize adapters
#         self.llm = LLMAdapter(config["llm"])
#         self.terminal = TerminalAdapter()
#         self.redis = RedisAdapter(config.get("redis", {"host": "localhost", "port": 6379}))
        
#         # Initialize core components
#         self.working_directory = config.get("working_directory", ".")
#         self.planner = Planner(self.llm)
#         self.code_generator = CodeGenerator(self.llm)
#         self.code_analyzer = CodeAnalyzer(self.llm)
#         self.file_manager = FileManager(self.working_directory)
#         self.dependency_manager = DependencyManager()
#         self.improvement_engine = ImprovementEngine(self.llm)
#         self.ast_parser = ASTParser()
        
#         # Current state
#         self.current_task = None
#         self.current_plan = None
#         self.execution_state = {}
#         self.task_id = None
        
#         # Concurrency settings
#         self.max_workers = config.get("concurrency", {}).get("max_workers", 5)
#         self.semaphore = asyncio.Semaphore(self.max_workers)
    
#     def _generate_task_id(self, task_description: str) -> str:
#         """Generate a unique task ID based on the task description"""
#         return hashlib.sha256(task_description.encode()).hexdigest()
    
#     async def _store_context(self, key: str, data: Dict) -> bool:
#         """Store context data in Redis with proper namespacing"""
#         return await self.redis.store_context(f"task:{self.task_id}:{key}", data)
    
#     async def _get_context(self, key: str) -> Optional[Dict]:
#         """Retrieve context data from Redis with proper namespacing"""
#         return await self.redis.get_context(f"task:{self.task_id}:{key}")
    
#     async def _store_execution_state(self) -> bool:
#         try:
#             state = {
#                 "task": self.current_task,
#                 "execution_state": self.execution_state,
#                 "generated_files": self.execution_state.get("generated_files", []),
#                 "completed_steps": self.execution_state.get("completed_steps", [])
#             }
            
#             if self.current_plan:
#                 state["plan"] = {
#                     "understanding": getattr(self.current_plan, "understanding", ""),
#                     "files": getattr(self.current_plan, "files", []),
#                     "steps": [step.to_dict() if hasattr(step, "to_dict") else step 
#                             for step in getattr(self.current_plan, "steps", [])]
#                 }
            
#             return await self.redis.store_execution_state(self.task_id, state)
#         except Exception as e:
#             self.logger.error(f"State storage failed: {str(e)}")
#             return False
    
#     async def _load_execution_state(self) -> bool:
#         """Load execution state from Redis with proper deserialization"""
#         state = await self.redis.get_execution_state(self.task_id)
#         if state:
#             try:
#                 self.current_task = state.get("task")
#                 if state.get("plan"):
#                     plan_data = state["plan"]
#                     steps = []
#                     for step_data in plan_data.get("steps", []):
#                         try:
#                             steps.append(Step(**step_data))
#                         except Exception as e:
#                             self.logger.warning(f"Invalid step format in saved state: {str(e)}")
#                             continue
                            
#                     self.current_plan = Plan(
#                         understanding=plan_data.get("understanding", ""),
#                         files=plan_data.get("files", []),
#                         steps=steps
#                     )
#                 self.execution_state = state.get("execution_state", {})
#                 return True
#             except Exception as e:
#                 self.logger.error(f"Error loading execution state: {str(e)}")
#         return False
    
#     async def _validate_step(self, step: Step) -> Optional[StepResult]:
#         """Validate a step before execution"""
#         if not step.type:
#             return StepResult(
#                 status="failed",
#                 error="Step type is missing",
#                 note="Every step must have a type"
#             )
            
#         if step.type not in ["code_generation", "code_modification", "terminal_command"]:
#             return StepResult(
#                 status="failed",
#                 error=f"Invalid step type: {step.type}",
#                 note="Step type must be code_generation, code_modification, or terminal_command"
#             )
            
#         if step.type in ["code_generation", "code_modification"]:
#             if not step.file_path:
#                 return StepResult(
#                     status="failed",
#                     error="File path is required",
#                     note=f"{step.type} steps require a file_path"
#                 )
#             if not step.requirements:
#                 return StepResult(
#                     status="failed",
#                     error="Requirements are required",
#                     note=f"{step.type} steps require requirements"
#                 )
                
#         if step.type == "terminal_command" and not step.command:
#             return StepResult(
#                 status="failed",
#                 error="Command is required",
#                 note="terminal_command steps require a command"
#             )
            
#         return None

#     async def set_task(self, task_description: str):
#         """Set the current task and initialize context"""
#         self.current_task = task_description
#         self.task_id = self._generate_task_id(task_description)
        
#         # Try to load existing state
#         if not await self._load_execution_state():
#             # Initialize new state
#             self.execution_state = {
#                 "current_step": 0,
#                 "completed_steps": [],
#                 "generated_files": [],
#                 "execution_results": {}
#             }
#             await self._store_execution_state()
    
#     async def _analyze_and_refine(self, file_path: str) -> bool:
#         """Analyze and refine a file in an improvement loop"""
#         try:
#             code = await self.file_manager.read_file(file_path)
#             analysis = await self.code_analyzer.analyze(code, file_path)
            
#             # Store analysis in Redis
#             await self.redis.track_file(file_path, {
#                 "analysis": analysis.__dict__,
#                 "hash": compute_file_hash(file_path)
#             })
            
#             metrics = await self.improvement_engine.analyze_code_quality(code, analysis)
            
#             improvement_count = 0
#             max_iterations = 3
            
#             while await self.improvement_engine.needs_improvement(metrics) and improvement_count < max_iterations:
#                 improvement_plan = await self.improvement_engine.generate_improvement_plan(code, analysis, metrics)
                
#                 # Store improvement context
#                 await self._store_context(f"improve:{file_path}:{improvement_count}", {
#                     "metrics": metrics.__dict__,
#                     "plan": improvement_plan
#                 })
                
#                 # Get full context from Redis
#                 context = {
#                     "file_path": file_path,
#                     "analysis": analysis.__dict__,
#                     "metrics": metrics.__dict__,
#                     "improvement_plan": improvement_plan,
#                     "task": self.current_task
#                 }
                
#                 refined_code = await self.improvement_engine.refine_code(code, improvement_plan, context)
#                 await self.file_manager.write_file(file_path, refined_code)
                
#                 # Update state
#                 code = refined_code
#                 analysis = await self.code_analyzer.analyze(code, file_path)
#                 metrics = await self.improvement_engine.analyze_code_quality(code, analysis)
#                 improvement_count += 1
                
#                 self.logger.info(f"Improvement iteration {improvement_count} for {file_path}")
                
#             return improvement_count > 0
#         except Exception as e:
#             self.logger.error(f"Error during analysis and refinement of {file_path}: {str(e)}")
#             return False
            
#     async def _update_dependencies(self, file_path: str):
#         """Update dependency graph for a file with Redis tracking"""
#         try:
#             code = await self.file_manager.read_file(file_path)
#             language = extract_language_from_path(file_path)
            
#             if language != "unknown":
#                 dependencies = self.ast_parser.find_dependencies(code, language)
#                 self.dependency_manager.add_file(file_path, dependencies)
                
#                 # Store comprehensive file metadata in Redis
#                 file_info = {
#                     "path": file_path,
#                     "language": language,
#                     "dependencies": dependencies,
#                     "functions": self.ast_parser.extract_functions(code, language),
#                     "hash": compute_file_hash(file_path),
#                     "task_id": self.task_id
#                 }
#                 await self.redis.track_file(file_path, file_info)
                
#                 # Store snippet context
#                 snippet_hash = hashlib.sha256(code.encode()).hexdigest()
#                 await self.redis.track_code_snippet(snippet_hash, {
#                     "code": code,
#                     "file_path": file_path,
#                     "language": language,
#                     "dependencies": dependencies
#                 })
#         except Exception as e:
#             self.logger.error(f"Error updating dependencies for {file_path}: {str(e)}")
            
#     async def execute_step(self, step_idx: int, step: Step) -> StepResult:
#         """Enhanced step execution with context awareness"""
#         async with self.semaphore:
#             self.logger.info(f"Executing step {step_idx+1}: {step.description}")
            
#             try:
#                 # Validate step first
#                 validation_result = await self._validate_step(step)
#                 if validation_result:
#                     return validation_result
                
#                 # Validate file_path exists for file operations
#                 if step.type in ["code_generation", "code_modification"] and not step.file_path:
#                     return StepResult(
#                         status="failed",
#                         error="Missing file_path",
#                         note=f"{step.type} requires file_path"
#                     )
                
#                 # Ensure working directory exists
#                 await self.file_manager.ensure_directory(self.working_directory)
                    
#                 # Convert step to dict using to_dict() if available
#                 step_dict = step.to_dict() if hasattr(step, 'to_dict') else {
#                     "type": step.type,
#                     "description": step.description,
#                     "file_path": step.file_path,
#                     "requirements": step.requirements,
#                     "command": step.command,
#                     "params": step.params
#                 }
                
#                 await self._store_context(f"step:{step_idx}", {
#                     "step": step_dict,
#                     "status": "started"
#                 })

#                 if step.type == "code_generation":
#                     file_path = os.path.normpath(step.file_path)

#                     # Ensure directory exists first
#                     try:
#                         os.makedirs(os.path.dirname(file_path), exist_ok=True)
#                     except Exception as e:
#                         return StepResult(
#                             status="failed",
#                             error=f"Could not create directory: {str(e)}"
#                         )
                    
#                     # Check Redis for existing version
#                     file_info = await self.redis.get_file_metadata(file_path)
#                     if file_info and await self.file_manager.file_exists(file_path):
#                         current_hash = compute_file_hash(file_path)
#                         if file_info.get("hash") == current_hash:
#                             self.logger.info(f"Skipping generation - file exists and is current: {file_path}")
#                             return StepResult(status="skipped", note="File already exists and is current")
                    
#                     # Get context from Redis with proper serialization
#                     context = await self._get_context(f"step:{step_idx}") or {}
#                     context.update({
#                         "task": self.current_task,
#                         "plan": {
#                             "understanding": self.current_plan.understanding if self.current_plan else None,
#                             "files": self.current_plan.files if self.current_plan else None
#                         }
#                     })
                    
#                     code = await self.code_generator.generate(step.requirements, context)
#                     success = await self.file_manager.write_file(file_path, code)
#                     if not success:
#                         return StepResult(
#                             status="failed",
#                             error="File write failed"
#                         )
                    
#                     # Update state
#                     await self._update_dependencies(file_path)
#                     await self._analyze_and_refine(file_path)
                    
#                     # Track generated file
#                     self.execution_state["generated_files"].append(file_path)
#                     await self._store_execution_state()
                    
#                     file_hash = compute_file_hash(file_path)
#                     return StepResult(status="completed", file=file_path, result={"file_hash": file_hash})
                    
#                 elif step.type == "code_modification":
#                     file_path = step.file_path
                    
#                     if not await self.file_manager.file_exists(file_path):
#                         self.logger.warning(f"File not found for modification: {file_path}")
#                         return StepResult(status="failed", error=f"File not found: {file_path}")
                    
#                     current_code = await self.file_manager.read_file(file_path)
#                     analysis = await self.code_analyzer.analyze(current_code, file_path)
                    
#                     # Get context from Redis with proper serialization
#                     context = await self._get_context(f"step:{step_idx}") or {}
#                     context.update({
#                         "existing_code": current_code,
#                         "analysis": {
#                             "language": analysis.language,
#                             "imports": analysis.imports,
#                             "functions": analysis.functions,
#                             "classes": analysis.classes,
#                             "main_flow": analysis.main_flow,
#                             "issues": analysis.issues,
#                             "uses_async": analysis.uses_async
#                         },
#                         "task": self.current_task
#                     })
                    
#                     modified_code = await self.code_generator.modify(current_code, step.requirements, analysis)
#                     await self.file_manager.write_file(file_path, modified_code)
                    
#                     # Update state
#                     await self._update_dependencies(file_path)
#                     await self._analyze_and_refine(file_path)
#                     await self._store_execution_state()
                    
#                     file_hash = compute_file_hash(file_path)
#                     return StepResult(status="completed", file=file_path, result={"file_hash": file_hash})
                    
#                 elif step.type == "terminal_command":
#                     command = step.command
#                     output_dict = await self.terminal.execute(command, cwd=self.working_directory)
                    
#                     # Store command output in Redis
#                     await self._store_context(f"command:{step_idx}", {
#                         "command": command,
#                         "output": {
#                             "success": output_dict.get("success"),
#                             "return_code": output_dict.get("return_code"),
#                             "stdout": output_dict.get("stdout"),
#                             "stderr": output_dict.get("stderr")
#                         }
#                     })
                    
#                     return StepResult(status="completed", output=output_dict.get("stdout", ""))
                    
#                 else:
#                     self.logger.warning(f"Unknown step type: {step.type}")
#                     return StepResult(status="skipped", note=f"Unknown step type: {step.type}")
                    
#             except Exception as e:
#                 self.logger.error(f"Error executing step {step_idx+1}: {str(e)}", exc_info=True)
#                 return StepResult(
#                     status="failed",
#                     error=str(e),
#                     note=f"Step failed with error: {str(e)}"
#                 )
#             finally:
#                 # Update step completion status
#                 self.execution_state["current_step"] = step_idx + 1
#                 self.execution_state["completed_steps"].append(step_idx)
#                 await self._store_execution_state()
                
#     async def execute_plan(self, plan: Plan) -> Dict[int, StepResult]:
#         """Execute a plan with proper context tracking"""
#         self.current_plan = plan
#         results = {}
        
#         # Store initial plan in Redis
#         await self._store_context("initial_plan", plan.__dict__)
        
#         for i, step in enumerate(plan.steps):
#             if i in self.execution_state["completed_steps"]:
#                 self.logger.info(f"Skipping already completed step {i+1}")
#                 continue
                
#             result = await self.execute_step(i, step)
#             results[i] = result.__dict__
            
#             # Store step result in execution state
#             self.execution_state["execution_results"][str(i)] = result.__dict__
#             await self._store_execution_state()
            
#             if result.status == "failed":
#                 self.logger.warning(f"Step {i+1} failed, stopping execution")
#                 break
                
#         return results
        
#     async def refine_plan(self, current_results: Dict[str, Any]) -> Plan:
#         """Refine the plan based on execution results with full context"""
#         # Get all relevant context from Redis
#         task_context = await self._get_context("task")
#         initial_plan = await self._get_context("initial_plan")
#         step_contexts = {}
        
#         for step_idx in range(len(self.current_plan.steps)):
#             ctx = await self._get_context(f"step:{step_idx}")
#             if ctx:
#                 step_contexts[step_idx] = ctx
                
#         prompt = f"""
#         Task Context:
#         {task_context}
        
#         Initial Plan:
#         {initial_plan}
        
#         Step Execution Contexts:
#         {step_contexts}
        
#         Execution Results:
#         {current_results}
        
#         Please refine the plan based on these results. Consider:
#         - Adding new steps for uncovered functionality
#         - Removing redundant or failed steps
#         - Reordering steps based on dependencies
#         - Adding validation steps
        
#         Return the refined plan in the same JSON format with these required fields:
#         - understanding: string
#         - files: list of strings
#         - steps: list of step objects with type, description, etc.
#         """
        
#         refined_plan_dict = await self.llm.generate(prompt, formated_output="json")
        
#         # Validate the response contains required fields
#         if not isinstance(refined_plan_dict, dict):
#             refined_plan_dict = {}
        
#         # Ensure required fields exist with defaults
#         refined_plan_dict.setdefault("understanding", "No understanding provided")
#         refined_plan_dict.setdefault("files", [])
#         refined_plan_dict.setdefault("steps", [])
        
#         # Convert the refined plan dictionary back to a Plan object
#         steps = []
#         for step_data in refined_plan_dict["steps"]:
#             try:
#                 steps.append(Step(**step_data))
#             except Exception as e:
#                 self.logger.error(f"Invalid step format: {str(e)}")
#                 continue
                
#         refined_plan = Plan(
#             understanding=refined_plan_dict["understanding"],
#             files=refined_plan_dict["files"],
#             steps=steps
#         )
        
#         # Store refined plan in Redis
#         await self._store_context("refined_plan", refined_plan.__dict__)
#         return refined_plan
        
#     async def run_autonomous_loop(self, task_description: str, max_iterations: int = 3) -> Dict[str, Any]:
#         """Run the autonomous improvement loop with full context tracking"""
#         await self.set_task(task_description)
        
#         iteration = 0
#         overall_results = {}
        
#         while iteration < max_iterations:
#             self.logger.info(f"Starting autonomous iteration {iteration + 1}")
            
#             # Create or refine plan
#             if iteration == 0:
#                 self.current_plan = await self.planner.create_plan(task_description)
#                 # Store initial context
#                 await self._store_context("task", {
#                     "description": task_description,
#                     "iteration": iteration
#                 })
#             else:
#                 self.current_plan = await self.refine_plan(overall_results)
            
#             # Execute plan
#             iteration_results = await self.execute_plan(self.current_plan)
#             overall_results[f"iteration_{iteration + 1}"] = iteration_results
            
#             # Check if we should continue
#             all_completed = all(
#                 result.get("status") == "completed"
#                 for result in iteration_results.values()
#             )
            
#             if all_completed:
#                 self.logger.info("All steps completed successfully")
#                 break
                
#             iteration += 1
            
#         # Final improvement pass on all files
#         for file_path in self.current_plan.files:
#             if await self.file_manager.file_exists(file_path):
#                 await self._analyze_and_refine(file_path)
                
#         # Store final results
#         await self._store_context("final_results", overall_results)
#         return overall_results
        
#     async def run(self, task_description: str) -> Dict[str, Any]:
#         """Main entry point that runs the autonomous loop with context"""
#         return await self.run_autonomous_loop(task_description)





# import logging
# import asyncio
# from typing import Dict, List, Optional, Any
# import os
# import hashlib
# import time
# import json

# # Assuming components are in respective directories relative to project root
# # These imports should work if main.py setup sys.path correctly
# try:
#     from core.planner import Planner
#     from core.code_generator import CodeGenerator
#     from core.code_analyzer import CodeAnalyzer
#     from core.file_manager import FileManager
#     from core.dependency_manager import DependencyManager
#     from core.improvement_engine import ImprovementEngine
#     from adapters.terminal_adapter import TerminalAdapter
#     from adapters.llm_adapter import LLMAdapter
#     from adapters.redis_adapter import RedisAdapter # Assuming Redis is still used for state/cache
#     from utils.schema import Plan, Step, StepResult, CodeAnalysis
#     from utils.helpers import save_json, compute_file_hash, extract_language_from_path, sanitize_path
#     from utils.ast_parser import ASTParser
#     from utils.cli_ui import CLI_UI # Import the UI class
# except ImportError as e:
#      # This might happen if agent.py is run directly or path setup failed
#      print(f"Agent Import Error: {e}. Ensure main.py is setting up sys.path correctly.")
#      raise # Re-raise the error to prevent execution with missing modules


# class Agent:
#     def __init__(self, config: Dict[str, Any], cli_ui: CLI_UI): # Accept CLI_UI instance
#         self.logger = logging.getLogger(__name__)
#         self.config = config
#         self.cli_ui = cli_ui # Store the UI instance

#         # --- Adapter Initialization ---
#         try:
#             self.llm = LLMAdapter(config["llm"])
#         except KeyError as e:
#             self.logger.error(f"LLM configuration missing key: {e}")
#             raise ValueError(f"LLM configuration missing key: {e}") from e
#         except Exception as e:
#              self.logger.error(f"Failed to initialize LLMAdapter: {e}", exc_info=True)
#              raise RuntimeError(f"Failed to initialize LLMAdapter: {e}") from e

#         self.terminal = TerminalAdapter()

#         # Conditionally initialize Redis if configured
#         self.redis = None
#         if config.get("redis"):
#             try:
#                 self.redis = RedisAdapter(config["redis"])
#                 self.logger.info("Redis adapter initialized.")
#             except Exception as e:
#                 self.logger.warning(f"Failed to initialize Redis adapter: {e}. Proceeding without Redis.")
#                 self.cli_ui.print_warning("Could not connect to Redis. State and caching will be limited.")
#         else:
#              self.logger.info("Redis not configured. State and caching will be limited.")


#         # --- Core Component Initialization ---
#         self.working_directory = config.get("working_directory") # Should be absolute path from main.py
#         if not os.path.isabs(self.working_directory):
#              self.logger.warning(f"Working directory '{self.working_directory}' might not be absolute. Ensure it's correctly resolved in main.py.")
#         os.makedirs(self.working_directory, exist_ok=True) # Ensure it exists

#         try:
#             self.planner = Planner(self.llm, self.redis) # Pass redis if available
#             self.code_generator = CodeGenerator(self.llm, self.redis)
#             self.code_analyzer = CodeAnalyzer(self.llm, self.redis)
#             self.file_manager = FileManager(self.working_directory)
#             self.dependency_manager = DependencyManager(self.redis) # Pass redis if available
#             self.improvement_engine = ImprovementEngine(self.llm, self.redis)
#         except Exception as e:
#              self.logger.error(f"Failed to initialize core components: {e}", exc_info=True)
#              raise RuntimeError(f"Failed to initialize core components: {e}") from e

#         # Initialize AST Parser (optional)
#         self.ast_parser = None
#         try:
#             self.ast_parser = ASTParser()
#             self.logger.info("AST Parser initialized.")
#         except FileNotFoundError as e:
#              self.logger.warning(f"AST Parser library not found: {e}. Code analysis features will be limited.")
#              self.cli_ui.print_warning(f"AST Parser library not found: {e}. Code analysis features will be limited.")
#         except Exception as e:
#              self.logger.error(f"Unexpected AST Parser Error: {e}. Code analysis features will be limited.", exc_info=True)
#              self.cli_ui.print_error(f"Unexpected AST Parser Error: {e}. Code analysis features will be limited.")


#         # --- Agent State ---
#         self.current_task: Optional[str] = None
#         self.current_plan: Optional[Plan] = None
#         self.task_id: Optional[str] = None
#         self.execution_results: Dict[int, StepResult] = {} # Store results per task run

#         # Concurrency settings
#         self.max_workers = config.get("concurrency", {}).get("max_workers", 5)
#         self.semaphore = asyncio.Semaphore(self.max_workers)
#         self.logger.debug(f"Agent initialized with max_workers={self.max_workers}")

#     def _generate_task_id(self, task_description: str) -> str:
#         """Generate a unique task ID based on the task description and timestamp"""
#         timestamp = str(time.time())
#         # Use a shorter, potentially more readable ID if preferred
#         return hashlib.sha256((task_description + timestamp).encode()).hexdigest()[:16]

#     # --- Redis Context/State Management ---
#     async def _store_context(self, key: str, data: Any) -> bool:
#         """Store context data in Redis (if Redis enabled). Handles serialization."""
#         if not self.redis or not self.task_id:
#             return False
#         full_key = f"task:{self.task_id}:{key}"
#         try:
#             # Basic serialization check - extend if needed
#             if isinstance(data, (dict, list, str, int, float, bool, type(None))):
#                 await self.redis.store_context(full_key, data)
#                 self.logger.debug(f"Stored context in Redis: {full_key}")
#                 return True
#             else:
#                 # Attempt to serialize complex objects if needed (e.g., dataclasses)
#                 # This might require a custom serializer in RedisAdapter or here
#                 self.logger.warning(f"Cannot directly store type {type(data)} in Redis context for key {full_key}. Skipping.")
#                 return False
#         except Exception as e:
#             self.logger.error(f"Redis store_context failed for key '{full_key}': {e}")
#             return False

#     async def _get_context(self, key: str) -> Optional[Any]:
#         """Retrieve context data from Redis (if Redis enabled)."""
#         if not self.redis or not self.task_id:
#             return None
#         full_key = f"task:{self.task_id}:{key}"
#         try:
#             data = await self.redis.get_context(full_key)
#             self.logger.debug(f"Retrieved context from Redis: {full_key} (Found: {data is not None})")
#             return data
#         except Exception as e:
#             self.logger.error(f"Redis get_context failed for key '{full_key}': {e}")
#             return None

#     # --- Interactive Execution Logic ---

#     async def set_task(self, task_description: str):
#         """Set the current task and generate a new task ID."""
#         self.current_task = task_description
#         self.task_id = self._generate_task_id(task_description)
#         self.current_plan = None # Reset plan for new task
#         self.execution_results = {} # Reset results
#         self.logger.info(f"Set new task (ID: {self.task_id}): {task_description[:50]}...")
#         # Store initial task info in context if Redis is enabled
#         await self._store_context("task_description", {"description": self.current_task})

#     async def _validate_step(self, step: Step) -> Optional[StepResult]:
#         """Validate a step before execution."""
#         if not hasattr(step, 'type') or not step.type:
#             return StepResult(status="failed", error="Step object missing 'type' attribute or type is empty")
#         valid_types = ["code_generation", "code_modification", "terminal_command"]
#         if step.type not in valid_types:
#             return StepResult(status="failed", error=f"Invalid step type: '{step.type}'. Valid types: {valid_types}")
#         if step.type in ["code_generation", "code_modification"]:
#             if not hasattr(step, 'file_path') or not step.file_path:
#                 return StepResult(status="failed", error=f"'{step.type}' step requires a 'file_path'")
#             # Requirements are crucial for generation/modification logic
#             if not hasattr(step, 'requirements') or not step.requirements:
#                  self.logger.warning(f"Step '{step.description}' ({step.type}) has no requirements. LLM might lack specific instructions.")
#                 # Allow proceeding but log a warning - maybe context is enough
#                 # return StepResult(status="failed", error=f"'{step.type}' step requires 'requirements'")
#         if step.type == "terminal_command":
#              if not hasattr(step, 'command') or not step.command:
#                 return StepResult(status="failed", error="'terminal_command' step requires a 'command'")
#         return None # Step is valid

#     async def _update_dependencies_and_analyze(self, file_path: str, code: Optional[str] = None) -> tuple[Optional[CodeAnalysis], List[str]]:
#         """Helper to update dependencies and perform basic analysis after file change."""
#         # Ensure file_path is absolute for consistency
#         abs_file_path = os.path.abspath(os.path.join(self.working_directory, file_path))

#         if not self.ast_parser:
#              self.logger.warning("AST Parser not available, skipping dependency update and analysis.")
#              return None, [] # Indicate analysis didn't run, no dependencies found

#         analysis: Optional[CodeAnalysis] = None
#         dependencies: List[str] = []

#         try:
#             if code is None:
#                 if not await self.file_manager.file_exists(abs_file_path):
#                      self.logger.warning(f"File not found for analysis: {abs_file_path}")
#                      return None, []
#                 code = await self.file_manager.read_file(abs_file_path) # Read the absolute path

#             language = extract_language_from_path(abs_file_path) # Analyze based on path

#             if language != "unknown":
#                 # --- Update Dependency Graph ---
#                 # Use relative path for dependency graph keys if preferred, but be consistent
#                 relative_path = os.path.relpath(abs_file_path, self.working_directory)
#                 try:
#                     dependencies = self.ast_parser.find_dependencies(code, language)
#                     # Store dependencies relative to the project structure if needed
#                     # For simplicity, using relative path from working dir as key
#                     self.dependency_manager.add_file(relative_path, dependencies)
#                     self.logger.debug(f"Updated dependencies for {relative_path}: {dependencies}")
#                     # Display dependency info using the UI
#                     dependents = self.dependency_manager.get_dependents(relative_path)
#                     self.cli_ui.display_dependencies(relative_path, dependencies, dependents)
#                 except Exception as e:
#                      self.logger.error(f"ASTParser failed to find dependencies for {relative_path}: {e}", exc_info=True)
#                      # Continue without dependency info

#                 # --- Perform Code Analysis ---
#                 try:
#                     analysis = await self.code_analyzer.analyze(code, relative_path) # Pass relative path for context
#                     self.logger.debug(f"Performed analysis for {relative_path}")
#                     # Display analysis summary using the UI
#                     self.cli_ui.display_analysis_summary(analysis)
#                 except Exception as e:
#                      self.logger.error(f"CodeAnalyzer failed for {relative_path}: {e}", exc_info=True)
#                      # Continue without analysis info


#                 # --- Store analysis/metadata in Redis if enabled ---
#                 if self.redis:
#                     try:
#                         file_info = {
#                             "path": relative_path, # Store relative path
#                             "language": language,
#                             "dependencies": dependencies,
#                             "functions": analysis.functions if analysis else [],
#                             "classes": analysis.classes if analysis else [],
#                             "hash": compute_file_hash(abs_file_path), # Compute hash from absolute path
#                             "task_id": self.task_id,
#                             "analysis": analysis.__dict__ if analysis else None,
#                             "timestamp": time.time()
#                         }
#                         await self.redis.track_file(relative_path, file_info) # Use relative path as key

#                         # Track code snippet
#                         snippet_hash = hashlib.sha256(code.encode()).hexdigest()
#                         await self.redis.track_code_snippet(snippet_hash, {
#                             'code': code, 'file_path': relative_path, 'language': language,
#                             'dependencies': dependencies, 'analysis': analysis.__dict__ if analysis else None
#                         })
#                         self.logger.debug(f"Stored file info and snippet in Redis for {relative_path}")
#                     except Exception as e:
#                          self.logger.error(f"Failed to store file info/snippet in Redis for {relative_path}: {e}", exc_info=True)
#             else:
#                  self.logger.warning(f"Unknown language for {relative_path}, skipping dependency update/analysis.")

#             return analysis, dependencies # Return results

#         except FileNotFoundError:
#              self.logger.warning(f"File not found during analysis: {abs_file_path}")
#              return None, []
#         except Exception as e:
#             # Catch broader errors during file read or processing
#             self.logger.error(f"Error during dependency update/analysis for {abs_file_path}: {e}", exc_info=True)
#             self.cli_ui.print_warning(f"Could not analyze or update dependencies for {file_path}.")
#             return None, []


#     async def execute_step_interactive(self, step_idx: int, step: Step) -> StepResult:
#         """Execute a single step with interactive prompts."""
#         async with self.semaphore:
#             self.cli_ui.display_step_start(step_idx, step)
#             step_start_time = time.time()
#             result: StepResult = StepResult(status="failed", error="Step execution did not complete") # Default

#             try:
#                 # Validate step
#                 validation_result = await self._validate_step(step)
#                 if validation_result:
#                     self.cli_ui.display_step_result(step_idx, validation_result)
#                     return validation_result

#                 # --- Step Execution Logic with Interaction ---

#                 # Resolve file path relative to working directory and make absolute
#                 abs_file_path = None
#                 if hasattr(step, 'file_path') and step.file_path:
#                     try:
#                         # Ensure file_path is treated as relative to working_directory
#                         abs_file_path = os.path.abspath(os.path.join(self.working_directory, step.file_path))
#                         # Basic path traversal check (optional but recommended)
#                         if not abs_file_path.startswith(os.path.abspath(self.working_directory)):
#                              raise ValueError("Attempted path traversal outside working directory.")
#                         self.logger.debug(f"Resolved step file path: '{step.file_path}' -> '{abs_file_path}'")
#                     except Exception as e:
#                          self.logger.error(f"Invalid file path provided in step: {step.file_path} - {e}")
#                          return StepResult(status="failed", error=f"Invalid file path: {step.file_path} ({e})")


#                 if step.type == "code_generation":
#                     if not abs_file_path: return StepResult(status="failed", error="Absolute file path resolution failed for code_generation") # Should not happen if validation passed

#                     self.cli_ui.print_message(f"Target file: [cyan]{abs_file_path}[/]")

#                     # Check if file exists
#                     exists = await self.file_manager.file_exists(abs_file_path)
#                     if exists:
#                         if not self.cli_ui.ask_confirmation(f"File '[bold]{step.file_path}[/]' already exists. Overwrite?"):
#                             self.logger.warning(f"User skipped overwriting file: {abs_file_path}")
#                             return StepResult(status="skipped", note="User chose not to overwrite existing file.")

#                     # Generate Code
#                     self.cli_ui.print_thinking("Generating code...")
#                     # Prepare context for LLM
#                     context = {
#                         "task": self.current_task,
#                         "plan_understanding": self.current_plan.understanding if self.current_plan else "N/A",
#                         "target_file_path": step.file_path # Provide relative path in context
#                         # Add more context if needed (e.g., previous step results)
#                     }
#                     code = await self.code_generator.generate(step.requirements or "Generate code based on context.", context)

#                     if isinstance(code, dict) and 'error' in code: # Check for LLM error
#                          error_msg = code['error']
#                          self.logger.error(f"LLM generation failed: {error_msg}")
#                          return StepResult(status="failed", error=f"LLM Error: {error_msg}")
#                     elif not isinstance(code, str):
#                          self.logger.error(f"LLM generation returned unexpected type: {type(code)}")
#                          return StepResult(status="failed", error=f"LLM returned unexpected type: {type(code)}")

#                     # Display Code and Ask for Confirmation/Edit
#                     language = extract_language_from_path(abs_file_path)
#                     self.cli_ui.display_code(code, language=language, file_path=step.file_path) # Show relative path to user

#                     edit_choice = self.cli_ui.ask_edit_confirmation(step.file_path) # Ask using relative path

#                     if edit_choice == 'cancel':
#                         self.logger.warning(f"User cancelled writing file: {abs_file_path}")
#                         return StepResult(status="skipped", note="User cancelled action.")
#                     elif edit_choice == 'edit':
#                         # Write the generated code first so the user can edit it
#                         try:
#                             await self.file_manager.write_file(abs_file_path, code)
#                             self.cli_ui.prompt_manual_edit(abs_file_path) # Prompt using absolute path
#                             # Re-read the code after potential manual edit
#                             code = await self.file_manager.read_file(abs_file_path)
#                             self.cli_ui.print_message("Code updated from file after manual edit.", style="dim")
#                             self.logger.info(f"User manually edited {abs_file_path}. Reloaded content.")
#                         except FileNotFoundError:
#                              self.logger.error(f"File {abs_file_path} not found after user edit prompt.")
#                              return StepResult(status="failed", error="File not found after manual edit prompt.")
#                         except Exception as e:
#                              self.logger.error(f"Error during manual edit process for {abs_file_path}: {e}", exc_info=True)
#                              return StepResult(status="failed", error=f"Error during manual edit: {e}")


#                     # Write File (either originally confirmed or after edit)
#                     self.cli_ui.print_thinking(f"Writing code to {step.file_path}...")
#                     try:
#                         # Use the potentially modified code content
#                         success = await self.file_manager.write_file(abs_file_path, code)
#                         if not success:
#                             raise IOError("File write operation returned false.")
#                         self.logger.info(f"Successfully wrote code to {abs_file_path}")
#                         file_hash = compute_file_hash(abs_file_path)
#                         result = StepResult(status="completed", file=step.file_path, result={"file_hash": file_hash})
#                         # Analyze and update dependencies after successful write (pass relative path)
#                         await self._update_dependencies_and_analyze(step.file_path, code)

#                     except Exception as e:
#                         self.logger.error(f"Error writing file {abs_file_path}: {e}", exc_info=True)
#                         result = StepResult(status="failed", error=f"Failed to write file '{step.file_path}': {e}")


#                 elif step.type == "code_modification":
#                     if not abs_file_path: return StepResult(status="failed", error="Absolute file path resolution failed for code_modification")

#                     self.cli_ui.print_message(f"Target file: [cyan]{abs_file_path}[/]")

#                     # Read existing code
#                     try:
#                         existing_code = await self.file_manager.read_file(abs_file_path)
#                         self.logger.info(f"Read existing code from {abs_file_path} ({len(existing_code)} bytes)")
#                     except FileNotFoundError:
#                         self.logger.error(f"File not found for modification: {abs_file_path}")
#                         return StepResult(status="failed", error=f"File not found: {step.file_path}")
#                     except Exception as e:
#                          self.logger.error(f"Error reading file {abs_file_path} for modification: {e}", exc_info=True)
#                          return StepResult(status="failed", error=f"Error reading file '{step.file_path}': {e}")

#                     language = extract_language_from_path(abs_file_path)
#                     self.cli_ui.print_message("Existing code snippet:", style="dim")
#                     self.cli_ui.display_code(existing_code[:500] + ("..." if len(existing_code) > 500 else ""), language=language, file_path=step.file_path) # Show snippet

#                     # Analyze existing code (pass relative path)
#                     self.cli_ui.print_thinking("Analyzing existing code...")
#                     analysis, _ = await self._update_dependencies_and_analyze(step.file_path, existing_code)

#                     # Generate Modifications
#                     self.cli_ui.print_thinking("Generating code modifications...")
#                     modifications = step.requirements or "Modify the code based on the plan and context."
#                     modified_code = await self.code_generator.modify(existing_code, modifications, analysis)

#                     if isinstance(modified_code, dict) and 'error' in modified_code: # Check for LLM error
#                          error_msg = modified_code['error']
#                          self.logger.error(f"LLM modification failed: {error_msg}")
#                          return StepResult(status="failed", error=f"LLM Error: {error_msg}")
#                     elif not isinstance(modified_code, str):
#                          self.logger.error(f"LLM modification returned unexpected type: {type(modified_code)}")
#                          return StepResult(status="failed", error=f"LLM returned unexpected type: {type(modified_code)}")


#                     # Display Modified Code and Ask for Confirmation/Edit
#                     self.cli_ui.print_message("Proposed modified code:", style="bold")
#                     self.cli_ui.display_code(modified_code, language=language, file_path=step.file_path) # Show relative path

#                     edit_choice = self.cli_ui.ask_edit_confirmation(step.file_path, action="apply modifications to") # Ask using relative path

#                     if edit_choice == 'cancel':
#                         self.logger.warning(f"User cancelled modifying file: {abs_file_path}")
#                         return StepResult(status="skipped", note="User cancelled action.")
#                     elif edit_choice == 'edit':
#                          # Write the proposed changes first so user can edit them
#                          try:
#                             await self.file_manager.write_file(abs_file_path, modified_code)
#                             self.cli_ui.prompt_manual_edit(abs_file_path) # Use absolute path
#                             # Re-read the code after potential manual edit
#                             modified_code = await self.file_manager.read_file(abs_file_path)
#                             self.cli_ui.print_message("Code updated from file after manual edit.", style="dim")
#                             self.logger.info(f"User manually edited {abs_file_path} after modification proposal. Reloaded content.")
#                          except Exception as e:
#                              self.logger.error(f"Error during manual edit process for {abs_file_path}: {e}", exc_info=True)
#                              return StepResult(status="failed", error=f"Error during manual edit: {e}")

#                     # Write Modified File (if confirmed directly or after edit)
#                     self.cli_ui.print_thinking(f"Applying modifications to {step.file_path}...")
#                     try:
#                         # Use the potentially modified code
#                         success = await self.file_manager.write_file(abs_file_path, modified_code)
#                         if not success:
#                             raise IOError("File write operation returned false.")
#                         self.logger.info(f"Successfully wrote modified code to {abs_file_path}")
#                         file_hash = compute_file_hash(abs_file_path)
#                         note = "Applied via manual edit" if edit_choice == 'edit' else None
#                         result = StepResult(status="completed", file=step.file_path, result={"file_hash": file_hash}, note=note)
#                         # Analyze and update dependencies after successful write (pass relative path)
#                         await self._update_dependencies_and_analyze(step.file_path, modified_code)
#                     except Exception as e:
#                         self.logger.error(f"Error writing modified file {abs_file_path}: {e}", exc_info=True)
#                         result = StepResult(status="failed", error=f"Failed to write modified file '{step.file_path}': {e}")


#                 elif step.type == "terminal_command":
#                     command = step.command
#                     # Display command relative to working directory for clarity
#                     self.cli_ui.display_command(command)
#                     # Confirm execution in the resolved working directory
#                     if not self.cli_ui.ask_confirmation(f"Execute the above command in '[bold]{self.working_directory}[/]'?"):
#                         self.logger.warning(f"User skipped executing command: {command}")
#                         return StepResult(status="skipped", note="User chose not to execute command.")

#                     # Execute Command
#                     self.cli_ui.print_thinking(f"Executing: {command}")
#                     # Ensure execution happens in the agent's working directory
#                     output_dict = await self.terminal.execute(command, cwd=self.working_directory)
#                     self.logger.info(f"Command '{command}' executed in '{self.working_directory}'. Success: {output_dict.get('success')}")

#                     # Display Output
#                     self.cli_ui.display_command_output(output_dict)

#                     status = "completed" if output_dict.get("success") else "failed"
#                     result = StepResult(
#                         status=status,
#                         output=output_dict.get("stdout", ""),
#                         error=output_dict.get("stderr", "") if not output_dict.get("success") else None,
#                         result={"return_code": output_dict.get("return_code")}
#                     )

#                 else:
#                     # This case should ideally not be reached if validation is correct
#                     self.logger.error(f"Reached unknown step type execution block: {step.type}")
#                     result = StepResult(status="failed", error=f"Internal error: Unknown step type '{step.type}'")

#                 # --- Finalize Step ---
#                 step_end_time = time.time()
#                 self.logger.info(f"Step {step_idx + 1} ('{step.description[:30]}...') finished with status '{result.status}' in {step_end_time - step_start_time:.2f} seconds.")
#                 self.cli_ui.display_step_result(step_idx, result)
#                 return result

#             except Exception as e:
#                 step_end_time = time.time()
#                 self.logger.error(f"Critical error executing step {step_idx+1} ('{step.description[:30]}...') after {step_end_time - step_start_time:.2f} seconds: {str(e)}", exc_info=True)
#                 err_res = StepResult(status="failed", error=f"Unexpected Agent Error during step execution: {str(e)}")
#                 self.cli_ui.display_step_result(step_idx, err_res)
#                 return err_res


#     async def execute_plan_interactive(self, plan: Plan) -> bool:
#         """Execute a plan interactively, step by step."""
#         if not plan or not plan.steps:
#              self.cli_ui.print_error("Cannot execute an empty or invalid plan.")
#              return False

#         self.current_plan = plan
#         self.execution_results = {} # Reset results for this plan execution

#         self.cli_ui.display_plan(plan)

#         if not self.cli_ui.ask_confirmation("Proceed with executing this plan?"):
#             self.logger.warning("User chose not to execute the plan.")
#             self.cli_ui.print_message("Plan execution cancelled by user.", style="yellow")
#             return False # Indicate plan was cancelled before starting

#         all_steps_succeeded = True
#         for i, step in enumerate(plan.steps):
#             step_result = await self.execute_step_interactive(i, step)
#             self.execution_results[i] = step_result # Store result

#             if step_result.status == "failed":
#                 self.logger.warning(f"Step {i+1} failed. Stopping plan execution.")
#                 self.cli_ui.print_error(f"Step {i+1} ('{step.description[:30]}...') failed. Stopping plan execution.")
#                 all_steps_succeeded = False
#                 # Ask user if they want to try refining the plan
#                 if self.cli_ui.ask_confirmation("A step failed. Attempt to refine the plan and continue?"):
#                     self.logger.info("User chose to refine the plan after failure.")
#                     # Attempt refinement. If successful, the refined plan execution continues.
#                     # If refinement fails or the refined plan fails, it returns False.
#                     return await self.refine_and_retry_plan_interactive()
#                 else:
#                     self.logger.info("User chose not to refine the plan after failure.")
#                     break # Stop execution of the current plan
#             elif step_result.status == "skipped":
#                  self.logger.info(f"Step {i+1} ('{step.description[:30]}...') was skipped by the user.")
#                  # Decide if skipping should halt the plan (e.g., if a critical step is skipped)
#                  # For now, let's allow continuing, but log it.
#                  # If skipping should stop, set all_steps_succeeded = False and break.

#         # If loop completes without breaking due to failure/refusal to refine
#         return all_steps_succeeded


#     async def refine_and_retry_plan_interactive(self) -> bool:
#         """Attempt to refine the plan after a failure and execute the new plan."""
#         if not self.current_plan or not self.execution_results:
#             self.cli_ui.print_error("Cannot refine plan: No current plan or execution results available.")
#             return False # Refinement cannot proceed

#         self.cli_ui.print_thinking("Refining the plan based on execution results...")
#         self.logger.info("Attempting plan refinement...")

#         try:
#             # Convert StepResult objects to dictionaries for the LLM prompt
#             # Ensure sensitive data (like full command output) is handled appropriately if needed
#             results_dict_for_llm = {}
#             for idx, res in self.execution_results.items():
#                  # Create a serializable version of the result
#                  res_data = {
#                      "status": res.status,
#                      "error": res.error,
#                      "file": res.file,
#                      # Limit output length in context to avoid excessive prompt size
#                      "output_snippet": (res.output[:200] + "..." if res.output and len(res.output) > 200 else res.output) if res.output else None,
#                      "note": res.note
#                  }
#                  results_dict_for_llm[idx] = {k: v for k, v in res_data.items() if v is not None} # Remove None values


#             # Prepare feedback for the planner
#             feedback = f"Refine plan due to failures or issues encountered. Execution results so far: {json.dumps(results_dict_for_llm, indent=2)}"

#             # Call the planner's refine method
#             refined_plan = await self.planner.refine_plan(self.current_plan, feedback)

#             self.logger.info("Plan refinement generated by LLM.")
#             self.cli_ui.print_message("Plan refinement generated.", style="bold magenta")

#             # Execute the refined plan (this replaces the rest of the original plan execution)
#             # The success/failure of the task now depends entirely on the refined plan's execution
#             return await self.execute_plan_interactive(refined_plan)

#         except Exception as e:
#             self.logger.error(f"Error during plan refinement process: {e}", exc_info=True)
#             self.cli_ui.print_error(f"Failed to refine the plan: {e}")
#             return False # Refinement failed, so the overall task failed at this point


#     async def run_interactive(self, task_description: str) -> Dict[str, Any]:
#         """Main interactive entry point for a single task."""
#         await self.set_task(task_description)
#         task_start_time = time.time()
#         self.logger.info(f"--- Starting Task ID: {self.task_id} ---")

#         # 1. Create Initial Plan
#         self.cli_ui.print_thinking("Creating initial execution plan...")
#         try:
#             initial_plan = await self.planner.create_plan(self.current_task)
#             if not initial_plan or not initial_plan.steps:
#                  self.logger.error("Planner returned an empty or invalid plan.")
#                  self.cli_ui.print_error("Failed to create a valid initial plan.")
#                  return {"task_id": self.task_id, "error": "Plan creation failed (empty plan)", "success": False}
#             self.logger.info(f"Initial plan created successfully with {len(initial_plan.steps)} steps.")
#             # Store initial plan in context if Redis is enabled
#             await self._store_context("initial_plan", initial_plan.__dict__)
#         except Exception as e:
#             self.logger.error(f"Failed to create initial plan: {e}", exc_info=True)
#             self.cli_ui.print_error(f"Failed to create initial plan: {e}")
#             return {"task_id": self.task_id, "error": f"Plan creation failed: {e}", "success": False}

#         # 2. Execute Plan Interactively
#         plan_succeeded = await self.execute_plan_interactive(initial_plan)

#         # 3. Final Summary
#         task_end_time = time.time()
#         duration = task_end_time - task_start_time
#         final_status_message = "successfully" if plan_succeeded else "with errors or cancellation"

#         if plan_succeeded:
#             self.cli_ui.print_message(f"\nPlan executed successfully in {duration:.2f} seconds.", style="bold green")
#             self.logger.info(f"Task '{self.task_id}' completed successfully in {duration:.2f} seconds.")
#         else:
#             self.cli_ui.print_error(f"\nPlan execution finished {final_status_message} in {duration:.2f} seconds.")
#             self.logger.warning(f"Task '{self.task_id}' finished {final_status_message} in {duration:.2f} seconds.")

#         # Prepare final results dictionary
#         final_results = {
#             "task_id": self.task_id,
#             # Serialize results, removing non-serializable parts if necessary
#             "results": {idx: res.__dict__ for idx, res in self.execution_results.items()},
#             "success": plan_succeeded,
#             "duration_seconds": duration
#         }
#         # Store final results in context if Redis is enabled
#         await self._store_context("final_results", final_results)

#         # Optionally display detailed final results via UI
#         self.cli_ui.display_final_results(final_results)

#         return final_results


#     async def cleanup(self):
#         """Perform cleanup actions when the agent exits."""
#         self.logger.info("Performing agent cleanup...")
#         if self.redis:
#             try:
#                 await self.redis.close()
#                 self.logger.info("Redis connection closed.")
#             except Exception as e:
#                 self.logger.error(f"Error closing Redis connection: {e}")
#         # Add any other cleanup needed (e.g., closing files, stopping subprocesses)
#         self.cli_ui.print_message("Agent cleanup complete.", style="dim")
#         self.logger.info("--- Agent Shutdown ---")


# core/agent.py

import logging
import asyncio
from typing import Dict, List, Optional, Any, Union
import os
import hashlib
import time
import json
import re # Import regex
import pathlib # For path operations

# Assuming components are in respective directories relative to project root
try:
    from core.planner import Planner
    from core.code_generator import CodeGenerator
    from core.code_analyzer import CodeAnalyzer
    from core.file_manager import FileManager
    from core.dependency_manager import DependencyManager
    from core.improvement_engine import ImprovementEngine
    from adapters.terminal_adapter import TerminalAdapter
    from adapters.llm_adapter import LLMAdapter
    from adapters.redis_adapter import RedisAdapter
    from utils.schema import Plan, Step, StepResult, CodeAnalysis
    from utils.helpers import save_json, compute_file_hash, extract_language_from_path, sanitize_path
    from utils.ast_parser import ASTParser
    from utils.cli_ui import CLI_UI
    from utils.logger import get_logger # Import get_logger
    # Import Rich components used in helper methods if needed directly
    from rich.panel import Panel
except ImportError as e:
     print(f"Agent Import Error: {e}. Ensure main.py is setting up sys.path correctly.")
     raise

class Agent:
    def __init__(self, config: Dict[str, Any], cli_ui: CLI_UI):
        self.logger = get_logger(__name__) # Use centralized logger
        self.config = config
        self.cli_ui = cli_ui

        # --- Adapter Initialization ---
        try:
            self.llm = LLMAdapter(config["llm"])
        except KeyError as e:
            self.logger.error(f"LLM configuration missing key: {e}")
            raise ValueError(f"LLM configuration missing key: {e}") from e
        except Exception as e:
             self.logger.error(f"Failed to initialize LLMAdapter: {e}", exc_info=True)
             raise RuntimeError(f"Failed to initialize LLMAdapter: {e}") from e

        self.terminal = TerminalAdapter()

        # Conditionally initialize Redis if configured
        self.redis = None
        if config.get("redis"):
            try:
                self.redis = RedisAdapter(config["redis"])
                self.logger.info("Redis adapter initialized.")
            except Exception as e:
                self.logger.warning(f"Failed to initialize Redis adapter: {e}. Proceeding without Redis.")
                self.cli_ui.print_warning("Could not connect to Redis. State and caching will be limited.")
        else:
             self.logger.info("Redis not configured. State and caching will be limited.")

        # --- Core Component Initialization ---
        self.working_directory = config.get("working_directory")
        if not os.path.isabs(self.working_directory):
             self.logger.warning(f"Working directory '{self.working_directory}' might not be absolute.")
        # Ensure working directory exists (FileManager does this too, but good to be sure)
        try:
            pathlib.Path(self.working_directory).mkdir(parents=True, exist_ok=True)
        except Exception as e:
             self.logger.error(f"Failed to create working directory '{self.working_directory}': {e}", exc_info=True)
             raise RuntimeError(f"Cannot create working directory: {e}") from e


        try:
            # Pass redis adapter where needed
            self.planner = Planner(self.llm, self.redis)
            self.code_generator = CodeGenerator(self.llm, self.redis)
            self.code_analyzer = CodeAnalyzer(self.llm, self.redis)
            self.file_manager = FileManager(self.working_directory)
            self.dependency_manager = DependencyManager(self.redis)
            self.improvement_engine = ImprovementEngine(self.llm, self.redis)
        except Exception as e:
             self.logger.error(f"Failed to initialize core components: {e}", exc_info=True)
             raise RuntimeError(f"Failed to initialize core components: {e}") from e

        # Initialize AST Parser (optional)
        self.ast_parser = None
        try:
            self.ast_parser = ASTParser()
            self.logger.info("AST Parser initialized.")
        except FileNotFoundError as e:
             self.logger.warning(f"AST Parser library not found: {e}. Code analysis features will be limited.")
             self.cli_ui.print_warning(f"AST Parser library not found: {e}. Code analysis features will be limited.")
        except Exception as e:
             self.logger.error(f"Unexpected AST Parser Error: {e}. Code analysis features will be limited.", exc_info=True)
             self.cli_ui.print_error(f"Unexpected AST Parser Error: {e}. Code analysis features will be limited.")

        # --- Agent State ---
        self.current_task: Optional[str] = None
        self.current_plan: Optional[Plan] = None
        self.task_id: Optional[str] = None
        # execution_state now holds index and step results for resumption
        self.execution_state: Dict[str, Any] = {"current_step_index": 0, "step_results": {}}
        # execution_results stores StepResult objects for the current run/refinement
        self.execution_results: Dict[int, StepResult] = {}

        # Concurrency settings
        self.max_workers = config.get("concurrency", {}).get("max_workers", 5)
        self.semaphore = asyncio.Semaphore(self.max_workers)
        self.logger.debug(f"Agent initialized with max_workers={self.max_workers}")

    def _generate_task_id(self, task_description: str) -> str:
        """Generate a unique task ID based on the task description and timestamp"""
        timestamp = str(time.time())
        content_hash = hashlib.sha256(task_description[:1000].encode()).hexdigest() # Hash first 1k chars
        return f"{timestamp}-{content_hash}"[:24] # Keep ID manageable

    # --- Redis Context/State Management ---
    async def _store_context(self, key: str, data: Any) -> bool:
        """Store context data in Redis (if Redis enabled)."""
        if not self.redis or not self.task_id:
            return False
        full_key = f"task:{self.task_id}:context:{key}" # Add context namespace
        try:
            await self.redis.store_context(full_key, data) # Rely on redis adapter's serialization
            self.logger.debug(f"Stored context in Redis: {full_key}")
            return True
        except Exception as e:
            self.logger.error(f"Redis store_context failed for key '{full_key}': {e}")
            return False

    async def _get_context(self, key: str) -> Optional[Any]:
        """Retrieve context data from Redis (if Redis enabled)."""
        if not self.redis or not self.task_id:
            return None
        full_key = f"task:{self.task_id}:context:{key}" # Add context namespace
        try:
            data = await self.redis.get_context(full_key)
            self.logger.debug(f"Retrieved context from Redis: {full_key} (Found: {data is not None})")
            return data
        except Exception as e:
            self.logger.error(f"Redis get_context failed for key '{full_key}': {e}")
            return None

    async def _store_execution_state(self) -> bool:
        """Stores the current execution state (plan, results, step index) to Redis."""
        if not self.redis or not self.task_id:
            return False
        try:
            # Capture current state for storage
            state_to_store = {
                "task_description": self.current_task,
                "task_id": self.task_id,
                # Use the current execution_state directly
                "current_step_index": self.execution_state.get("current_step_index", 0),
                "step_results": {idx: res.__dict__ for idx, res in self.execution_results.items()}, # Store results from current run
            }
            if self.current_plan:
                 state_to_store["plan"] = {
                     "understanding": self.current_plan.understanding,
                     "files": self.current_plan.files,
                     "steps": [s.to_dict() for s in self.current_plan.steps]
                 }

            # Use the dedicated state storage method in Redis adapter
            success = await self.redis.store_execution_state(self.task_id, state_to_store)
            if success:
                 self.logger.debug(f"Stored execution state for task {self.task_id}")
            else:
                 self.logger.warning(f"Failed to store execution state for task {self.task_id}")
            return success
        except Exception as e:
            self.logger.error(f"Failed to store execution state: {e}", exc_info=True)
            return False

    async def _load_execution_state(self) -> bool:
        """Loads execution state from Redis to potentially resume."""
        if not self.redis or not self.task_id:
             self.logger.debug("Redis not available or no Task ID set, cannot load state.")
             self.execution_state = {"current_step_index": 0, "step_results": {}} # Reset local state
             self.execution_results = {}
             return False
        try:
            # Use the dedicated state retrieval method
            state = await self.redis.get_execution_state(self.task_id)
            if state:
                self.logger.info(f"Found existing execution state for task {self.task_id}.")
                self.current_task = state.get("task_description", self.current_task)
                # Restore plan
                self.current_plan = None # Reset plan initially
                if state.get("plan") and isinstance(state["plan"], dict):
                    try:
                        plan_data = state["plan"]
                        steps = [Step.from_dict(step_data) for step_data in plan_data.get("steps", [])]
                        self.current_plan = Plan(
                            understanding=plan_data.get("understanding", ""),
                            files=plan_data.get("files", []),
                            steps=steps
                        )
                        self.logger.info(f"Restored plan with {len(self.current_plan.steps)} steps from state.")
                    except Exception as e:
                         self.logger.error(f"Error parsing plan from saved state: {e}", exc_info=True)
                         self.current_plan = None # Invalidate plan if parsing fails

                # Restore results and index from the main state dict
                loaded_results = state.get("step_results", {})
                self.execution_results = {}
                for idx_str, res_dict in loaded_results.items():
                    try:
                        self.execution_results[int(idx_str)] = StepResult(**res_dict)
                    except Exception as e:
                         self.logger.warning(f"Could not parse step result {idx_str} from state: {e}")

                self.execution_state["current_step_index"] = state.get("current_step_index", 0)
                # Ensure step_results are mirrored in execution_state if needed elsewhere, though execution_results is primary now
                self.execution_state["step_results"] = state.get("step_results", {})

                self.cli_ui.print_message(f"Resuming task '{self.task_id}'. Last completed step index: {self.execution_state['current_step_index'] -1 }. Next step: {self.execution_state['current_step_index'] + 1}", style="yellow")
                return True
            else:
                self.logger.info(f"No existing execution state found for task {self.task_id}.")
                self.execution_state = {"current_step_index": 0, "step_results": {}} # Initialize default state
                self.execution_results = {}
                return False
        except Exception as e:
            self.logger.error(f"Failed to load or parse execution state: {e}", exc_info=True)
            self.execution_state = {"current_step_index": 0, "step_results": {}} # Reset state on error
            self.execution_results = {}
            return False


    # --- Task Management ---
    async def set_task(self, task_description: str, source: str = "User Prompt"):
        """Set the current task, generate a new task ID, log source, and attempt to load state."""
        self.current_task = task_description
        self.task_id = self._generate_task_id(task_description) # Generate ID based on initial description
        self.current_plan = None # Reset plan
        self.execution_results = {} # Reset results for the current run
        self.execution_state = {"current_step_index": 0, "step_results": {}} # Reset internal state tracker

        self.logger.info(f"Set new task (ID: {self.task_id}) from {source}: {task_description[:100]}...")

        # Attempt to load state ONLY AFTER task_id is set
        await self._load_execution_state()

        # Store initial task info regardless of loaded state (overwrites if loaded)
        await self._store_context("task_info", {"description": self.current_task, "source": source, "task_id": self.task_id})


    # --- Direct Action Handlers ---
    async def _handle_direct_analysis(self, file_path: str, focus: str = "general") -> bool:
        """Handles a direct request to analyze a specific file."""
        self.cli_ui.print_thinking(f"Analyzing {file_path} (focus: {focus})...")
        try:
            abs_path = self.file_manager._resolve_path(file_path)
            if not abs_path.startswith(os.path.abspath(self.working_directory)):
                 self.cli_ui.print_error(f"Security Error: Cannot analyze files outside the workspace.")
                 return False

            if not await self.file_manager.file_exists(abs_path):
                 self.cli_ui.print_error(f"File not found for analysis: {file_path}")
                 return False

            code = await self.file_manager.read_file(abs_path)
            # Use relative path for analysis context/caching if possible
            relative_path = os.path.relpath(abs_path, self.working_directory)
            analysis_result = await self.code_analyzer.analyze(code, file_path=relative_path, analysis_focus=focus)

            self.cli_ui.print_message(f"Analysis Results for [cyan]{relative_path}[/]:", style="bold")
            analysis_json = json.dumps(analysis_result.__dict__, indent=2, default=str) # Use default=str for non-serializable
            self.cli_ui.console.print(Panel(analysis_json, title="Code Analysis Result", border_style="blue", expand=False))
            return True

        except ValueError as ve:
            self.cli_ui.print_error(f"Analysis Error: {ve}")
            return False
        except FileNotFoundError:
            self.cli_ui.print_error(f"File not found: {file_path}")
            return False
        except Exception as e:
            self.logger.error(f"Error during direct analysis of {file_path}: {e}", exc_info=True)
            self.cli_ui.print_error(f"An unexpected error occurred during analysis: {e}")
            return False

    async def _handle_direct_modification(self, file_path: str, modification_request: str) -> bool:
        """Handles a direct request to modify a specific file."""
        self.cli_ui.print_thinking(f"Preparing to modify {file_path}...")
        try:
            abs_path = self.file_manager._resolve_path(file_path)
            if not abs_path.startswith(os.path.abspath(self.working_directory)):
                 self.cli_ui.print_error(f"Security Error: Cannot modify files outside the workspace.")
                 return False

            if not await self.file_manager.file_exists(abs_path):
                self.cli_ui.print_error(f"File not found for modification: {file_path}")
                return False

            existing_code = await self.file_manager.read_file(abs_path)
            language = extract_language_from_path(abs_path)
            relative_path = os.path.relpath(abs_path, self.working_directory)

            analysis = None
            try:
                analysis = await self.code_analyzer.analyze(existing_code, file_path=relative_path)
                self.cli_ui.display_analysis_summary(analysis)
            except Exception as e:
                 self.logger.warning(f"Could not analyze {relative_path} before modification: {e}")

            self.cli_ui.print_message("Current code snippet:", style="dim")
            self.cli_ui.display_code(existing_code[:500] + "..." if len(existing_code) > 500 else existing_code, language=language, file_path=relative_path)
            self.cli_ui.print_message(f"Modification requested: [italic]{modification_request}[/]")

            self.cli_ui.print_thinking("Generating modifications...")
            context = {"file_path": relative_path}
            # Pass CodeAnalysis object directly if available
            modified_code = await self.code_generator.modify(
                existing_code=existing_code,
                modifications=modification_request,
                analysis=analysis, # Pass the object
                # language=language,
                context=context
            )


            if isinstance(modified_code, dict) and 'error' in modified_code:
                 self.cli_ui.print_error(f"LLM modification failed: {modified_code['error']}")
                 return False
            elif not isinstance(modified_code, str) or not modified_code.strip():
                 self.cli_ui.print_error("LLM did not return valid code for modification.")
                 return False

            self.cli_ui.display_code(modified_code, language=language, file_path=relative_path)
            edit_choice = self.cli_ui.ask_edit_confirmation(relative_path, action="apply modifications to")

            if edit_choice == 'cancel':
                self.cli_ui.print_message("Modification cancelled by user.", style="yellow")
                return False
            elif edit_choice == 'edit':
                try:
                    await self.file_manager.write_file(abs_path, modified_code)
                    self.cli_ui.prompt_manual_edit(abs_path)
                    modified_code = await self.file_manager.read_file(abs_path)
                    self.cli_ui.print_message("Code updated from file after manual edit.", style="dim")
                    self.logger.info(f"User manually edited {abs_path} during direct modification.")
                except Exception as e:
                     self.logger.error(f"Error during manual edit for direct modification {abs_path}: {e}", exc_info=True)
                     self.cli_ui.print_error(f"Error during manual edit: {e}")
                     return False

            self.cli_ui.print_thinking(f"Applying changes to {relative_path}...")
            try:
                # Use the potentially modified code
                success = await self.file_manager.write_file(abs_path, modified_code)
                if success:
                    self.cli_ui.print_message(f"Successfully modified {relative_path}.", style="bold green")
                    await self._update_dependencies_and_analyze(relative_path, modified_code) # Use relative path
                    return True
                else:
                    self.cli_ui.print_error(f"Failed to write changes to {relative_path}.")
                    return False
            except Exception as e:
                 self.logger.error(f"Error writing final modifications to {abs_path}: {e}", exc_info=True)
                 self.cli_ui.print_error(f"Failed to write changes to {relative_path}: {e}")
                 return False

        except ValueError as ve:
             self.cli_ui.print_error(f"Modification Error: {ve}")
             return False
        except FileNotFoundError:
             self.cli_ui.print_error(f"File not found: {file_path}") # Use original path in error message
             return False
        except Exception as e:
            self.logger.error(f"Error during direct modification of {file_path}: {e}", exc_info=True)
            self.cli_ui.print_error(f"An unexpected error occurred during modification: {e}")
            return False


    # --- Interactive Execution Logic ---
    async def run_interactive(self, initial_input: str) -> Dict[str, Any]:
        """Main interactive entry point for a single task."""
        # Set task and attempt to load state based on initial input's hash
        await self.set_task(initial_input, source="User Input") # This now handles loading state if available
        task_start_time = time.time()
        self.logger.info(f"--- Starting Task ID: {self.task_id} ---")
        # Use self.current_task which might have been updated by _load_execution_state
        self.logger.info(f"Effective Task Description (potentially loaded): {self.current_task[:500]}...")

        task_description = self.current_task # Use the potentially loaded description
        task_description_source = "User Input or Loaded State" # Adjust source if needed
        handled_directly = False # Flag to skip planning if handled by direct action/conversation
        plan_to_execute = self.current_plan # Use potentially loaded plan

        # --- Task Pre-processing Logic (Only if not resuming a plan) ---
        if plan_to_execute is None: # Only run pre-processing if we don't have a plan from loaded state
            try:
                # 1. Check for Load Command
                load_trigger = "load:"
                if initial_input.lower().startswith(load_trigger):
                    file_path_to_load = initial_input[len(load_trigger):].strip()
                    self.logger.info(f"Detected file load request for: {file_path_to_load}")
                    try:
                        resolved_path = self.file_manager._resolve_path(file_path_to_load)
                        if not resolved_path.startswith(os.path.abspath(self.working_directory)):
                             self.cli_ui.print_error(f"Security Error: Cannot load files outside the workspace.")
                             return {"task_id": self.task_id, "error": "Path outside workspace", "success": False}

                        if await self.file_manager.file_exists(resolved_path):
                            self.cli_ui.print_thinking(f"Loading task from {file_path_to_load}...")
                            # *** Successfully loaded, update task_description and source ***
                            task_description = await self.file_manager.read_file(resolved_path)
                            task_description_source = f"File: {file_path_to_load}"
                            self.current_task = task_description # Update agent's current task
                            # Optionally reset Task ID based on loaded content, or keep original?
                            # Let's keep the original Task ID for consistency for now.
                            # await self.set_task(task_description, source=task_description_source) # This would reset ID and state loading
                            self.logger.info(f"Task description loaded successfully from {resolved_path}. Length: {len(task_description)}")
                            # *** DO NOT set handled_directly = True here ***
                            # *** Fall through to planning below ***
                        else:
                            self.cli_ui.print_error(f"Task file not found: {file_path_to_load}")
                            return {"task_id": self.task_id, "error": f"Task file not found: {file_path_to_load}", "success": False}

                    except Exception as e:
                        # ... (error handling for loading) ...
                        self.logger.error(f"Error loading task file '{file_path_to_load}': {e}", exc_info=True)
                        self.cli_ui.print_error(f"Error reading task file: {e}")
                        return {"task_id": self.task_id, "error": f"Error reading task file: {e}", "success": False}

                # 2. Check for Direct Actions (Analyze/Modify) - Only if NOT loaded from file
                # Use initial_input here, not task_description (which might be file content)
                if not task_description_source.startswith("File:"):
                    direct_action_match = re.match(r"^\s*(analyze|modify|explain|review|refactor|change)\s+([\w./\\~-]+)(?:\s+(.*))?$", initial_input, re.IGNORECASE)
                    if direct_action_match:
                        action = direct_action_match.group(1).lower()
                        file_path = direct_action_match.group(2).strip().replace("~", os.path.expanduser("~"))
                        details = (direct_action_match.group(3) or "").strip()
                        self.logger.info(f"Detected direct action request: Action='{action}', File='{file_path}', Details='{details[:50]}...'")

                        action_success = False
                        if action in ["analyze", "explain", "review"]:
                            action_success = await self._handle_direct_analysis(file_path, focus=details or "general")
                            handled_directly = True # Mark as handled
                        elif action in ["modify", "refactor", "change"]:
                            if not details:
                                self.cli_ui.print_warning(f"Modification request for '{file_path}' needs details. Please specify what to change.")
                                # Fall through to planning
                            else:
                                action_success = await self._handle_direct_modification(file_path, details)
                                handled_directly = True # Mark as handled

                        # If handled directly, return result immediately
                        if handled_directly:
                             task_end_time = time.time()
                             return { "task_id": self.task_id, "results": {"summary": f"Direct action '{action}' on {file_path} {'completed' if action_success else 'failed'}."}, "success": action_success, "duration_seconds": time.time() - task_start_time }

                    # 3. Check for Conversational Input - Only if NOT loaded and NOT direct action
                    if not handled_directly: # Check again in case direct action fell through
                         coding_keywords = ['create', 'build', 'implement', 'add', 'fix', 'develop', 'write', 'generate', 'make', 'modify', 'analyze', 'refactor', 'class', 'function', 'module', 'api', 'test', 'bug', 'feature', 'endpoint', 'database', 'ui', '.py', '.js', '.html']
                         is_likely_coding_task = any(keyword in initial_input.lower() for keyword in coding_keywords)
                         is_short_and_general = len(initial_input.split()) < 10 and not is_likely_coding_task

                         if is_short_and_general:
                            self.logger.info("Detected potentially conversational input.")
                            self.cli_ui.print_message("I'm ready for coding tasks! Please describe what you'd like me to build, analyze, or modify, or use 'load: <file_path>' to load a task.", style="bold blue")
                            handled_directly = True # Mark as handled

            except Exception as e:
                self.logger.error(f"Error during task pre-processing: {e}", exc_info=True)
                # Fall through, let planning handle it or fail

        # --- Proceed with Planning or Finish ---
        # If handled directly by non-load pre-processing (e.g. conversational, direct action)
        if handled_directly:
             task_end_time = time.time()
             return {"task_id": self.task_id, "results": {"summary": "Task handled directly or conversationally without planning."}, "success": True, "duration_seconds": time.time() - task_start_time}

        # --- Standard Planning (If no plan loaded and not handled directly) ---
        # This block is now reached if:
        #   a) We didn't load a plan from state AND
        #   b) The input wasn't handled directly (conversational/direct action) OR
        #   c) The input was `load: file.txt` which successfully loaded content into task_description
        if plan_to_execute is None:
            self.logger.info(f"Proceeding with standard planning process. Task source: {task_description_source}")
            self.cli_ui.print_thinking("Creating execution plan...")
            try:
                context_for_planner = {"working_directory": self.working_directory}
                # Pass the final task_description (could be from user or file)
                plan_response = await self.planner.create_plan(
                    task_description=task_description,
                    context=context_for_planner
                )

                # Handle plan_response (Plan object or conversational string)
                if isinstance(plan_response, str):
                     self.logger.info(f"Planner returned conversational response: {plan_response}")
                     self.cli_ui.print_message(plan_response, style="bold blue")
                     task_end_time = time.time()
                     return {"task_id": self.task_id, "results": {"summary": "Task handled conversationally by planner."}, "success": True, "duration_seconds": time.time() - task_start_time}

                elif isinstance(plan_response, Plan):
                     plan_to_execute = plan_response # Set the plan to be executed
                     self.logger.info(f"Plan created successfully with {len(plan_to_execute.steps)} steps.")
                     self.current_plan = plan_to_execute # Store the newly created plan
                     plan_dict_for_storage = {"understanding": plan_to_execute.understanding,"files": plan_to_execute.files,"steps": [s.to_dict() for s in plan_to_execute.steps]}
                     if self.redis: await self._store_context("initial_plan", plan_dict_for_storage)

                else: # Handle unexpected type
                     self.logger.error(f"Planner returned unexpected type: {type(plan_response)}")
                     self.cli_ui.print_error("Received unexpected response from planner.")
                     return {"task_id": self.task_id, "error": "Unexpected planner response type", "success": False}

            except Exception as e:
                self.logger.error(f"Failed to create plan: {e}", exc_info=True)
                self.cli_ui.print_error(f"Failed to create plan: {e}")
                return {"task_id": self.task_id, "error": f"Plan creation failed: {e}", "success": False}

        # --- Execute Plan ---
        # This block runs if a plan was loaded from state OR created successfully above
        plan_succeeded = False
        if plan_to_execute:
            self.logger.info(f"Starting execution of plan for task {self.task_id}")
            plan_succeeded = await self.execute_plan_interactive(plan_to_execute)
        else:
             self.logger.error("Plan execution skipped as no valid plan was available.")
             self.cli_ui.print_error("Cannot execute plan as none was loaded or created successfully.")

        # --- Final Summary ---
        # ... (rest of the final summary logic remains the same) ...
        task_end_time = time.time()
        duration = task_end_time - task_start_time
        final_status_message = "successfully" if plan_succeeded else "with errors or cancellation"

        if plan_succeeded:
            self.cli_ui.print_message(f"\nTask completed {final_status_message} in {duration:.2f} seconds.", style="bold green")
        else:
            self.cli_ui.print_error(f"\nTask finished {final_status_message} in {duration:.2f} seconds.")

        final_results = {
            "task_id": self.task_id,
            "task_source": task_description_source,
            "results": {idx: res.__dict__ for idx, res in self.execution_results.items()},
            "success": plan_succeeded,
            "duration_seconds": duration
        }
        # Store final state including results
        await self._store_execution_state() # Store final state

        self.cli_ui.display_final_results(final_results) # Display summary

        return final_results


    # --- Step Validation and Execution ---
    async def _validate_step(self, step: Step) -> Optional[StepResult]:
        """Validate a step before execution."""
        if not hasattr(step, 'type') or not step.type:
            return StepResult(status="failed", error="Step object missing 'type' attribute or type is empty")
        valid_types = ["code_generation", "code_modification", "terminal_command", "code_analysis"]
        if step.type not in valid_types:
            return StepResult(status="failed", error=f"Invalid step type: '{step.type}'. Valid types: {valid_types}")

        if step.type in ["code_generation", "code_modification", "code_analysis"]:
            if not hasattr(step, 'file_path') or not step.file_path:
                return StepResult(status="failed", error=f"'{step.type}' step requires a 'file_path'")
            # Requirements optional for analysis
            if step.type != "code_analysis" and (not hasattr(step, 'requirements') or not step.requirements):
                 self.logger.warning(f"Step '{step.description}' ({step.type}) has no requirements. LLM might lack specific instructions.")

        if step.type == "terminal_command":
             if not hasattr(step, 'command') or not step.command:
                return StepResult(status="failed", error="'terminal_command' step requires a 'command'")
        return None # Step is valid

    async def execute_step_interactive(self, step_idx: int, step: Step) -> StepResult:
        """Execute a single step with interactive prompts."""
        async with self.semaphore:
            # self.cli_ui.display_step_start(step_idx, step)
            step_start_time = time.time()
            # Default result if something goes very wrong before assignment
            result: StepResult = StepResult(status="failed", error="Step execution did not initialize properly")

            try:
                try:
                    self.cli_ui.display_step_start(step_idx, step)
                except Exception as e:
                    self.logger.error(f"Error in self.cli_ui.display_step_start: {e}", exc_info=True)
                    return StepResult(status="failed", error=f"Error initializing UI: {e}")
                # Validate step structure first
                validation_result = await self._validate_step(step)
                if validation_result:
                    self.cli_ui.display_step_result(step_idx, validation_result)
                    # Store validation failure result before returning
                    self.execution_results[step_idx] = validation_result
                    self.execution_state["current_step_index"] = step_idx # Mark this step as attempted
                    await self._store_execution_state()
                    return validation_result
                
                # --- ADD THE DEBUG LOGS HERE ---
                self.logger.debug(f"Step {step_idx + 1}: step.type = '{step.type}'")
                if hasattr(step, 'file_path'):
                    self.logger.debug(f"Step {step_idx + 1}: step.file_path = '{step.file_path}'")
                else:
                    self.logger.debug(f"Step {step_idx + 1}: step.file_path attribute not found")
                # --- END OF DEBUG LOGS ---

                # Resolve file path relative to working directory and make absolute
                abs_file_path: Optional[str] = None
                relative_file_path: Optional[str] = None # Store relative path for results/context
                if hasattr(step, 'file_path') and step.file_path:
                    try:
                        relative_file_path = step.file_path # Assume it's relative
                        abs_file_path = self.file_manager._resolve_path(relative_file_path)
                        # --- Path Safety Check ---
                        if not abs_file_path.startswith(os.path.abspath(self.working_directory)):
                             self.logger.error(f"Security Risk: Step {step_idx+1} attempted to access path outside working directory: {abs_file_path}")
                             raise ValueError("Attempted path traversal outside working directory.")
                        self.logger.debug(f"Step {step_idx+1}: Resolved file path '{relative_file_path}' -> '{abs_file_path}'")
                    except ValueError as e: # Catch path validation errors
                         self.logger.error(f"Invalid file path in step {step_idx+1}: '{relative_file_path}' - {e}")
                         result = StepResult(status="failed", error=f"Invalid file path: {relative_file_path} ({e})")
                         # Store result and update state before returning
                         self.execution_results[step_idx] = result
                         self.execution_state["current_step_index"] = step_idx # Mark as attempted
                         await self._store_execution_state()
                         self.cli_ui.display_step_result(step_idx, result)
                         return result
                    except Exception as e: # Catch other resolution errors
                        self.logger.error(f"Error resolving path in step {step_idx+1}: '{relative_file_path}' - {e}", exc_info=True)
                        result = StepResult(status="failed", error=f"Error resolving path: {relative_file_path} ({e})")
                        self.execution_results[step_idx] = result
                        self.execution_state["current_step_index"] = step_idx
                        await self._store_execution_state()
                        self.cli_ui.display_step_result(step_idx, result)
                        return result


                # --- Step Execution Logic ---
                if step.type == "code_generation":
                    if not abs_file_path or not relative_file_path: # Check if paths resolved
                         result = StepResult(status="failed", error="Internal error: File path not resolved for code_generation")
                    else:
                        self.cli_ui.print_message(f"Target file: [cyan]{relative_file_path}[/]")
                        exists = await self.file_manager.file_exists(abs_file_path)
                        overwrite_confirmed = True
                        if exists:
                            self.logger.warning(f"Target file for generation already exists: {abs_file_path}")
                            overwrite_confirmed = self.cli_ui.ask_confirmation(f"File '[bold]{relative_file_path}[/]' already exists. Overwrite?")
                        if not overwrite_confirmed:
                            self.logger.info(f"User skipped overwriting file: {abs_file_path}")
                            result = StepResult(status="skipped", note="User chose not to overwrite existing file.", file=relative_file_path)
                        else:
                            # Proceed with generation
                            self.cli_ui.print_thinking("Generating code...")
                            context = { "task": self.current_task, "target_file_path": relative_file_path, "step_description": step.description }
                            code = await self.code_generator.generate(step.requirements or "Generate code based on context.", context)

                            if isinstance(code, dict) and 'error' in code:
                                 result = StepResult(status="failed", error=f"LLM Error: {code['error']}", file=relative_file_path)
                            elif not isinstance(code, str):
                                 result = StepResult(status="failed", error=f"LLM returned unexpected type: {type(code)}", file=relative_file_path)
                            else: # Code generated successfully
                                language = extract_language_from_path(abs_file_path)
                                self.cli_ui.display_code(code, language=language, file_path=relative_file_path)
                                edit_choice = self.cli_ui.ask_edit_confirmation(relative_file_path)

                                write_to_file = False # Flag to control if writing should proceed
                                edit_failed = False # Flag if manual edit had an error

                                if edit_choice == 'cancel':
                                    result = StepResult(status="skipped", note="User cancelled action.", file=relative_file_path)
                                    # Do not proceed to write
                                elif edit_choice == 'edit':
                                    try:
                                        await self.file_manager.write_file(abs_file_path, code) # Write temp version for editing
                                        self.cli_ui.prompt_manual_edit(abs_file_path) # Ask user to edit
                                        code = await self.file_manager.read_file(abs_file_path) # Re-read potentially modified code
                                        self.logger.info(f"Reloaded code from {relative_file_path} after manual edit.")
                                        write_to_file = True # Proceed to final write (which overwrites with potentially edited content)
                                    except Exception as e:
                                        self.logger.error(f"Error during manual edit process for {relative_file_path}: {e}", exc_info=True)
                                        result = StepResult(status="failed", error=f"Error during manual edit: {e}", file=relative_file_path)
                                        edit_failed = True # Mark edit as failed
                                        # Do not proceed to write
                                elif edit_choice == 'confirm':
                                    write_to_file = True # Proceed to write the generated code
                                    # 'result' still holds the default "failed" value here, but that's okay now

                                # --- Attempt to write file if confirmed or edit succeeded ---
                                if write_to_file and not edit_failed:
                                    self.cli_ui.print_thinking(f"Writing code to {relative_file_path}...")
                                    try:
                                        # Use the final 'code' variable (potentially modified by edit)
                                        success = await self.file_manager.write_file(abs_file_path, code)
                                        if not success:
                                            raise IOError("File write operation failed (returned False).")

                                        # Write successful: Update result
                                        file_hash = compute_file_hash(abs_file_path)
                                        note = "Applied via manual edit" if edit_choice == 'edit' else None
                                        result = StepResult(status="completed", file=relative_file_path, result={"file_hash": file_hash}, note=note)
                                        try:
                                            # Update dependencies only AFTER successful write
                                            await self._update_dependencies_and_analyze(relative_file_path, code)
                                        except Exception as analysis_e:
                                            self.logger.warning(f"Post-write analysis/dependency update failed for {relative_file_path}: {analysis_e}")
                                            # Log the warning but the step is still considered completed

                                    except Exception as e:
                                        # Write failed: Update result
                                        self.logger.error(f"Error writing file {abs_file_path} in step {step_idx+1}: {e}", exc_info=True)
                                        result = StepResult(status="failed", error=f"Failed to write file '{relative_file_path}': {e}", file=relative_file_path)


                elif step.type == "code_modification":
                    if not abs_file_path or not relative_file_path:
                        result = StepResult(status="failed", error="Internal error: File path not resolved for code_modification")
                    elif not await self.file_manager.file_exists(abs_file_path):
                        self.logger.error(f"File not found for modification step: {abs_file_path}")
                        result = StepResult(status="failed", error=f"File not found: {relative_file_path}", file=relative_file_path)
                    else:
                        # Proceed with modification
                        try:
                            existing_code = await self.file_manager.read_file(abs_file_path)
                        except Exception as e:
                             result = StepResult(status="failed", error=f"Error reading file '{relative_file_path}': {e}", file=relative_file_path)
                             # Go to finally block
                        else: # Reading successful
                            language = extract_language_from_path(abs_file_path)
                            self.cli_ui.print_message("Existing code snippet:", style="dim")
                            self.cli_ui.display_code(existing_code[:500] + "...", language=language, file_path=relative_file_path)
                            analysis, _ = await self._update_dependencies_and_analyze(relative_file_path, existing_code) # Analyze before modification

                            self.cli_ui.print_thinking("Generating code modifications based on plan...")
                            modifications = step.requirements or "Modify the code based on the plan and context."
                            # Pass CodeAnalysis object if available
                            # modified_code = await self.code_generator.modify(
                            #     existing_code=existing_code, modifications=modifications, analysis=analysis, language=language,
                            #     context={"task": self.current_task, "step_description": step.description}
                            # )
                            modified_code = await self.code_generator.modify(
                                existing_code=existing_code, modifications=modifications, analysis=analysis,
                                context={"task": self.current_task, "step_description": step.description}
                            )
                            
                            self.logger.debug(f"Step {step_idx + 1}: modified_code type = '{type(modified_code)}'")
                            self.logger.debug(f"Step {step_idx + 1}: modified_code value = '{modified_code}'")

                            if isinstance(modified_code, dict) and 'error' in modified_code:
                                result = StepResult(status="failed", error=f"LLM Error: {modified_code['error']}", file=relative_file_path)
                            elif not isinstance(modified_code, str):
                                result = StepResult(status="failed", error=f"LLM returned unexpected type: {type(modified_code)}", file=relative_file_path)
                            else: # Modification generated
                                self.logger.debug(f"Step {step_idx + 1}: Reached display_code")
                                self.cli_ui.display_code(modified_code, language=language, file_path=relative_file_path)
                                edit_choice = self.cli_ui.ask_edit_confirmation(relative_file_path, action="apply modifications to")
                                # INSERT THE NEW LINE HERE
                                result = StepResult(status="pending", file=relative_file_path)
                                self.logger.debug(f"Step {step_idx + 1}: edit_choice = '{edit_choice}'")
                                if edit_choice == 'cancel':
                                    result = StepResult(status="skipped", note="User cancelled action.", file=relative_file_path)
                                else:
                                    if edit_choice == 'edit':
                                        try:
                                            await self.file_manager.write_file(abs_file_path, modified_code)
                                            self.cli_ui.prompt_manual_edit(abs_file_path)
                                            modified_code = await self.file_manager.read_file(abs_file_path)
                                        except Exception as e:
                                             result = StepResult(status="failed", error=f"Error during manual edit: {e}", file=relative_file_path)
                                             # Go to finally block

                                    # Write Modified File (if confirmed or after edit, unless edit failed)
                                    if result.status != "failed":
                                        self.cli_ui.print_thinking(f"Applying modifications to {relative_file_path}...")
                                        try:
                                            success = await self.file_manager.write_file(abs_file_path, modified_code)
                                            if not success: raise IOError("File write failed")
                                            file_hash = compute_file_hash(abs_file_path)
                                            note = "Applied via manual edit" if edit_choice == 'edit' else None
                                            result = StepResult(status="completed", file=relative_file_path, result={"file_hash": file_hash}, note=note)
                                            # Run analysis AFTER successful write
                                            await self._update_dependencies_and_analyze(relative_file_path, modified_code)
                                        except Exception as e:
                                            self.logger.error(f"Error writing modified file {abs_file_path} in step {step_idx+1}: {e}", exc_info=True)
                                            result = StepResult(status="failed", error=f"Failed to write modified file '{relative_file_path}': {e}", file=relative_file_path)
                                        
                                        # --- ADD THE LOG LINE HERE ---
                                        self.logger.debug(f"Step {step_idx + 1}: Result before finally block = '{result}'")

                elif step.type == "terminal_command":
                    command = step.command
                    self.cli_ui.display_command(command)
                    if not self.cli_ui.ask_confirmation(f"Execute the above command in '[bold]{self.working_directory}[/]'?"):
                         result = StepResult(status="skipped", note="User chose not to execute command.")
                    else:
                        self.cli_ui.print_thinking(f"Executing: {command}")
                        try:
                            output_dict = await self.terminal.execute(command, cwd=self.working_directory)
                            self.cli_ui.display_command_output(output_dict)
                            status = "completed" if output_dict.get("success") else "failed"
                            error_msg = output_dict.get("stderr", "") if not output_dict.get("success") else None
                            result = StepResult(status=status, output=output_dict.get("stdout", ""), error=error_msg, result={"return_code": output_dict.get("return_code")})
                        except Exception as e:
                             self.logger.error(f"Error executing terminal command '{command}' in step {step_idx+1}: {e}", exc_info=True)
                             result = StepResult(status="failed", error=f"Failed to execute command: {e}")

                elif step.type == "code_analysis":
                    if not abs_file_path or not relative_file_path:
                         result = StepResult(status="failed", error="Internal error: File path not resolved for code_analysis")
                    else:
                        analysis_focus = step.requirements or "general"
                        analysis_success = await self._handle_direct_analysis(relative_file_path, focus=analysis_focus)
                        result = StepResult(status="completed" if analysis_success else "failed", file=relative_file_path, note=f"Analysis focus: {analysis_focus}")

                else:
                    # Should not happen if validation works
                    self.logger.error(f"Reached unknown step type execution block in step {step_idx+1}: {step.type}")
                    result = StepResult(status="failed", error=f"Internal error: Unknown step type '{step.type}'")

            except Exception as e: # Catch-all for unexpected errors during step execution logic
                 self.logger.error(f"Critical unexpected error executing step {step_idx+1}: {str(e)}", exc_info=True)
                 result = StepResult(status="failed", error=f"Unexpected Agent Error during step execution: {str(e)}")

            finally:
                # --- Finalize Step ---
                step_end_time = time.time()
                self.logger.info(f"Step {step_idx + 1} ('{step.description[:30]}...') finished with status '{result.status}' in {step_end_time - step_start_time:.2f} seconds.")
                # Store result for current run and persistent state
                self.execution_results[step_idx] = result
                self.execution_state["current_step_index"] = step_idx + 1 # Move index forward AFTER attempt
                self.execution_state["step_results"][str(step_idx)] = result.__dict__ # Update persistent state store
                await self._store_execution_state() # Save state after each step attempt
                self.cli_ui.display_step_result(step_idx, result) # Display result to user
                return result


    async def execute_plan_interactive(self, plan: Plan) -> bool:
        """Execute a plan interactively, step by step, supporting resumption."""
        if not plan or not plan.steps:
             self.cli_ui.print_error("Cannot execute an empty or invalid plan.")
             return False

        self.current_plan = plan # Store current plan being executed

        self.cli_ui.display_plan(plan)

        # Check if we are resuming and the plan looks similar (optional check)
        start_index = self.execution_state.get("current_step_index", 0)
        if start_index > 0:
             self.logger.info(f"Attempting to resume plan execution from step {start_index + 1}.")
             if not self.cli_ui.ask_confirmation(f"Resume execution from step {start_index + 1}? (Choose No to start from beginning)"):
                  self.logger.info("User chose not to resume, restarting plan from step 1.")
                  start_index = 0
                  self.execution_state["current_step_index"] = 0
                  self.execution_results = {} # Clear results if not resuming
                  self.execution_state["step_results"] = {}
                  await self._store_execution_state() # Save cleared state
        elif not self.cli_ui.ask_confirmation("Proceed with executing this plan from the beginning?"):
            self.logger.warning("User chose not to execute the plan.")
            self.cli_ui.print_message("Plan execution cancelled by user.", style="yellow")
            return False # Indicate plan was cancelled

        all_steps_succeeded_so_far = True
        for i in range(start_index, len(plan.steps)):
            step = plan.steps[i]

            # Execute the step (execute_step_interactive now handles storing results/state)
            step_result = await self.execute_step_interactive(i, step)

            if step_result.status == "failed":
                self.logger.warning(f"Step {i+1} failed. Stopping plan execution.")
                all_steps_succeeded_so_far = False
                if self.cli_ui.ask_confirmation("A step failed. Attempt to refine the plan and continue?"):
                    self.logger.info("User chose to refine the plan after failure.")
                    # refinement call returns the success status of the *refined* plan execution
                    return await self.refine_and_retry_plan_interactive()
                else:
                    self.logger.info("User chose not to refine the plan after failure.")
                    break # Stop execution of the current plan
            # No need to check for skipped, just continue

        # If loop completes or breaks after user chooses not to refine
        return all_steps_succeeded_so_far


    async def refine_and_retry_plan_interactive(self) -> bool:
        """Attempt to refine the plan after a failure and execute the new plan."""
        if not self.current_plan: # Need the original plan for context
            self.cli_ui.print_error("Cannot refine plan: No current plan available.")
            return False

        # execution_results should contain results up to the failure point
        if not self.execution_results:
            self.cli_ui.print_warning("Cannot refine plan: No execution results recorded.")
            # Maybe still allow refinement based on just the plan? Risky.
            return False

        self.cli_ui.print_thinking("Refining the plan based on execution results...")
        self.logger.info("Attempting plan refinement...")

        try:
            # Prepare data for the refinement prompt
            initial_plan_dict = {
                "understanding": self.current_plan.understanding,
                "files": self.current_plan.files,
                "steps": [s.to_dict() for s in self.current_plan.steps]
            }
            # Serialize current execution results for the prompt
            results_dict_for_llm = {}
            for idx, res in self.execution_results.items():
                 # Create a serializable version, maybe exclude large outputs
                 res_data = res.__dict__.copy()
                 if res_data.get('output') and len(res_data['output']) > 500: # Limit output length
                     res_data['output'] = res_data['output'][:500] + "..."
                 results_dict_for_llm[idx] = {k: v for k, v in res_data.items() if v is not None}


            # Call the planner's refine method
            # This method should exist in Planner class and accept these arguments
            refined_plan_response = await self.planner.refine_plan_with_results(
                 initial_plan_json=json.dumps(initial_plan_dict, default=str),
                 results_json=json.dumps(results_dict_for_llm, default=str),
                 feedback="A step failed during execution. Please revise the plan to fix the issue and achieve the original goal."
            )

            # Handle response (string error or dict plan)
            if isinstance(refined_plan_response, str):
                 self.logger.warning(f"Plan refinement failed or was conversational: {refined_plan_response}")
                 self.cli_ui.print_error(f"Plan refinement failed: {refined_plan_response}")
                 return False # Refinement failed

            elif isinstance(refined_plan_response, dict):
                 refined_plan_dict = refined_plan_response
                 try:
                     # Parse and validate the refined plan dict
                     refined_steps = [Step.from_dict(step_data) for step_data in refined_plan_dict.get("steps", [])]
                     if not refined_steps: raise ValueError("Refined plan has no steps.")
                     refined_plan = Plan(
                         understanding=refined_plan_dict.get("understanding", "N/A - Refined"),
                         files=refined_plan_dict.get("files", []),
                         steps=refined_steps
                     )
                     self.logger.info("Plan refinement successful.")
                     self.cli_ui.print_message("Plan refined.", style="bold magenta")
                     if self.redis: await self._store_context("refined_plan", refined_plan_dict)

                 except Exception as e:
                     self.logger.error(f"Failed to parse refined plan: {e}", exc_info=True)
                     self.cli_ui.print_error(f"Failed to parse the refined plan from LLM: {e}")
                     return False # Parsing failed

                 # --- Execute the REFINED plan ---
                 # Reset execution state for the refined plan run
                 self.logger.info("Executing refined plan...")
                 self.execution_state = {"current_step_index": 0, "step_results": {}} # Reset state
                 self.execution_results = {} # Reset results for the new plan run
                 await self._store_execution_state() # Save reset state

                 # The overall success now depends on this refined plan execution
                 return await self.execute_plan_interactive(refined_plan)
            else:
                self.logger.error(f"Refinement returned unexpected type: {type(refined_plan_response)}")
                self.cli_ui.print_error("Plan refinement returned an unexpected result type.")
                return False

        except Exception as e:
            self.logger.error(f"Error during plan refinement process: {e}", exc_info=True)
            self.cli_ui.print_error(f"Failed to refine the plan: {e}")
            return False


    # --- Dependency & Analysis Helper ---
    async def _update_dependencies_and_analyze(self, file_path: str, code: Optional[str] = None) -> tuple[Optional[CodeAnalysis], List[str]]:
        """Helper to update dependencies and perform basic analysis after file change. Uses relative path."""
        analysis: Optional[CodeAnalysis] = None
        dependencies: List[str] = []

        if not self.ast_parser:
             # self.logger.warning("AST Parser not available, skipping dependency update and analysis.")
             return None, [] # Silently skip if no parser

        try:
            # Resolve path once
            abs_file_path = self.file_manager._resolve_path(file_path)
            # Ensure it's still within workspace (should be checked before calling this usually)
            if not abs_file_path.startswith(os.path.abspath(self.working_directory)):
                 self.logger.error(f"Attempted analysis outside workspace: {abs_file_path}")
                 return None, []

            relative_path = os.path.relpath(abs_file_path, self.working_directory)

            if code is None:
                if not await self.file_manager.file_exists(abs_file_path):
                     # self.logger.warning(f"File not found for analysis: {abs_file_path}")
                     return None, [] # Silently skip if file gone
                code = await self.file_manager.read_file(abs_file_path)

            language = extract_language_from_path(abs_file_path)

            if language != "unknown" and language in self.ast_parser.SUPPORTED_LANGUAGES:
                 # Update Dependency Graph using relative path
                 try:
                     dependencies = self.ast_parser.find_dependencies(code, language)
                     self.dependency_manager.add_file(relative_path, dependencies)
                     # Only log/display if dependencies change maybe? Less noise.
                     # dependents = self.dependency_manager.get_dependents(relative_path)
                     # self.cli_ui.display_dependencies(relative_path, dependencies, dependents)
                     self.logger.debug(f"Updated dependencies for {relative_path}: {len(dependencies)} found.")
                 except Exception as e:
                      self.logger.error(f"ASTParser failed to find dependencies for {relative_path}: {e}", exc_info=True)

                 # Perform Code Analysis using relative path
                 try:
                     analysis = await self.code_analyzer.analyze(code, relative_path) # Use relative path
                     self.logger.debug(f"Performed analysis for {relative_path}")
                     # Display only if issues found? Less noise.
                     # self.cli_ui.display_analysis_summary(analysis)
                 except Exception as e:
                      self.logger.error(f"CodeAnalyzer failed for {relative_path}: {e}", exc_info=True)
                      analysis = None # Ensure analysis is None if it fails

                 # Store analysis/metadata in Redis if enabled
                 if self.redis:
                     try:
                         # Use latest analysis result
                         analysis_dict = analysis.__dict__ if analysis else None
                         file_hash = compute_file_hash(abs_file_path)
                         file_info = {
                             "path": relative_path, "language": language, "dependencies": dependencies,
                             "hash": file_hash, "task_id": self.task_id,
                             "analysis": analysis_dict, "timestamp": time.time()
                         }
                         await self.redis.track_file(relative_path, file_info)
                         # Track snippet removed for brevity, can be added back
                         self.logger.debug(f"Stored file info in Redis for {relative_path}")
                     except Exception as e:
                          self.logger.error(f"Failed to store file info in Redis for {relative_path}: {e}", exc_info=True)
            else:
                 self.logger.debug(f"Unsupported language '{language}' for {relative_path}, skipping AST analysis.")

            return analysis, dependencies

        except FileNotFoundError:
             # self.logger.warning(f"File not found during analysis helper: {file_path}")
             return None, [] # Silently fail
        except Exception as e:
            self.logger.error(f"Error during _update_dependencies_and_analyze for {file_path}: {e}", exc_info=True)
            # self.cli_ui.print_warning(f"Could not analyze or update dependencies for {file_path}.")
            return None, []


    # --- Cleanup ---
    async def cleanup(self):
        """Perform cleanup actions when the agent exits."""
        self.logger.info("Performing agent cleanup...")
        if self.redis:
            try:
                await self.redis.close()
                self.logger.info("Redis connection closed.")
            except Exception as e:
                self.logger.error(f"Error closing Redis connection: {e}")
        self.logger.info("--- Agent Shutdown ---")