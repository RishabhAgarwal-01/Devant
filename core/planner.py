"""Planner for the AI Coding Agent with async support"""
from typing import Dict, List, Any
from adapters.llm_adapter import LLMAdapter
from utils.schema import Plan, Step  # Import schema classes
from config.prompts import PROMPTS

class Planner:
    
    def __init__(self, llm_adapter:LLMAdapter):
        self.llm = llm_adapter
    
    # Create a structured plan from a task description asynchronously
    async def create_plan(self, task_description:str) -> Dict[str, Any]:
        prompt = PROMPTS["planner"]["create_plan"].format(task_description=task_description)

        plan_json = await self.llm.generate(prompt, formated_output="json")

        # Validate the plan structure
        if not isinstance(plan_json, dict):
            raise ValueError("Generated plan is not a valid JSON object")
        
        if "understanding" not in plan_json or "files" not in plan_json or "steps" not in plan_json:
            raise ValueError("Generated plan is missing required fields")
        
        if not isinstance(plan_json["steps"], list) or len(plan_json["steps"]) == 0:
            raise ValueError("Generated plan has no steps")
        
        return plan_json

    # Refine an existing plan based on feedback asynchronously
    async def refine_plan(self, initial_plan:Plan, feedback:str) -> Plan:
        # Convert Plan object to dictionary for the prompt
        initial_plan_dict = {
            "understanding": initial_plan.understanding,
            "files": initial_plan.files,
            "steps": [step.__dict__ for step in initial_plan.steps]
        }
        
        prompt = f"""
        Initial Plan: {initial_plan_dict}
        
        Feedback: {feedback}
        
        Please refine the plan based on this feedback. Keep the same JSON structure.
        """
        
        refined_plan_dict = await self.llm.generate(prompt, formated_output="json")
        
        # Convert the refined plan dictionary back to a Plan object
        steps = [Step(**step) for step in refined_plan_dict["steps"]]
        return Plan(
            understanding=refined_plan_dict["understanding"],
            files=refined_plan_dict["files"],
            steps=steps
        )