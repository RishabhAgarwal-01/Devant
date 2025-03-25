# """
# Agent orchestrator for the AI Coding Agent with async support
# """
# import os
# import asyncio
# from typing import Dict, List, Optional, Any

# from core.planner import Planner
# from core.code_generator import CodeGenerator
# from core.code_analyzer import CodeAnalyzer
# from core.file_manager import FileManager
# from adapters.terminal_adapter import TerminalAdapter
# from adapters.llm_adapter import LLMAdapter
# from utils.schema import Plan, Step, StepResult
# from utils.helpers import save_json, compute_file_hash
# from utils.logger import get_logger  # Updated import

# class Agent:
#     def __init__(self, config: Dict[str, Any]):
#         self.logger = get_logger(__name__)  # Updated logger retrieval
#         self.config = config
        
#         # Initialize adapters
#         self.llm = LLMAdapter(config["llm"])
#         self.terminal = TerminalAdapter()
        
#         # Initialize core components
#         self.planner = Planner(self.llm)
#         self.code_generator = CodeGenerator(self.llm)
#         self.code_analyzer = CodeAnalyzer(self.llm)
#         self.file_manager = FileManager()
        
#         # Current state
#         self.current_task = None
#         self.working_directory = config.get("working_directory", ".")
        
#         # Concurrency settings
#         self.max_workers = config.get("concurrency", {}).get("max_workers", 5)
#         self.semaphore = asyncio.Semaphore(self.max_workers)
        
#     def set_task(self, task_description: str):
#         """Set the current task for the agent to work on."""
#         self.current_task = task_description
#         self.logger.info(f"New task set: {task_description}")
        
#     async def plan(self) -> Plan:
#         """Create a plan for the current task asynchronously."""
#         if not self.current_task:
#             raise ValueError("No task has been set")
        
#         self.logger.info("Creating plan for current task")
#         plan_dict = await self.planner.create_plan(self.current_task)
        
#         # Save the plan to a JSON file for reference
#         save_json(plan_dict, os.path.join(self.working_directory, "plan.json"))
        
#         # Convert dictionary to Plan object
#         steps = [Step(**step) for step in plan_dict["steps"]]
#         return Plan(
#             understanding=plan_dict["understanding"],
#             files=plan_dict["files"],
#             steps=steps
#         )
    
#     async def execute_step(self, step_idx: int, step: Step) -> Dict[str, Any]:
#         """Execute a single step from the plan asynchronously."""
#         async with self.semaphore:
#             self.logger.info(f"Executing step {step_idx+1}: {step.description}")
            
#             if step.type == "code_generation":
#                 file_path = step.file_path
#                 code = await self.code_generator.generate(step.requirements, getattr(step, "context", None))
#                 await self.file_manager.write_file(file_path, code)
#                 return {"status": "completed", "file": file_path}
                
#             elif step.type == "code_modification":
#                 file_path = step.file_path
#                 try:
#                     current_code = await self.file_manager.read_file(file_path)
#                     analysis = await self.code_analyzer.analyze(current_code)
#                     modified_code = await self.code_generator.modify(
#                         current_code, 
#                         getattr(step, "modifications", ""),  # Default to empty string if missing
#                         analysis
#                     )
#                     await self.file_manager.write_file(file_path, modified_code)
#                     return {"status": "completed", "file": file_path}
#                 except FileNotFoundError:
#                     self.logger.warning(f"File {file_path} not found for modification. Creating new file instead.")
#                     code = await self.code_generator.generate(getattr(step, "modifications", ""))
#                     await self.file_manager.write_file(file_path, code)
#                     return {"status": "completed", "file": file_path, "note": "Created new file instead of modifying"}
                
#             elif step.type == "terminal_command":
#                 command = step.command
#                 output = await self.terminal.execute(command, cwd=self.working_directory)
#                 return {"status": "completed", "output": output}
        
#             else:
#                 self.logger.warning(f"Unknown step type: {step.type}")
#                 return {"status": "skipped", "reason": f"Unknown step type: {step.type}"}
    
#     async def execute_plan(self, plan: Plan) -> Dict[str, Any]:
#         """Execute a generated plan asynchronously."""
#         results = {}
        
#         # Log the plan
#         self.logger.info(f"Executing plan: {plan.understanding}")
#         self.logger.info(f"Files to create/modify: {plan.files}")
        
#         # Execute steps with potential parallelism
#         tasks = []
#         for step_idx, step in enumerate(plan.steps):
#             tasks.append(self.execute_step(step_idx, step))
        
#         # Wait for all tasks to complete
#         step_results = await asyncio.gather(*tasks, return_exceptions=True)
        
#         # Process results
#         for step_idx, result in enumerate(step_results):
#             if isinstance(result, Exception):
#                 self.logger.error(f"Step {step_idx+1} failed with error: {str(result)}")
#                 results[f"step_{step_idx+1}"] = {"status": "failed", "error": str(result)}
#             else:
#                 results[f"step_{step_idx+1}"] = result
        
#         return results
    
#     async def run(self, task_description: str) -> Dict[str, Any]:
#         """Run the complete agent workflow on a task asynchronously."""
#         self.set_task(task_description)
#         plan = await self.plan()
#         return await self.execute_plan(plan)

"""
Agent orchestrator for the AI Coding Agent with async support
"""
import logging
import asyncio
from typing import Dict, List, Optional, Any
import os
from core.planner import Planner
from core.code_generator import CodeGenerator
from core.code_analyzer import CodeAnalyzer
from core.file_manager import FileManager
from adapters.terminal_adapter import TerminalAdapter
# from ..adapters.vscode_adapter import VSCodeAdapter
from adapters.llm_adapter import LLMAdapter
from utils.schema import Plan, Step, StepResult  # Import schema classes
from utils.helpers import save_json, compute_file_hash  # Import helper functions

class Agent:
    def __init__(self, config: Dict[str, Any]):
        self.logger = logging.getLogger(__name__)
        self.config = config
        
        # Initialize adapters
        self.llm = LLMAdapter(config["llm"])
        self.terminal = TerminalAdapter()
        # self.vscode = VSCodeAdapter(config["vscode"])
        
        # Initialize core components
        self.working_directory = config.get("working_directory", ".")
        self.planner = Planner(self.llm)
        self.code_generator = CodeGenerator(self.llm)
        self.code_analyzer = CodeAnalyzer(self.llm)
        self.file_manager = FileManager(self.working_directory)
        
        # Current state
        self.current_task = None
        self.working_directory = config.get("working_directory", ".")
        
        # Concurrency settings
        self.max_workers = config.get("concurrency", {}).get("max_workers", 5)
        self.semaphore = asyncio.Semaphore(self.max_workers)
        
    def set_task(self, task_description: str):
        """Set the current task for the agent to work on."""
        self.current_task = task_description
        self.logger.info(f"New task set: {task_description}")
        
    async def plan(self) -> Plan:  # Updated return type
        """Create a plan for the current task asynchronously."""
        if not self.current_task:
            raise ValueError("No task has been set")
        
        self.logger.info("Creating plan for current task")
        plan_dict = await self.planner.create_plan(self.current_task)
        
        # Save the plan to a JSON file for reference
        save_json(plan_dict, os.path.join(self.working_directory, "plan.json"))
        
        # Convert dictionary to Plan object
        steps = [Step(**step) for step in plan_dict["steps"]]
        return Plan(
            understanding=plan_dict["understanding"],
            files=plan_dict["files"],
            steps=steps
        )
    
    async def execute_step(self, step_idx: int, step: Step) -> StepResult:  # Updated parameter and return type
        """Execute a single step from the plan asynchronously."""
        async with self.semaphore:
            self.logger.info(f"Executing step {step_idx+1}: {step.description}")
            
            if step.type == "code_generation":
                file_path = step.file_path
                code = await self.code_generator.generate(step.requirements, step.params)
                await self.file_manager.write_file(file_path, code)
                
                # Compute file hash for verification
                file_hash = compute_file_hash(file_path)
                return StepResult(status="completed", file=file_path, result={"file_hash": file_hash})
                
            elif step.type == "code_modification":
                file_path = step.file_path
                try:
                    current_code = await self.file_manager.read_file(file_path)
                    analysis = await self.code_analyzer.analyze(current_code)
                    modified_code = await self.code_generator.modify(
                        current_code, 
                        step.requirements,
                        analysis
                    )
                    await self.file_manager.write_file(file_path, modified_code)
                    
                    # Compute file hash for verification
                    file_hash = compute_file_hash(file_path)
                    return StepResult(status="completed", file=file_path, result={"file_hash": file_hash})
                except FileNotFoundError:
                    self.logger.warning(f"File {file_path} not found for modification. Creating new file instead.")
                    code = await self.code_generator.generate(step.requirements)
                    await self.file_manager.write_file(file_path, code)
                    return StepResult(status="completed", file=file_path, note="Created new file instead of modifying")
                
            elif step.type == "terminal_command":
                command = step.command
                output_dict = await self.terminal.execute(command, cwd=self.working_directory)
                return StepResult(status="completed", output=output_dict.get("stdout", ""))
                
            # elif step.type == "vscode_action":
            #     action = step.action
            #     params = step.params or {}
            #     result_dict = await self.vscode.execute_action(action, params)
            #     return StepResult(status="completed", result=result_dict)
            
            else:
                self.logger.warning(f"Unknown step type: {step.type}")
                return StepResult(status="skipped", note=f"Unknown step type: {step.type}")
    
    async def execute_plan(self, plan: Plan) -> Dict[str, Any]:  # Updated parameter type
        """Execute a generated plan asynchronously."""
        results = {}
        
        # Log the plan
        self.logger.info(f"Executing plan: {plan.understanding}")
        self.logger.info(f"Files to create/modify: {plan.files}")
        
        # Execute steps with potential parallelism
        tasks = []
        for step_idx, step in enumerate(plan.steps):
            tasks.append(self.execute_step(step_idx, step))
        
        # Wait for all tasks to complete
        step_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for step_idx, result in enumerate(step_results):
            if isinstance(result, Exception):
                self.logger.error(f"Step {step_idx+1} failed with error: {str(result)}")
                results[f"step_{step_idx+1}"] = StepResult(status="failed", error=str(result)).__dict__
            else:
                results[f"step_{step_idx+1}"] = result.__dict__
        
        return results
    
    async def run(self, task_description: str) -> Dict[str, Any]:
        """Run the complete agent workflow on a task asynchronously."""
        import os
        from utils.helpers import save_json  # Import here to avoid circular imports
        
        self.set_task(task_description)
        plan = await self.plan()
        results = await self.execute_plan(plan)
        
        # Save results to a file
        results_path = os.path.join(self.working_directory, "execution_results.json")
        save_json(results, results_path)
        self.logger.info(f"Execution results saved to {results_path}")
        
        return results
