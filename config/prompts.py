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

"""
Prompt library for the AI Coding Agent
"""
# System prompts for the AI agent's various tasks without vscode action
PROMPTS = {
    "planner": {
        "create_plan": """
        Task: {task_description}
        
        Create a detailed plan for completing this coding task. The plan should include:
        1. An overall understanding of what needs to be built
        2. A breakdown of files that need to be created or modified
        3. A sequence of specific steps to take
        
        For each step, specify:
        - Step type (code_generation, code_modification, terminal_command)
        - Detailed description of what should happen in this step
        - Any specific requirements or constraints
        - Expected output or result
        
        Format your response as a JSON object with the following structure:
        {{
            "understanding": "description of the overall task",
            "files": ["list", "of", "files", "to", "create", "or", "modify"],
            "steps": [
                {{
                    "type": "step_type",
                    "description": "what this step does",
                    "requirements": "specific requirements",
                    "file_path": "path/to/file" (if applicable),
                    "command": "command to run" (if applicable),
                    "action": "code generation" (if applicable),
                    "params": {{}} (if applicable)
                }}
            ]
        }}
        """
    },
    
    "code_generator": {
        "generate": """
        Requirements: {requirements}
        
        {context}
        
        Generate code that fulfills these requirements. Use best practices and write clean, 
        efficient, and well-documented code. Include appropriate error handling and tests where necessary.
        Implement async/await patterns where appropriate for better performance.
        
        Return only the code without any additional explanation:
        """,
        
        "modify": """
        Existing Code:
        ```
        {existing_code}
        ```
        
        Required Modifications: {modifications}
        
        {analysis}
        
        Modify the existing code according to the required modifications. Maintain the overall structure 
        and style of the code unless specifically asked to change it. Include clear comments for significant changes.
        Implement async/await patterns where appropriate for better performance.
        
        Return the complete modified code without any additional explanation:
        """
    },
    
    "code_analyzer": {
        "analyze": """
        Analyze the following code and provide a structured breakdown:
        
        ```
        {code}
        ```
        
        Extract and return the following information in JSON format:
        1. Language detected
        2. Imports and dependencies
        3. Functions/classes/methods defined
        4. Function signatures with parameter types (if detectable)
        5. Main execution flow
        6. Potential issues or antipatterns
        7. Whether the code uses async/await patterns
        
        Format as JSON only:
        """
    }
}