# config/settings.py
import json
import os
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def load_config(config_path: str) -> Dict[str, Any]:
    """Load configuration from a JSON file."""
    # Check if the file exists
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    # Load the configuration file and read it
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # Add environment variables
    if "llm" in config and "api_key" not in config["llm"]:
        api_key_env = os.environ.get("GEMINI_API_KEY")
        if api_key_env:
            config["llm"]["api_key"] = api_key_env #set the api key from the environment variable
    
    return config


