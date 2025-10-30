# """
# Prompt library for the AI Coding Agent
# """
# # System prompts for the AI agent's various tasks
# PROMPTS = {
#     "planner": {
#         "create_plan": """
#         Task: {task_description}
        
#         Create a detailed plan for completing this coding task. The plan should include:
#         1. An overall understanding of what needs to be built
#         2. A breakdown of files that need to be created or modified
#         3. A sequence of specific steps to take
        
#         For each step, specify:
#         - Step type (code_generation, code_modification, terminal_command, vscode_action)
#         - Detailed description of what should happen in this step
#         - Any specific requirements or constraints
#         - Expected output or result
        
#         Format your response as a JSON object with the following structure:
#         {{
#             "understanding": "description of the overall task",
#             "files": ["list", "of", "files", "to", "create", "or", "modify"],
#             "steps": [
#                 {{
#                     "type": "step_type",
#                     "description": "what this step does",
#                     "requirements": "specific requirements",
#                     "file_path": "path/to/file" (if applicable),
#                     "command": "command to run" (if applicable),
#                     "action": "vscode action" (if applicable),
#                     "params": {{}} (if applicable)
#                 }}
#             ]
#         }}
#         """
#     },
    
#     "code_generator": {
#         "generate": """
#         Requirements: {requirements}
        
#         {context}
        
#         Generate code that fulfills these requirements. Use best practices and write clean, 
#         efficient, and well-documented code. Include appropriate error handling and tests where necessary.
#         Implement async/await patterns where appropriate for better performance.
        
#         Return only the code without any additional explanation:
#         """,
        
#         "modify": """
#         Existing Code:
#         ```
#         {existing_code}
#         ```
        
#         Required Modifications: {modifications}
        
#         {analysis}
        
#         Modify the existing code according to the required modifications. Maintain the overall structure 
#         and style of the code unless specifically asked to change it. Include clear comments for significant changes.
#         Implement async/await patterns where appropriate for better performance.
        
#         Return the complete modified code without any additional explanation:
#         """
#     },
    
#     "code_analyzer": {
#         "analyze": """
#         Analyze the following code and provide a structured breakdown:
        
#         ```
#         {code}
#         ```
        
#         Extract and return the following information in JSON format:
#         1. Language detected
#         2. Imports and dependencies
#         3. Functions/classes/methods defined
#         4. Function signatures with parameter types (if detectable)
#         5. Main execution flow
#         6. Potential issues or antipatterns
#         7. Whether the code uses async/await patterns
        
#         Format as JSON only:
#         """
#     }
# }





# """
# Prompt library for the AI Coding Agent
# """
# # System prompts for the AI agent's various tasks without vscode action
# PROMPTS = {
#     "planner": {
#     "create_plan": """
#         Task: {task_description}
        
#         Create a detailed, executable plan for completing this coding task. The plan MUST include:
#         1. Clear understanding of the overall task
#         2. Complete list of files needed (with paths)
#         3. Specific, actionable steps
        
#         FOR CODE GENERATION STEPS YOU MUST INCLUDE:
#         - type: "code_generation"
#         - file_path: Relative path (e.g., "app/main.py", "models/weather.py")
#         - requirements: Detailed specifications including:
#         * Required imports
#         * Function signatures
#         * Expected behavior
#         * Error handling
#         * Any dependencies
        
#         FOR CODE MODIFICATION STEPS YOU MUST INCLUDE:
#         - type: "code_modification" 
#         - file_path: Path to existing file
#         - requirements: Exact changes needed
#         - Expected result
        
#         FOR TERMINAL COMMANDS:
#         - type: "terminal_command"
#         - command: Exact command to run
#         - Expected result
        
#         EXAMPLE STEP FOR FASTAPI:
#         {{
#             "type": "code_generation",
#             "file_path": "app/main.py",
#             "description": "Create main FastAPI application file",
#             "requirements": "Create FastAPI app with:\\n- GET /weather endpoint\\n- City parameter validation\\n- Error handling\\n- Async database connection",
#             "params": {{}}
#         }}
        
#         Return ONLY valid JSON with this structure:
#         {{
#             "understanding": "clear_description",
#             "files": ["complete_file_list"],
#             "steps": [
#                 {{
#                     "type": "step_type",
#                     "description": "what_this_step_does",
#                     "requirements": "specific_requirements",
#                     "file_path": "path/if_applicable",
#                     "command": "command_if_applicable",
#                     "params": {{}}
#                 }}
#             ]
#         }}
#         """, 
#     "refine_plan": """
#         Based on the execution results, refine the plan. Consider:
#         - Which steps succeeded/failed
#         - What needs to be modified
#         - Any new steps needed

#         Return ONLY JSON with this structure:
#         {{
#             "understanding": "updated_understanding",
#             "files": ["updated_file_list"],
#             "steps": [
#                 {{
#                     "type": "step_type",
#                     "description": "updated_description",
#                     "requirements": "updated_requirements",
#                     "file_path": "path_if_applicable",
#                     "command": "command_if_applicable"
#                 }}
#             ]
#         }}
#         """
#     },
    
    
#     "code_generator": {
#         "generate": """
#         Requirements: {requirements}
        
#         {context}
        
#         Generate code that fulfills these requirements. Use best practices and write clean, 
#         efficient, and well-documented code. Include appropriate error handling and tests where necessary.
#         Implement async/await patterns where appropriate for better performance.
        
#         Return only the code without any additional explanation:
#         """,
        
#         "modify": """
#         Existing Code:
#         ```
#         {existing_code}
#         ```
        
#         Required Modifications: {modifications}
        
#         {analysis}
        
#         Modify the existing code according to the required modifications. Maintain the overall structure 
#         and style of the code unless specifically asked to change it. Include clear comments for significant changes.
#         Implement async/await patterns where appropriate for better performance.
        
#         Return the complete modified code without any additional explanation:
#         """
#     },
    
#     "code_analyzer": {
#         "analyze": """
#         Analyze the following code and provide a structured breakdown:
        
#         ```
#         {code}
#         ```
        
#         Extract and return the following information in JSON format:
#         1. Language
#         2. Imports and dependencies
#         3. Functions/classes/methods defined
#         4. Function signatures with parameter types (if detectable)
#         5. Main execution flow
#         6. Potential issues or antipatterns
#         7. Whether the code uses async/await patterns
        
#         Format as JSON only:
#         """
#     },
#     "improvement": {
#         "analyze_quality": """
#         Analyze the following code and provide quality metrics (0-1 scale):
#         - Code Quality (structure, readability, style)
#         - Test Coverage (presence of tests)
#         - Performance (efficiency considerations)
#         - Modularity (proper separation of concerns)
#         - Documentation (comments, docstrings)
        
#         Code:
#         ```{language}
#         {code}
#         ```
        
#         Analysis:
#         {analysis}
        
#         Return JSON with these metrics:
#         {{
#             "code_quality": float,
#             "test_coverage": float,
#             "performance": float,
#             "modularity": float,
#             "documentation": float
#         }}
#         """,
        
#         "improvement_plan": """
#         Based on the following code analysis and quality metrics, generate a detailed improvement plan:
        
#         Current Quality Metrics:
#         {metrics}
        
#         Code Analysis:
#         {analysis}
        
#         Code:
#         ```{language}
#         {code}
#         ```
        
#         Create a list of specific improvement actions needed. For each action, specify:
#         - action_type: (refactor, add_tests, optimize, document, modularize)
#         - description: Detailed description of what to change
#         - priority: (high, medium, low)
        
#         Return as JSON list:
#         [
#             {{
#                 "action_type": "refactor",
#                 "description": "Split this large function into smaller ones",
#                 "priority": "high"
#             }},
#             ...
#         ]
#         """,
        
#         "refine_code": """
#         Improve the following code based on the improvement plan:
        
#         Improvement Plan:
#         {improvement_plan}
        
#         Context:
#         {context}
        
#         Original Code:
#         ```{language}
#         {code}
#         ```
        
#         Return the improved code only:
#         """
#     }
# }


# config/prompts.py
"""
Prompt library for the AI Coding Agent
"""
import json # Ensure json is imported

# System prompts for the AI agent's various tasks without vscode action
PROMPTS = {
    "planner": {
        "create_plan": """
        Task: {task_description}

        Context (if any): {context}

        IMPORTANT: First, analyze the nature of the Task description.
        1. If the user is asking to 'analyze', 'modify', 'explain', 'review', or 'refactor' a specific existing file path mentioned in the task (e.g., "modify src/utils.py to add validation"), create a single-step plan focusing ONLY on that action (e.g., a 'code_analysis' or 'code_modification' step targeting that exact file). Verify the file exists before planning modification. Do not generate steps for creating new files unless explicitly asked as part of the modification/refactoring.
        2. If the user input seems conversational, asks a general question, or does not clearly describe a specific coding task (creating features, fixing bugs, writing files), DO NOT generate a plan JSON. Instead, respond conversationally (e.g., "I can help with coding tasks. Please describe what you'd like me to build, analyze, or modify.").
        3. If the Task describes a standard coding goal (e.g., "create a flask app", "add a new endpoint", "fix the bug in login.py"), proceed to generate a detailed, executable plan.
        4. If the Task describes a multi-step process, a list of requirements, or a design document (potentially loaded from a file), analyze the *entire* input to understand the full scope. Break down this potentially complex request into a sequential, logical plan. Ensure the 'understanding' field accurately summarizes the overall goal derived from the full task description.

        IF GENERATING A PLAN (Cases 1, 3, 4):
        - Create a detailed, executable plan for completing the coding task.
        - The plan MUST include:
            1. Clear 'understanding' of the overall task based *only* on the provided description and context.
            2. Complete list of 'files' needed (create or modify), using relative paths (e.g., "app/main.py"). Before planning 'code_generation', consider if a file with the same purpose/path already exists; if so, prefer 'code_modification' if appropriate.
            3. Specific, actionable 'steps'.

        FOR EACH STEP:
        - Use relative paths for `file_path`.
        - Ensure necessary fields are included based on type:
            - code_generation: MUST include `file_path` and detailed `requirements` (imports, signatures, behavior, dependencies, error handling).
            - code_modification: MUST include `file_path` and specific `requirements` detailing the exact changes needed.
            - terminal_command: MUST include the exact `command`.
            - code_analysis: MUST include `file_path` and optionally `requirements` specifying the analysis focus.

        EXAMPLE STEP FOR FASTAPI:
        {{
            "type": "code_generation",
            "file_path": "app/main.py",
            "description": "Create main FastAPI application file",
            "requirements": "Create FastAPI app with:\\n- GET /weather endpoint\\n- City parameter validation\\n- Error handling\\n- Async database connection",
            "params": {{}}
        }}

        Return ONLY valid JSON with this structure (or a conversational string if Case 2 applies):
        {{
            "understanding": "clear_description",
            "files": ["complete_file_list_relative_paths"],
            "steps": [
                {{
                    "type": "step_type",
                    "description": "what_this_step_does",
                    "requirements": "specific_requirements_or_analysis_focus",
                    "file_path": "path/if_applicable",
                    "command": "command_if_applicable",
                    "params": {{}} // Optional parameters for the step type
                }}
                // ... more steps
            ]
        }}
        """,
        # Updated refine_plan prompt to match arguments passed by agent
        "refine_plan": """
        Based on the execution results and feedback, refine the plan. Consider:
        - Which steps succeeded/failed/skipped.
        - Why failures occurred (error messages, output).
        - Modifying existing steps (e.g., changing requirements, commands).
        - Adding new steps to address issues or missing functionality.
        - Removing redundant or unnecessary steps.
        - Reordering steps if dependencies changed.

        Initial Plan JSON: {initial_plan_json}
        Execution Results JSON: {results_json}
        User Feedback: {feedback}

        Return ONLY the refined plan as valid JSON with this structure:
        {{
            "understanding": "updated_understanding",
            "files": ["updated_file_list"],
            "steps": [
                {{
                    "type": "step_type",
                    "description": "updated_description",
                    "requirements": "updated_requirements",
                    "file_path": "path_if_applicable",
                    "command": "command_if_applicable",
                    "params": {{}}
                }}
            ]
        }}
        """
    },
    "code_generator": {
        "generate": """
        Requirements: {requirements}
        Context: {context}

        Generate clean, efficient, and well-documented code in the language implied by the context (e.g., file path) that fulfills the requirements precisely.
        Use best practices for the language. Include appropriate error handling.
        Implement async/await patterns where appropriate for performance if requested or suitable.
        Ensure the generated code aligns with the provided context (e.g., existing plan, task description).

        Return ONLY the generated code, without any additional explanation, comments outside the code, or markdown formatting.
        """,
        "modify": """
        Existing Code (in {language}):
        ```
        {existing_code}
        ```

        Required Modifications: {modifications}
        Code Analysis (optional): {analysis}
        Context (optional): {context}

        IMPORTANT: Modify ONLY the `Existing Code` provided based *strictly* on the `Required Modifications`.
        - Do NOT add unrelated functions, classes, or logic.
        - Preserve the original code structure and style unless the modifications explicitly require changes.
        - Compare the 'Required Modifications' against the 'Existing Code' to ensure the changes are relevant and targeted.
        - Include clear comments *only* for significant changes if appropriate for the language style.
        - Implement async/await patterns where appropriate for better performance if requested or suitable.

        Return ONLY the complete modified code, without any additional explanation or markdown formatting.
        """
    },
    "code_analyzer": {
        "analyze": """
        Analyze the following code ({language}) and provide a structured breakdown.
        Focus: {analysis_focus}

        Code:
        ```
        {code}
        ```

        If the focus is 'general', extract the following:
        1. Language detected (confirm if different from provided)
        2. Imports and dependencies
        3. Functions/classes/methods defined (names, parameters, basic purpose if obvious)
        4. Main execution flow (brief summary)
        5. Potential issues or antipatterns (e.g., style issues, possible bugs, complexity)
        6. Whether the code uses async/await patterns

        If the focus is specific (e.g., 'dependencies', 'signatures', 'bugs'), provide detailed information primarily on that aspect, but include a brief language confirmation.

        Format the response as JSON only:
        {{
          "language": "detected_language",
          "analysis_focus": "{analysis_focus}",
          "imports": ["list", "of", "imports"],
          "functions": [ {{"name": "func_name", "signature": "params", "purpose": "brief"}}, ... ],
          "classes": [ {{"name": "class_name", "methods": ["method1", "..."]}}, ... ],
          "main_flow": "summary_of_execution",
          "issues": ["list", "of", "potential_issues"],
          "uses_async": boolean,
          "specific_focus_details": {{}} // Populate if focus was specific
        }}
        """
    },
    # Improvement prompts remain the same as before
    "improvement": {
        "analyze_quality": """
        Analyze the following code and provide quality metrics (0-1 scale):
        - Code Quality (structure, readability, style)
        - Test Coverage (presence of tests)
        - Performance (efficiency considerations)
        - Modularity (proper separation of concerns)
        - Documentation (comments, docstrings)

        Code:
        ```{language}
        {code}
        ```

        Analysis:
        {analysis}

        Return JSON with these metrics:
        {{
            "code_quality": float,
            "test_coverage": float,
            "performance": float,
            "modularity": float,
            "documentation": float
        }}
        """,
        "improvement_plan": """
        Based on the following code analysis and quality metrics, generate a detailed improvement plan:

        Current Quality Metrics:
        {metrics}

        Code Analysis:
        {analysis}

        Code:
        ```{language}
        {code}
        ```

        Create a list of specific improvement actions needed. For each action, specify:
        - action_type: (refactor, add_tests, optimize, document, modularize)
        - description: Detailed description of what to change
        - priority: (high, medium, low)

        Return as JSON list:
        [
            {{
                "action_type": "refactor",
                "description": "Split this large function into smaller ones",
                "priority": "high"
            }},
            ...
        ]
        """,
        "refine_code": """
        Improve the following code based on the improvement plan:

        Improvement Plan:
        {improvement_plan}

        Context:
        {context}

        Original Code:
        ```{language}
        {code}
        ```

        Return the improved code only:
        """
    }
}