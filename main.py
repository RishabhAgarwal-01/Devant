# """
# Main entry point for the AI Coding Agent with async support
# """
# import argparse
# import logging
# import json
# import os
# import asyncio
# import sys
# sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# from core.agent import Agent
# from config.settings import load_config
# from utils.logger import setup_logging, get_logger
# from utils.helpers import save_json, load_json

# async def main_async():
#     """Async main entry point for the AI coding agent."""
#     parser = argparse.ArgumentParser(description='AI Coding Agent with Groq Llama')
#     parser.add_argument('--config', type=str, default='config/default.json',
#                         help='Path to configuration file')
#     parser.add_argument('--task', type=str, help='Task description for the agent')
#     parser.add_argument('--task-file', type=str, help='File containing task description')
#     parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
#     parser.add_argument('--model', type=str, help='Override Llama model (llama3-70b-8192, llama3-8b-8192, etc.)')
#     parser.add_argument('--working-dir', type=str, help='Working directory for the agent')
#     parser.add_argument('--resume', type=str, help='Resume from a saved execution state file')
#     parser.add_argument('--log-file', type=str, help='Path to log file')
    
#     args = parser.parse_args()
    
#     # Setup logging
#     log_level = logging.DEBUG if args.verbose else logging.INFO
#     setup_logging(log_level, args.log_file)
    
#     # Get logger for main module
#     logger = get_logger(__name__)
    
#     # Load configuration
#     config = load_config(args.config)
    
#     # Override model if provided
#     if args.model:
#         config["llm"]["model"] = args.model
    
#     # Override working directory if provided
#     if args.working_dir:
#         config["working_directory"] = args.working_dir
        
#     # Initialize agent
#     agent = Agent(config)
    
#     # Handle resuming from a saved state
#     if args.resume:
#         try:
#             saved_state = load_json(args.resume)
#             logger.info(f"Resuming execution from {args.resume}")
#             # Add resume logic here using the saved state
#         except Exception as e:
#             logger.error(f"Error loading saved state: {str(e)}")
#             return
    
#     # Get task description
#     task = None
#     if args.task:
#         task = args.task
#     elif args.task_file:
#         try:
#             with open(args.task_file, 'r', encoding='utf-8') as f:
#                 task = f.read()
#         except Exception as e:
#             logger.error(f"Error reading task file: {str(e)}")
#             return
#     else:
#         logger.error("No task provided. Please provide a task using --task or --task-file")
#         return
    
#     # Run the agent
#     try:
#         logger.info(f"Starting agent execution with task: {task[:50]}...")
#         working_dir = config.get("working_directory", "./workspace")
#         if not os.path.exists(working_dir):
#             os.makedirs(working_dir)
#             logger.info(f"Created working directory: {working_dir}")
#         result = await agent.run(task)
        
#         # Save the results
#         results_file = os.path.join(config["working_directory"], "execution_results.json")
#         save_json(result, results_file)
#         logger.info(f"Execution results saved to {results_file}")
#         print(json.dumps(result, indent=2))
#     except Exception as e:
#         logger.error(f"Error running agent: {str(e)}", exc_info=True)
#         raise

# def main():
#     """Synchronous entry point that calls the async main function."""
#     asyncio.run(main_async())

# if __name__ == "__main__":
#     main()


# main.py - Updated for Interactive CLI and Continuous Workflow

import argparse
import logging
import json
import os
import asyncio
import sys
from typing import Optional

# Ensure the project root is in the Python path
# Determine the script's directory
script_dir = os.path.dirname(os.path.abspath(__file__))
# Determine the project root directory (assuming main.py is in the root)
project_root = script_dir
# Add project root to Python path if it's not already there
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# Add core directory to Python path explicitly if needed (adjust based on structure)
core_dir = os.path.join(project_root, 'core')
if core_dir not in sys.path:
     sys.path.insert(0, core_dir)
utils_dir = os.path.join(project_root, 'utils')
if utils_dir not in sys.path:
     sys.path.insert(0, utils_dir)
adapters_dir = os.path.join(project_root, 'adapters')
if adapters_dir not in sys.path:
     sys.path.insert(0, adapters_dir)
config_dir = os.path.join(project_root, 'config')
if config_dir not in sys.path:
     sys.path.insert(0, config_dir)


from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.text import Text

# Adjusted imports based on typical project structure
# Assumes core, utils, config, adapters are directories directly under the project root
try:
    from core.agent import Agent
    from config.settings import load_config
    from utils.logger import setup_logging, get_logger
    from utils.helpers import save_json, load_json
    from utils.cli_ui import CLI_UI # Import the new UI class
except ImportError as e:
     print(f"Import Error: {e}. Please ensure the script is run from the project root directory or check PYTHONPATH.")
     print(f"Current sys.path: {sys.path}")
     sys.exit(1)


# --- Configuration and Setup ---

# Default configuration path relative to project root
DEFAULT_CONFIG_PATH = os.path.join(project_root, 'config', 'default.json')

async def main_async():
    """Async main entry point for the interactive AI coding agent."""
    parser = argparse.ArgumentParser(description='Interactive AI Coding Agent')
    parser.add_argument('--config', type=str, default=DEFAULT_CONFIG_PATH,
                        help='Path to configuration file')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    parser.add_argument('--model', type=str, help='Override LLM model')
    parser.add_argument('--working-dir', type=str, help='Working directory for the agent (relative to project root)')
    parser.add_argument('--log-file', type=str, help='Path to log file (relative to project root)')
    # Removed --task, --task-file, --resume as we'll handle this interactively

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    # Make logging less intrusive in the interactive UI
    log_filename = args.log_file or "ai_agent_interactive.log"
    # Ensure log file path is absolute or relative to project root
    log_filepath = os.path.join(project_root, log_filename)
    setup_logging(log_level, log_filepath)
    logger = get_logger(__name__)
    logger.info(f"--- Starting Interactive AI Coding Agent (PID: {os.getpid()}) ---")
    logger.info(f"Project Root: {project_root}")
    logger.info(f"Logging to file: {log_filepath}")

    # Initialize CLI UI
    cli_ui = CLI_UI()
    cli_ui.print_message(f"Logging detailed output to: [bold cyan]{log_filepath}[/]", style="dim")

    # Load configuration
    try:
        config_path = os.path.join(project_root, args.config) # Ensure config path is correct
        config = load_config(config_path)
        logger.info(f"Configuration loaded from {config_path}")
    except FileNotFoundError:
        cli_ui.print_error(f"Configuration file not found: {config_path}. Exiting.")
        logger.error(f"Configuration file not found: {config_path}")
        return
    except Exception as e:
        cli_ui.print_error(f"Error loading configuration: {e}")
        logger.error(f"Error loading configuration from {config_path}: {e}", exc_info=True)
        return

    # Resolve working directory relative to project root
    if args.working_dir:
        config["working_directory"] = os.path.join(project_root, args.working_dir)
        logger.info(f"Overriding working directory with: {config['working_directory']}")
    else:
        # Ensure default working directory exists, relative to project root
        default_work_dir_rel = config.get("working_directory", "./workspace") # Default relative path
        config["working_directory"] = os.path.join(project_root, default_work_dir_rel)

    os.makedirs(config["working_directory"], exist_ok=True)
    logger.info(f"Using working directory: {config['working_directory']}")


    # Override model if provided
    if args.model:
        if "llm" not in config: config["llm"] = {}
        config["llm"]["model"] = args.model
        logger.info(f"Overriding LLM model with: {args.model}")


    # Check for API Key
    if "llm" not in config: config["llm"] = {} # Ensure llm config section exists
    if not config.get("llm", {}).get("api_key"):
         api_key_env = os.environ.get("GEMINI_API_KEY")
         if api_key_env:
             config["llm"]["api_key"] = api_key_env
             logger.info("GEMINI_API_KEY found in environment variables.")
         else:
            cli_ui.print_error("GEMINI_API_KEY not found in config or environment variables. Please set it.")
            logger.error("GEMINI_API_KEY missing.")
            return

    # Initialize agent
    try:
        agent = Agent(config, cli_ui) # Pass UI to agent
        logger.info("Agent initialized successfully.")
    except Exception as e:
        cli_ui.print_error(f"Error initializing agent: {e}")
        logger.error(f"Error initializing agent: {e}", exc_info=True)
        return

    # --- Main Interactive Loop ---
    cli_ui.display_header()

    while True:
        try:
            task = cli_ui.ask_for_task()
            if not task or task.lower() in ['exit', 'quit', 'q']:
                cli_ui.print_message("Exiting agent. Goodbye!", style="bold green")
                logger.info("User requested exit.")
                break

            # Run the agent for the given task
            cli_ui.print_message(f"\nStarting task: [bold yellow]{task[:100]}...[/]", style="bold blue")
            logger.info(f"Starting agent execution with task: {task[:50]}...")

            # The agent's run method is now interactive via the CLI_UI
            result = await agent.run_interactive(task)

            # Display final results summary (optional, can be verbose)
            # cli_ui.display_final_results(result)
            cli_ui.print_message("\nTask processing complete. Ready for next task.", style="bold green")
            logger.info("Agent finished task processing.")

        except KeyboardInterrupt:
            cli_ui.print_message("\n\nExecution interrupted by user. Exiting.", style="bold red")
            logger.warning("Execution interrupted by user (KeyboardInterrupt).")
            break
        except Exception as e:
            cli_ui.print_error(f"\nAn unexpected error occurred during task execution: {e}")
            logger.error(f"Error during main loop: {str(e)}", exc_info=True)
            # Optionally ask user if they want to continue
            if not Confirm.ask("[bold red]An error occurred. Continue to next task?[/]", default=False):
                 cli_ui.print_message("Exiting due to error.", style="bold red")
                 break

    # Cleanup (optional)
    await agent.cleanup()
    logger.info("Agent shutdown complete.")


def main():
    """Synchronous entry point that calls the async main function."""
    try:
        asyncio.run(main_async())
    except Exception as e:
        # Fallback logging if setup failed or happens outside async loop
        print(f"[MAIN CRITICAL ERROR] An unexpected error occurred: {e}", file=sys.stderr)
        logging.getLogger(__name__).error("Critical error in main execution", exc_info=True)
        sys.exit(1) # Exit with error code

if __name__ == "__main__":
    # This structure ensures that the script directory is correctly determined
    # and added to the path before any module imports are attempted by main().
    main()