# """Planner for the AI Coding Agent with async support"""
# from typing import Dict, List, Any, Optional
# from adapters.llm_adapter import LLMAdapter
# from adapters.redis_adapter import RedisAdapter
# from utils.schema import Plan, Step
# from config.prompts import PROMPTS
# from utils.logger import get_logger
# import json

# class Planner:
#     def __init__(self, llm_adapter: LLMAdapter, redis_adapter: Optional[RedisAdapter] = None):
#         self.llm = llm_adapter
#         self.redis = redis_adapter
#         self.logger = get_logger(__name__)
    
#     async def create_plan(self, task_description: str) -> Plan:
#         """Create a structured plan with context awareness"""
#         # Get relevant context from Redis if available
#         context = {}
#         if self.redis:
#             context = await self.redis.search_context(task_description[:50])
        
#         prompt = PROMPTS["planner"]["create_plan"].format(
#             task_description=task_description,
#             context=json.dumps(context) if context else "No relevant context found"
#         )

#         plan_json = await self.llm.generate(prompt, formated_output="json")

#         # Validate the plan structure
#         if not isinstance(plan_json, dict):
#             raise ValueError("Generated plan is not a valid JSON object")
        
#         required_fields = ["understanding", "files", "steps"]
#         if any(field not in plan_json for field in required_fields):
#             raise ValueError("Generated plan is missing required fields")
        
#         if not isinstance(plan_json["steps"], list) or len(plan_json["steps"]) == 0:
#             raise ValueError("Generated plan has no steps")
        
#         # Convert steps to Step objects with validation
#         steps = []
#         for step_data in plan_json["steps"]:
#             try:
#                 # Add validation for code generation steps
#                 if step_data.get("type") in ["code_generation", "code_modification"]:
#                     if not step_data.get("file_path"):
#                         raise ValueError(f"Step of type {step_data.get('type')} requires file_path")
#                     if not step_data.get("requirements"):
#                         raise ValueError(f"Step of type {step_data.get('type')} requires requirements")
                
#                 step = Step(**step_data)
#                 steps.append(step)
#             except Exception as e:
#                 self.logger.warning(f"Invalid step skipped: {str(e)}")
#                 continue
        
#         if not steps:
#             raise ValueError("No valid steps in generated plan")
        
#         return Plan(
#             understanding=plan_json["understanding"],
#             files=plan_json["files"],
#             steps=steps
#         )

#     async def refine_plan(self, initial_plan: Plan, feedback: str) -> Plan:
#         """Refine an existing plan based on feedback with context"""
#         # Get execution context from Redis if available
#         execution_context = {}
#         if self.redis:
#             execution_context = {
#                 "completed_steps": await self.redis.get_context("completed_steps"),
#                 "failed_steps": await self.redis.get_context("failed_steps"),
#                 "generated_files": await self.redis.get_context("generated_files")
#             }
        
#         # Convert Plan object to dictionary using to_dict()
#         initial_plan_dict = {
#             "understanding": initial_plan.understanding,
#             "files": initial_plan.files,
#             "steps": [step.to_dict() for step in initial_plan.steps]
#         }
        
#         prompt = f"""
#         Initial Plan: {json.dumps(initial_plan_dict, indent=2)}
        
#         Execution Context: {json.dumps(execution_context, indent=2)}
        
#         Feedback: {feedback}
        
#         Please refine the plan based on this feedback. Keep the same JSON structure.
#         For code generation steps, you MUST include:
#         - file_path: A valid relative path (e.g., "app/main.py")
#         - requirements: Detailed specifications
#         """
        
#         refined_plan_dict = await self.llm.generate(prompt, formated_output="json")
        
#         # Validate the refined plan structure
#         if not isinstance(refined_plan_dict, dict):
#             raise ValueError("Refined plan is not a valid JSON object")
        
#         # Convert the refined plan dictionary back to a Plan object with validation
#         steps = []
#         for step_data in refined_plan_dict.get("steps", []):
#             try:
#                 # Validate required fields for code steps
#                 if step_data.get("type") in ["code_generation", "code_modification"]:
#                     if not step_data.get("file_path"):
#                         self.logger.warning("Skipping step missing file_path")
#                         continue
#                     if not step_data.get("requirements"):
#                         self.logger.warning("Skipping step missing requirements")
#                         continue
                
#                 step = Step(**step_data)
#                 steps.append(step)
#             except Exception as e:
#                 self.logger.warning(f"Invalid step in refined plan: {str(e)}")
#                 continue
        
#         if not steps:
#             raise ValueError("Refined plan contains no valid steps")
        
#         return Plan(
#             understanding=refined_plan_dict.get("understanding", "No understanding provided"),
#             files=refined_plan_dict.get("files", []),
#             steps=steps
#         )


# core/planner.py
"""Planner for the AI Coding Agent with async support"""
import json
import logging # Import logging
from typing import Dict, List, Any, Optional, Union
from adapters.llm_adapter import LLMAdapter
from adapters.redis_adapter import RedisAdapter
from utils.schema import Plan, Step
from config.prompts import PROMPTS
from utils.logger import get_logger

class Planner:
    def __init__(self, llm_adapter: LLMAdapter, redis_adapter: Optional[RedisAdapter] = None):
        self.llm = llm_adapter
        self.redis = redis_adapter # Keep redis adapter if needed for context or other features
        self.logger = get_logger(__name__)

    async def create_plan(self, task_description: str, context: Optional[Dict] = None) -> Union[Plan, str]:
        """
        Create a structured plan based on the task description and provided context.
        Can return a Plan object or a conversational string.
        """
        # Use the context provided by the agent, or default to "No context provided"
        context_str = json.dumps(context, indent=2) if context else "No additional context provided"
        self.logger.debug(f"Creating plan with context: {context_str[:200]}...")

        prompt = PROMPTS["planner"]["create_plan"].format(
            task_description=task_description,
            context=context_str
        )

        # Generate response using LLM
        # Let the LLM decide whether to return JSON plan or conversational string based on the prompt instructions
        llm_response = await self.llm.generate(prompt, formated_output=None) # Get raw response first

        # --- Response Processing ---
        if not llm_response or isinstance(llm_response, dict) and 'error' in llm_response:
             error_msg = llm_response.get('error', 'Unknown LLM error') if isinstance(llm_response, dict) else "Empty response from LLM"
             self.logger.error(f"LLM failed during plan creation: {error_msg}")
             return f"Sorry, I encountered an error trying to create a plan: {error_msg}"

        # Try parsing as JSON (plan)
        try:
            # Attempt to find JSON block even if there's surrounding text (more robust)
            json_start = llm_response.find('{')
            json_end = llm_response.rfind('}') + 1
            plan_json = None
            if json_start != -1 and json_end > json_start:
                 plan_json_str = llm_response[json_start:json_end]
                 try:
                      plan_json = json.loads(plan_json_str)
                 except json.JSONDecodeError:
                      self.logger.warning(f"Found JSON-like structure but failed to parse. Treating as conversational. Response: {llm_response[:200]}...")
                      # Fall through to treat as conversational

            # If no JSON object found or parsing failed, assume it's conversational
            if plan_json is None:
                 self.logger.info("Planner response seems conversational (no valid JSON object found).")
                 return llm_response.strip() # Return the cleaned string

            # --- Plan Validation ---
            if not isinstance(plan_json, dict):
                 # Should not happen if json.loads succeeded, but check anyway
                 raise ValueError("Parsed plan is not a valid JSON object")

            required_fields = ["understanding", "files", "steps"]
            if any(field not in plan_json for field in required_fields):
                 self.logger.warning(f"Generated JSON missing required fields (understanding, files, steps). Treating as conversational. JSON: {plan_json_str[:200]}")
                 return llm_response.strip() # Return the original LLM string

            if not isinstance(plan_json.get("steps"), list) or not plan_json.get("steps"):
                  self.logger.warning(f"Generated plan has no steps. Treating as conversational. JSON: {plan_json_str[:200]}")
                  return llm_response.strip()

            # Convert steps to Step objects with validation
            steps = []
            for step_data in plan_json["steps"]:
                try:
                    # Basic validation within planner
                    if step_data.get("type") in ["code_generation", "code_modification", "code_analysis"]:
                       if not step_data.get("file_path"):
                           raise ValueError(f"Step type '{step_data.get('type')}' requires 'file_path'")
                    elif step_data.get("type") == "terminal_command":
                        if not step_data.get("command"):
                            raise ValueError("Step type 'terminal_command' requires 'command'")
                    elif not step_data.get("type"):
                        raise ValueError("Step is missing required 'type' field.")

                    step = Step.from_dict(step_data) # Use classmethod
                    steps.append(step)
                except Exception as e:
                    self.logger.warning(f"Invalid step skipped during plan creation: {step_data}. Error: {e}", exc_info=True)
                    continue # Skip invalid steps

            if not steps: # If all steps were invalid
                 self.logger.error(f"Plan generation resulted in no valid steps. Raw response: {llm_response[:500]}")
                 return "I couldn't create a valid plan with actionable steps for that task."

            # --- Return Plan Object ---
            return Plan(
                understanding=plan_json["understanding"],
                files=plan_json.get("files", []) or [], # Ensure files is a list
                steps=steps
            )

        except Exception as e:
             self.logger.error(f"Unexpected error during plan creation or parsing: {e}", exc_info=True)
             return f"Sorry, I encountered an unexpected error while processing the plan: {e}"


    async def refine_plan_with_results(self, initial_plan_json: str, results_json: str, feedback: str) -> Union[Dict, str]:
         """
         Refines a plan based on execution results using the LLM.
         Returns a dictionary representing the refined plan JSON or a conversational error string.
         """
         self.logger.debug("Attempting plan refinement...")
         try:
             prompt = PROMPTS["planner"]["refine_plan"].format(
                 initial_plan_json=initial_plan_json,
                 results_json=results_json,
                 feedback=feedback
             )
             # Use formated_output="json" as refine_plan prompt specifically requests JSON
             refined_plan_response = await self.llm.generate(prompt, formated_output="json")

             # Check for LLM errors
             if isinstance(refined_plan_response, dict) and 'error' in refined_plan_response:
                  error_msg = refined_plan_response['error']
                  self.logger.error(f"LLM refinement failed: {error_msg}")
                  return f"Sorry, I encountered an error while trying to refine the plan: {error_msg}"

             # Basic validation of the response structure
             if not isinstance(refined_plan_response, dict) or not refined_plan_response.get("steps"):
                  self.logger.warning(f"Refined plan from LLM is invalid or has no steps: {refined_plan_response}")
                  return "I couldn't generate a valid refinement for the plan. The response was not structured correctly or had no steps."

             # --- Deeper Validation (Optional but Recommended) ---
             # Validate steps within the refined plan dict before returning
             validated_steps = []
             invalid_step_count = 0
             for i, step_data in enumerate(refined_plan_response.get("steps", [])):
                 try:
                     # Attempt to create a Step object to validate structure
                     Step.from_dict(step_data)
                     validated_steps.append(step_data) # Keep the dict format
                 except Exception as e:
                      invalid_step_count += 1
                      self.logger.warning(f"Invalid step found in refined plan (Step {i+1}): {step_data}. Error: {e}")

             if invalid_step_count > 0:
                 self.logger.warning(f"Refined plan contained {invalid_step_count} invalid steps.")
                 # Decide whether to return partial plan or fail
                 # For now, let's return the dict but log the warning

             # Return the dictionary representing the refined plan
             # The Agent is responsible for parsing this dict back into a Plan object
             return refined_plan_response

         except Exception as e:
             self.logger.error(f"Unexpected error during plan refinement process: {e}", exc_info=True)
             return f"Sorry, an unexpected error occurred during plan refinement: {e}"