import sys
import os # Import os for path operations
from typing import Dict, Any, Optional, List, Literal

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
# Corrected import: Choice is not imported directly
from rich.prompt import Prompt, Confirm
from rich.text import Text
from rich.table import Table
from rich.tree import Tree
from rich.progress import Progress, SpinnerColumn, TextColumn

# Assuming schema definitions are in utils.schema
# Need to handle potential import errors if schema is complex or has issues
try:
    from utils.schema import Plan, Step, StepResult, CodeAnalysis
except ImportError as e:
     print(f"CLI_UI Import Error: Failed to import from utils.schema - {e}")
     # Define dummy classes if schema import fails, to allow basic UI function
     class Step: pass
     class Plan: pass
     class StepResult: pass
     class CodeAnalysis: pass
     # Or re-raise the error depending on desired behavior
     # raise


class CLI_UI:
    """Handles all Command Line Interface interactions using Rich."""

    def __init__(self):
        # Initialize Rich Console
        self.console = Console()

    def display_header(self):
        """Displays the application header."""
        self.console.print(Panel(
            Text("Interactive AI Coding Agent", style="bold blue", justify="center"),
            title="Welcome",
            border_style="green"
        ))
        self.console.print("Type your coding task below, or 'exit' to quit.", style="dim")

    def ask_for_task(self) -> str:
        """Prompts the user for the next task."""
        # Use Rich Prompt for better input handling
        task = Prompt.ask("\n[bold yellow]Enter your task description[/]")
        return task.strip() # Return stripped task string

    def print_message(self, message: str, style: Optional[str] = None):
        """Prints a general message to the console with optional styling."""
        # Use Rich Console's print method which supports style tags
        self.console.print(message, style=style or "") # Pass empty string if style is None

    def print_error(self, message: str):
        """Prints an error message formatted in a Panel."""
        # Use Rich Panel for visual distinction of errors
        self.console.print(Panel(f"[bold red]Error:[/bold red] {message}", title="Error", border_style="red", expand=False))

    def print_warning(self, message: str):
        """Prints a warning message."""
        # Use Rich style tags for warnings
        self.console.print(f"[yellow]Warning:[/yellow] {message}")

    def print_thinking(self, message: str = "Thinking..."):
        """Displays a thinking/processing indicator using Rich Progress."""
        # Use Rich Progress for a transient spinner
        with Progress(
            SpinnerColumn(), # Display a spinner animation
            TextColumn("[progress.description]{task.description}"), # Display the message
            transient=True, # Remove the progress display when done
            console=self.console
        ) as progress:
            progress.add_task(description=message, total=None) # Add an indeterminate task
            # Simulate work briefly for visual effect if the actual work is very fast
            import time
            time.sleep(0.5) # Adjust sleep time as needed

    def display_plan(self, plan: Plan):
        """Displays the execution plan using Rich Table."""
        if not plan or not hasattr(plan, 'steps') or not plan.steps:
            self.print_warning("No valid plan to display.")
            return

        # Create a Rich Table for structured display
        table = Table(title="Execution Plan", show_header=True, header_style="bold magenta", border_style="dim blue")
        table.add_column("Step", style="dim", width=6, justify="right")
        table.add_column("Type", style="cyan", width=18)
        table.add_column("Description", style="white", max_width=60, overflow="fold") # Fold long descriptions
        table.add_column("Details", style="green", max_width=50, overflow="fold")

        # Display plan understanding and target files
        understanding = getattr(plan, 'understanding', 'N/A')
        files = getattr(plan, 'files', [])
        self.console.print(f"\n[bold]Understanding:[/bold] {understanding}")
        self.console.print(f"[bold]Target Files:[/bold] {', '.join(files) if files else 'None specified'}")

        # Add each step to the table
        for i, step in enumerate(plan.steps):
            # Ensure step is a valid Step object or dict-like
            step_type = getattr(step, 'type', 'N/A')
            description = getattr(step, 'description', 'N/A')
            file_path = getattr(step, 'file_path', None)
            command = getattr(step, 'command', None)
            requirements = getattr(step, 'requirements', None)

            details = ""
            if file_path:
                details += f"File: {file_path}\n"
            if command:
                details += f"Cmd: {command}\n"
            if requirements:
                 # Truncate long requirements for display
                 req_snippet = (requirements[:70] + '...') if len(requirements) > 70 else requirements
                 details += f"Reqs: {req_snippet}"

            table.add_row(str(i + 1), step_type, description, details.strip())

        self.console.print(table) # Print the generated table

    def display_step_start(self, step_idx: int, step: Step):
        """Displays the start of a step execution using Rich Rule and styled text."""
        step_type = getattr(step, 'type', 'N/A')
        description = getattr(step, 'description', 'N/A')
        file_path = getattr(step, 'file_path', None)
        command = getattr(step, 'command', None)
        requirements = getattr(step, 'requirements', None)

        # Use Rich Rule for visual separation
        self.console.rule(f"[bold cyan]Step {step_idx + 1}: {step_type}[/bold cyan]")
        self.console.print(f"[italic]Description:[/italic] {description}")
        if file_path:
             # Use highlight=False to prevent Rich from highlighting paths potentially
             self.console.print(f"[italic]File Path:[/italic] {file_path}", highlight=False)
        if command:
             # Use backticks for command emphasis, handled by Rich markup
             self.console.print(f"[italic]Command:[/italic] [bold]`{command}`[/bold]")
        if requirements:
             # Truncate long requirements
             req_snippet = requirements[:150] + ('...' if len(requirements)>150 else '')
             self.console.print(f"[italic]Requirements:[/italic] {req_snippet}")


    def display_step_result(self, step_idx: int, result: StepResult):
        """Displays the result of a step execution using Rich Panel."""
        # Ensure result is a valid StepResult object or dict-like
        status = getattr(result, 'status', 'unknown')
        note = getattr(result, 'note', None)
        error = getattr(result, 'error', None)
        file = getattr(result, 'file', None)
        output = getattr(result, 'output', None)
        result_data = getattr(result, 'result', None) # This is the inner 'result' dict

        status_color = {
            "completed": "green",
            "skipped": "yellow",
            "failed": "red"
        }.get(status, "white") # Default color

        title = f"Step {step_idx + 1} Result: [{status_color}]{status.upper()}[/{status_color}]"
        content = ""
        if note:
            content += f"Note: {note}\n"
        if error:
            content += f"[bold red]Error:[/bold red] {error}\n"
        if file:
            content += f"File affected: {file}\n"
            # Check if inner result dict exists and has the hash
            if isinstance(result_data, dict) and result_data.get('file_hash'):
                 content += f"  Hash: {result_data['file_hash'][:12]}...\n"
        if output:
            # Only show snippet of output in result panel to avoid clutter
            output_snippet = output.strip()[:200]
            if len(output.strip()) > 200:
                output_snippet += "..."
            if output_snippet: # Avoid printing empty output string
                # Use Panel for better visual separation of output
                content += f"Output (snippet):\n"
                content += Panel(output_snippet, border_style="dim", expand=False)


        # Display the result in a Panel
        if content.strip():
             self.console.print(Panel(content.strip(), title=title, border_style=status_color, expand=False))
        else:
             # Show a simple panel if no details are available
             self.console.print(Panel("No further details.", title=title, border_style=status_color, expand=False))


    def display_code(self, code: str, language: str = 'python', file_path: Optional[str] = None):
        """Displays code with syntax highlighting using Rich Syntax."""
        title = f"Code Block ({language})"
        if file_path:
            title += f" - Target: {file_path}" # Add file path to title if available

        if not code or not code.strip():
             # Display a panel indicating empty code
             self.console.print(Panel("[dim]Empty code block.[/dim]", title=title, border_style="yellow"))
             return

        # Create Rich Syntax object for highlighting
        syntax = Syntax(
            code,
            language,
            theme="default", # Choose a theme (e.g., "default", "monokai")
            line_numbers=True, # Show line numbers
            word_wrap=False # Prevent wrapping long lines
        )
        # Display Syntax object within a Panel
        self.console.print(Panel(syntax, title=title, border_style="blue", expand=True)) # Expand panel to fit code

    def display_command(self, command: str):
        """Displays a command to be executed, formatted in a Panel."""
        # Use Rich markup for styling the command prompt
        self.console.print(Panel(f"[bold cyan]$[/] [white]{command}[/]", title="Command Preview", border_style="yellow", expand=False))

    # def display_command_output(self, output_dict: Dict[str, Any]):
    #     """Displays the output of a terminal command using Rich Panel."""
    #     # Extract output details
    #     stdout = output_dict.get('stdout', '').strip()
    #     stderr = output_dict.get('stderr', '').strip()
    #     return_code = output_dict.get('return_code')
    #     success = output_dict.get('success', False)

    #     # Determine status text and panel border color
    #     status_text = f"[bold green]Success (Code: {return_code})[/]" if success else f"[bold red]Failed (Code: {return_code})[/]"
    #     panel_border = "green" if success else "red"

    #     # Build content string
    #     content = f"{status_text}\n"
    #     if stdout:
    #         content += f"\n[bold]stdout:[/bold]\n"
    #         # Put stdout in its own nested panel for clarity
    #         content += Panel(stdout, border_style="dim", expand=True)
    #     if stderr:
    #         content += f"\n[bold red]stderr:[/bold red]\n"
    #         # Put stderr in its own nested panel
    #         content += Panel(stderr, border_style="dim red", expand=True)

    #     # Print the main panel containing status and nested output panels
    #     self.console.print(Panel(content.strip(), title="Command Output", border_style=panel_border, expand=True))

    def display_command_output(self, output_dict: Dict[str, Any]):
        """Displays the output of a terminal command using Rich Panel."""
        stdout = output_dict.get('stdout', '').strip()
        stderr = output_dict.get('stderr', '').strip()
        return_code = output_dict.get('return_code')
        success = output_dict.get('success', False)

        status_text = f"[bold green]Success (Code: {return_code})[/]" if success else f"[bold red]Failed (Code: {return_code})[/]"
        panel_border = "green" if success else "red"

        self.console.print(Panel(status_text, border_style=panel_border, title="Command Status", expand=False))

        if stdout:
            self.console.print(Panel(stdout, title="stdout", border_style="dim", expand=True))
        if stderr:
            self.console.print(Panel(stderr, title="stderr", border_style="red", expand=True))



    def ask_confirmation(self, message: str, default: bool = True) -> bool:
        """Asks the user for a yes/no confirmation using Rich Confirm."""
        # Use Rich Confirm for clear Y/n prompt
        return Confirm.ask(f"[bold yellow]? {message}[/]", default=default)

    def ask_edit_confirmation(self, file_path: str, action: str = "write to") -> Literal['confirm', 'edit', 'cancel']:
        """Asks user to confirm, edit manually, or cancel using Rich Prompt with choices."""
        # self.console.print(f"\n[bold yellow]Action required for:[/bold] {file_path}")
        self.console.print(f"\n[bold yellow]Action required for: {file_path}[/bold yellow]")

        # Use Prompt.ask with the 'choices' parameter
        choice = Prompt.ask(
            f"Do you want to {action} this file?",
            choices=["confirm", "edit", "cancel"], # Provide list of choices
            default="confirm" # Set the default choice
        )
        # The return value will be one of the strings in 'choices'
        return choice # type: ignore

    def prompt_manual_edit(self, file_path: str):
         """Instructs the user to manually edit the file, showing absolute path."""
         # Ensure the path is absolute for clarity
         abs_path = os.path.abspath(file_path)
         self.console.print(Panel(
              f"Please open and edit the file manually in your preferred editor:\n\n"
              f"[bold cyan]{abs_path}[/]\n\n"
              f"Save your changes, then press Enter here to continue.",
              title="Manual Edit Required",
              border_style="yellow"
         ))
         # Use input() to pause execution until user presses Enter
         input("Press Enter when ready...")

    def display_analysis_summary(self, analysis: Optional[CodeAnalysis]):
         """Displays a summary of the code analysis using Rich Table."""
         if not analysis or not isinstance(analysis, CodeAnalysis):
             self.print_warning("Code analysis data not available or invalid.")
             return

         # Create a simple table for the summary
         table = Table(title=f"Code Analysis Summary ({getattr(analysis, 'language', 'N/A')})", show_header=False, box=None, padding=(0, 1))
         table.add_column("Metric", style="dim")
         table.add_column("Value")

         # Add rows for key analysis metrics
         table.add_row("Language:", getattr(analysis, 'language', 'N/A'))
         table.add_row("Imports:", str(len(getattr(analysis, 'imports', []))))
         table.add_row("Functions:", str(len(getattr(analysis, 'functions', []))))
         table.add_row("Classes:", str(len(getattr(analysis, 'classes', []))))
         uses_async = getattr(analysis, 'uses_async', False)
         table.add_row("Async:", "[green]Yes[/]" if uses_async else "[red]No[/]")
         table.add_row("Issues Found:", str(len(getattr(analysis, 'issues', []))))

         self.console.print(table) # Print the summary table

    def display_dependencies(self, file_path: str, dependencies: List[str], dependents: List[str]):
        """Displays dependencies and dependents for a file using Rich Tree."""
        # Create a Rich Tree structure
        # tree = Tree(f"[bold blue]Dependency Info for:[/bold] {file_path}")
        tree = Tree(f"[bold blue]Dependency Info for: {file_path}[/bold blue]")

        # Add branch for dependencies
        dep_branch = tree.add("[green]Dependencies (File relies on):[/green]")
        if dependencies:
            for dep in dependencies:
                dep_branch.add(dep) # Add each dependency as a leaf
        else:
            dep_branch.add("[dim]None[/dim]") # Indicate no dependencies

        # Add branch for dependents
        dependent_branch = tree.add("[magenta]Dependents (File is used by):[/magenta]")
        if dependents:
            for dep in dependents:
                dependent_branch.add(dep) # Add each dependent as a leaf
        else:
            dependent_branch.add("[dim]None[/dim]") # Indicate no dependents

        self.console.print(tree) # Print the dependency tree

    def display_final_results(self, results: Dict[str, Any]):
         """Displays a summary of the final results for the task using Rich Rule and Table."""
         # Extract final results details
         success = results.get("success", False)
         task_id = results.get("task_id", "N/A")
         duration = results.get("duration_seconds", None)
         final_status = "[bold green]SUCCESS[/]" if success else "[bold red]FAILURE / CANCELLED[/]"
         duration_str = f"in {duration:.2f}s" if duration is not None else ""

         # Display final status using Rich Rule
         self.console.rule(f"[bold]Task {task_id} - Final Status: {final_status} {duration_str}[/bold]")

         # Display summary of step results in a table
         step_results = results.get("results", {})
         if step_results:
             table = Table(title="Step Summary", show_header=True, header_style="bold blue", border_style="dim")
             table.add_column("Step", style="dim", width=6, justify="right")
             table.add_column("Status", style="cyan", width=12)
             table.add_column("Details", style="white", overflow="fold") # Fold long details

             # Add a row for each step result
             for idx_str, res_dict in step_results.items():
                 try:
                     idx = int(idx_str) # Convert index string to int
                     status = res_dict.get('status', 'unknown')
                     color = {"completed": "green", "skipped": "yellow", "failed": "red"}.get(status, "white")
                     # Combine note and error for details column
                     details = res_dict.get('note') or res_dict.get('error') or ""
                     if res_dict.get('file'):
                         details += f" (File: {res_dict['file']})"
                     table.add_row(str(idx + 1), f"[{color}]{status.upper()}[/{color}]", details.strip())
                 except (ValueError, TypeError):
                      self.logger.warning(f"Could not parse step result index: {idx_str}") # Log if index is not int
                      table.add_row(idx_str, "[red]ERROR[/red]", "[dim]Invalid result format[/dim]")


             self.console.print(table) # Print the steps summary table
         else:
             self.console.print("[dim]No step results recorded for this task.[/dim]") # Message if no results