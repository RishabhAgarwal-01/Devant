"""
LLM adapter for the AI Coding Agent with async support
"""

import logging
import json
import aiohttp
import asyncio
from typing import Dict, List, Optional, Any, Union
from utils.logger import get_logger

class LLMAdapter:
    def __init__(self, config: Dict[str, Any]):
        #Initialize the logger
        self.logger = get_logger(__name__)
        #Set the configuration
        self.config = config

        # Groq API configuration
        self.api_key = config["api_key"]
        self.api_url = config.get("api_url", "https://api.groq.com/openai/v1/chat/completions")
        self.model = config.get("model", "llama3-70b-8192")
        self.max_tokens = config.get("max_tokens", 4000)
        self.temperature = config.get("temperature", 0.7)
        self.timeout = config.get("timeout", 30) #timeout in seconds

        # Rate limiting
        self.semaphore = asyncio.Semaphore(5)  # Limit concurrent API calls

    #generate method to generate the text
    async def generate(self, prompt:str, formated_output:Optional[str] = None) -> Union[str, Dict[str, Any]]:
        #Set the headers
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        #Adjust the prompt based on the desired output format
        formatted_prompt = prompt
        if formated_output == "json":
            formatted_prompt = f"{prompt}\n\nYou must respond with valid JSON only, no additional text."
        elif formated_output == "code":
            formatted_prompt = f"{prompt}\n\nRespond with code only, no explanations or markdown."
        
        #System message to help with formatting
        system_message = "You are a helpful AI assistant specialized in coding tasks."
        if formated_output == "json":
            system_message = "You are a helpful AI assistant that always responds with valid, properly formatted JSON."
        elif formated_output == "code":
            system_message = "You are a helpful AI assistant that always responds with clean, correct code without explanations."
        
        #Data to be sent
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": formatted_prompt}
            ],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature
        }

        #Use the semaphore to limit concurrency
        async with self.semaphore:
            try:
                self.logger.debug(f"Sending request to Groq API: {self.api_url}")
                
                #Use aiohttp for async HTTP requests
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        self.api_url,
                        headers=headers,
                        json=data,
                        timeout=aiohttp.ClientTimeout(total=self.timeout)
                    ) as response:
                        if response.status != 200:
                            error_msg = await response.text()
                            self.logger.error(f"API request failed with status {response.status}: {error_msg}")
                            return {"error": f"API request failed: {error_msg}" }
                        
                        result = await response.json()
                generated_text = result["choices"][0]["message"]["content"]

                #Post-process based on output format
                if formated_output == "json":
                    try:
                        return json.loads(generated_text)
                    except json.JSONDecodeError:
                        self.logger.error("Failed to parse generated text as JSON")
                        #try to extract JSON if it's surrounded by markdown code blocks
                        if " ```json" in generated_text:
                            try:
                                json_str = generated_text.split("```json")[1].split("```")[0].strip()
                                return json.loads(json_str)
                            except (IndexError, json.JSONDecodeError):
                                self.logger.error("Failed to extract JSON from markdown")
                        elif "```" in generated_text:
                            try:
                                json_str = generated_text.split("```")[1].split("```")[0].strip()
                                return json.loads(json_str)
                            except (IndexError, json.JSONDecodeError):
                                self.logger.error("Failed to extract JSON from markdown")
                        
                        #Return as string if parsing failed
                        return {"error": "Failed to parse response as JSON", "raw_response": generated_text}
                elif formated_output == "code":
                    #Remove markdown code blocks if present
                    if "```" in generated_text:
                        try:
                            #Extract code between markdown code blocks
                            lines = generated_text.split("```")
                            #If there are multiple code blocks, take the longest one
                            code_blocks = [lines[i] for i in range(1, len(lines), 2)]
                            code = max(code_blocks, key=len)

                            #Remove language identifier if present
                            if code.startswith("python") or code.startswith("javascript") or any(code.startswith(lang) for lang in ["bash", "json", "html", "css"]):
                                code = code.split("\n", 1)[1]
                            
                            return code.strip()
                        except IndexError:
                            self.logger.error("Failed to extract code from markdown")
                    #Return as-is if no markdown
                    return generated_text.strip()
                
                return generated_text

            except aiohttp.ClientError as e:
                self.logger.error(f"HTTP request failed: {str(e)}")
                return {"error": f"HTTP request failed: {str(e)}"}
            except asyncio.TimeoutError:
                self.logger.error(f"Request timed out after {self.timeout} seconds")
                return {"error": f"Request timed out after {self.timeout} seconds"}
            except Exception as e:
                self.logger.error(f"Unexpected error: {str(e)}")
                return {"error": f"Unexpected error: {str(e)}"}
    
