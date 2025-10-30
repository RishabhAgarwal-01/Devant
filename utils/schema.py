# from typing import Dict, List, Any, Optional, Union, Literal
# from dataclasses import dataclass, field
# # Define the data classes

# @dataclass
# class Step:
#     """A step in the execution plan."""
#     type: Literal["code_generation", "code_modification", "terminal_command", "vscode_action"]
#     description: str
#     requirements: Optional[str] = None
#     file_path: Optional[str] = None
#     command: Optional[str] = None
#     action: Optional[str] = None
#     params: Optional[Dict[str, Any]] = field(default_factory=dict)
#     expected_result: Optional[str] = None  # Add this field

#     def __post_init__(self):
#         """Validate the step after initialization."""
#         if self.type in ["code_generation", "code_modification"] and not self.file_path:
#             raise ValueError(f"Step of type {self.type} requires a file_path")

#     def to_dict(self) -> Dict:
#         """Convert to dictionary for JSON serialization."""
#         return {
#             "type": self.type,
#             "description": self.description,
#             "requirements": self.requirements,
#             "file_path": self.file_path,
#             "command": self.command,
#             "action": self.action,
#             "params": self.params,
#             "expected_result": self.expected_result
#         }

#     @classmethod
#     def from_dict(cls, data: Dict) -> 'Step':
#         """Create from dictionary."""
#         return cls(**data)

# #Plan class to define the complete execution plan
# @dataclass
# class Plan:
#     """A complete execution plan."""
#     understanding: str
#     files: List[str]
#     steps: List[Step]

# #CodeAnalysis class to define the analysis of code structure and functionality
# @dataclass
# class CodeAnalysis:
#     """Analysis of code structure and functionality."""
#     language: str
#     imports: List[str]
#     functions: List[Dict[str, Any]]
#     classes: List[Dict[str, Any]]
#     main_flow: str
#     issues: List[str]
#     uses_async: bool

# #StepResult class to define the result of executing a single step
# @dataclass
# class StepResult:
#     """Result of executing a single step."""
#     status: Literal["completed", "skipped", "failed"]
#     error: Optional[str] = None
#     file: Optional[str] = None
#     output: Optional[str] = None
#     result: Optional[Dict[str, Any]] = None
#     note: Optional[str] = None


# utils/schema.py

from typing import Dict, List, Any, Optional, Union, Literal
from dataclasses import dataclass, field
# Define the data classes

@dataclass
class Step:
    """A step in the execution plan."""
    type: Literal["code_generation", "code_modification", "terminal_command", "code_analysis", "vscode_action"] # Added code_analysis
    description: str
    requirements: Optional[str] = None # Can be requirements for generation/modification, or focus for analysis
    file_path: Optional[str] = None
    command: Optional[str] = None
    action: Optional[str] = None # Retained from original, but might not be used by current agent logic
    params: Optional[Dict[str, Any]] = field(default_factory=dict)
    expected_result: Optional[str] = None

    def __post_init__(self):
        """Validate the step after initialization."""
        if self.type in ["code_generation", "code_modification", "code_analysis"] and not self.file_path:
            raise ValueError(f"Step of type '{self.type}' requires a file_path")
        if self.type == "terminal_command" and not self.command:
            raise ValueError("Step of type 'terminal_command' requires a command")

    def to_dict(self) -> Dict[str, Any]:
        """Convert Step object to a dictionary, excluding None values."""
        return {k: v for k, v in self.__dict__.items() if v is not None}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Step':
        """Create Step object from dictionary, handling potential missing keys."""
        # Basic implementation assumes data dict matches dataclass fields.
        # More robust parsing might be needed depending on source reliability.
        # Ensure only known fields are passed to __init__
        known_fields = cls.__dataclass_fields__.keys()
        filtered_data = {k: v for k, v in data.items() if k in known_fields}
        return cls(**filtered_data)

@dataclass
class Plan:
    """A complete execution plan."""
    understanding: str
    files: List[str] # List of relative file paths involved
    steps: List[Step]

@dataclass
class CodeAnalysis:
    """Analysis of code structure and functionality."""
    language: str
    analysis_focus: Optional[str] = "general" # Added: What was analyzed (e.g., 'general', 'dependencies')
    imports: List[str] = field(default_factory=list)
    functions: List[Dict[str, Any]] = field(default_factory=list) # e.g., [{"name": "...", "signature": "...", "purpose": "..."}]
    classes: List[Dict[str, Any]] = field(default_factory=list) # e.g., [{"name": "...", "methods": [...]}]
    main_flow: Optional[str] = None # Summary of execution or structure
    issues: List[str] = field(default_factory=list) # Potential problems found
    uses_async: bool = False
    specific_focus_details: Optional[Dict[str, Any]] = field(default_factory=dict) # Added: Detailed results for specific focus

@dataclass
class StepResult:
    """Result of executing a single step."""
    status: Literal["completed", "skipped", "failed"]
    error: Optional[str] = None # Error message if status is 'failed'
    file: Optional[str] = None # Relative path of file generated/modified
    output: Optional[str] = None # Stdout/stderr from terminal commands
    result: Optional[Dict[str, Any]] = None # Other structured results (e.g., file hash, return code)
    note: Optional[str] = None # Additional notes (e.g., "skipped by user", "analysis details")