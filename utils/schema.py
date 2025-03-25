from typing import Dict, List, Any, Optional, Union, Literal
from dataclasses import dataclass

# Define the data classes

#Step class to define the steps in the execution plan
@dataclass
class Step:
    """A step in the execution plan."""
    type: Literal["code_generation", "code_modification", "terminal_command", "vscode_action"]
    description: str
    requirements: Optional[str] = None
    file_path: Optional[str] = None
    command: Optional[str] = None
    action: Optional[str] = None
    params: Optional[Dict[str, Any]] = None

#Plan class to define the complete execution plan
@dataclass
class Plan:
    """A complete execution plan."""
    understanding: str
    files: List[str]
    steps: List[Step]

#CodeAnalysis class to define the analysis of code structure and functionality
@dataclass
class CodeAnalysis:
    """Analysis of code structure and functionality."""
    language: str
    imports: List[str]
    functions: List[Dict[str, Any]]
    classes: List[Dict[str, Any]]
    main_flow: str
    issues: List[str]
    uses_async: bool

#StepResult class to define the result of executing a single step
@dataclass
class StepResult:
    """Result of executing a single step."""
    status: Literal["completed", "skipped", "failed"]
    error: Optional[str] = None
    file: Optional[str] = None
    output: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    note: Optional[str] = None
