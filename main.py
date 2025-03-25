"""
Main entry point for the AI Coding Agent with async support
"""
import argparse
import logging
import json
import os
import asyncio
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.agent import Agent
from config.settings import load_config
from utils.logger import setup_logging, get_logger
from utils.helpers import save_json, load_json

async def main_async():
    """Async main entry point for the AI coding agent."""
    parser = argparse.ArgumentParser(description='AI Coding Agent with Groq Llama')
    parser.add_argument('--config', type=str, default='config/default.json',
                        help='Path to configuration file')
    parser.add_argument('--task', type=str, help='Task description for the agent')
    parser.add_argument('--task-file', type=str, help='File containing task description')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    parser.add_argument('--model', type=str, help='Override Llama model (llama3-70b-8192, llama3-8b-8192, etc.)')
    parser.add_argument('--working-dir', type=str, help='Working directory for the agent')
    parser.add_argument('--resume', type=str, help='Resume from a saved execution state file')
    parser.add_argument('--log-file', type=str, help='Path to log file')
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(log_level, args.log_file)
    
    # Get logger for main module
    logger = get_logger(__name__)
    
    # Load configuration
    config = load_config(args.config)
    
    # Override model if provided
    if args.model:
        config["llm"]["model"] = args.model
    
    # Override working directory if provided
    if args.working_dir:
        config["working_directory"] = args.working_dir
        
    # Initialize agent
    agent = Agent(config)
    
    # Handle resuming from a saved state
    if args.resume:
        try:
            saved_state = load_json(args.resume)
            logger.info(f"Resuming execution from {args.resume}")
            # Add resume logic here using the saved state
        except Exception as e:
            logger.error(f"Error loading saved state: {str(e)}")
            return
    
    # Get task description
    task = None
    if args.task:
        task = args.task
    elif args.task_file:
        try:
            with open(args.task_file, 'r', encoding='utf-8') as f:
                task = f.read()
        except Exception as e:
            logger.error(f"Error reading task file: {str(e)}")
            return
    else:
        logger.error("No task provided. Please provide a task using --task or --task-file")
        return
    
    # Run the agent
    try:
        logger.info(f"Starting agent execution with task: {task[:50]}...")
        result = await agent.run(task)
        
        # Save the results
        results_file = os.path.join(config["working_directory"], "execution_results.json")
        save_json(result, results_file)
        logger.info(f"Execution results saved to {results_file}")
        print(json.dumps(result, indent=2))
    except Exception as e:
        logger.error(f"Error running agent: {str(e)}", exc_info=True)
        raise

def main():
    """Synchronous entry point that calls the async main function."""
    asyncio.run(main_async())

if __name__ == "__main__":
    main()