import pytest
import aiohttp
import json
import os
from dotenv import load_dotenv
from unittest.mock import AsyncMock, patch
from config.prompts import PROMPTS
from adapters.llm_adapter import LLMAdapter

load_dotenv()
api_key = os.getenv("GROQ_API_KEY")

# Mock configuration for LLMAdapter
CONFIG = {
    "api_key": api_key,
    "api_url": "https://api.groq.com/openai/v1/chat/completions",
    "model": "llama3-70b-8192",
    "max_tokens": 4000,
    "temperature": 0.7,
    "timeout": 30
}

@pytest.mark.asyncio
async def test_generate_create_plan_mocked():
    """Test LLMAdapter's generate method with a mocked API response."""

    adapter = LLMAdapter(CONFIG)

    # Example task description
    task_description = "Build a REST API using FastAPI for user authentication."
    prompt = PROMPTS["planner"]["create_plan"].format(task_description=task_description)

    # Expected mock response
    mock_response_data = {
        "choices": [{
            "message": {
                "content": json.dumps({
                    "understanding": "This task involves building a FastAPI-based REST API for authentication.",
                    "files": ["app/main.py", "app/routes/auth.py", "app/models/user.py"],
                    "steps": [
                        {
                            "type": "code_generation",
                            "description": "Create FastAPI app structure",
                            "file_path": "app/main.py"
                        }
                    ]
                })
            }
        }]
    }

    # Correctly mock aiohttp.ClientSession.post
    async def mock_post(*args, **kwargs):
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_response_data)

        # Properly mock async context manager (__aenter__ / __aexit__)
        async def mock_aenter(_self):
            return mock_response

        mock_response.__aenter__ = mock_aenter  # Accepts self correctly
        mock_response.__aexit__ = AsyncMock()

        return mock_response

    with patch("aiohttp.ClientSession.post", new=mock_post):
        response = await adapter.generate(prompt, formated_output="json")

        # Assertions
        assert isinstance(response, dict)
        assert "understanding" in response
        assert "files" in response
        assert "steps" in response
        assert response["files"] == ["app/main.py", "app/routes/auth.py", "app/models/user.py"]


@pytest.mark.asyncio
async def test_generate_create_plan_actual():
    """Test LLMAdapter's generate method with an actual API call."""

    adapter = LLMAdapter(CONFIG)

    # Example task description for the create_plan prompt
    task_description = "Build a REST API using FastAPI for user authentication."
    prompt = PROMPTS["planner"]["create_plan"].format(task_description=task_description)

    # Call the actual API
    response = await adapter.generate(prompt, formated_output="json")

    # Print the response for manual verification
    print("\nActual API Response:\n", json.dumps(response, indent=2))

    # Assertions to check basic structure
    assert isinstance(response, dict)
    assert "understanding" in response
    assert "files" in response
    assert "steps" in response
    assert isinstance(response["files"], list)
    assert isinstance(response["steps"], list)
