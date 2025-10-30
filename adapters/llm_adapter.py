# """
# LLM adapter for the AI Coding Agent with async support
# """

# import logging
# import json
# import aiohttp
# import asyncio
# from typing import Dict, List, Optional, Any, Union
# from utils.logger import get_logger

# class LLMAdapter:
#     def __init__(self, config: Dict[str, Any]):
#         # Initialize the logger
#         self.logger = get_logger(__name__)
#         # Set the configuration
#         self.config = config

#         # Groq API configuration
#         self.api_key = config["api_key"]
#         self.api_url = config.get("api_url", "https://api.groq.com/openai/v1/chat/completions")
#         self.model = config.get("model", "llama3-70b-8192")
#         self.max_tokens = config.get("max_tokens", 4000)
#         self.temperature = config.get("temperature", 0.7)
#         self.timeout = config.get("timeout", 30)  # timeout in seconds

#         # Rate limiting
#         self.semaphore = asyncio.Semaphore(5)  # Limit concurrent API calls

#     async def generate(self, prompt: str, formated_output: Optional[str] = None) -> Union[str, Dict[str, Any]]:
#         """Generate text from LLM with robust output handling"""
#         headers = {
#             "Content-Type": "application/json",
#             "Authorization": f"Bearer {self.api_key}"
#         }

#         # Format prompt based on desired output
#         formatted_prompt, system_message = self._format_prompt(prompt, formated_output)
        
#         data = {
#             "model": self.model,
#             "messages": [
#                 {"role": "system", "content": system_message},
#                 {"role": "user", "content": formatted_prompt}
#             ],
#             "max_tokens": self.max_tokens,
#             "temperature": self.temperature
#         }

#         async with self.semaphore:
#             try:
#                 self.logger.debug(f"Sending request to Groq API: {self.api_url}")
                
#                 async with aiohttp.ClientSession() as session:
#                     async with session.post(
#                         self.api_url,
#                         headers=headers,
#                         json=data,
#                         timeout=aiohttp.ClientTimeout(total=self.timeout)
#                     ) as response:
                        
#                         if response.status != 200:
#                             error_msg = await response.text()
#                             self.logger.error(f"API request failed with status {response.status}: {error_msg}")
#                             return {"error": f"API request failed: {error_msg}"}
                        
#                         result = await response.json()
#                         generated_text = result["choices"][0]["message"]["content"]

#                         # Process output based on requested format
#                         if formated_output == "json":
#                             return self._parse_json_response(generated_text)
#                         elif formated_output == "code":
#                             return self._extract_code(generated_text)
#                         return generated_text

#             except aiohttp.ClientError as e:
#                 self.logger.error(f"HTTP request failed: {str(e)}")
#                 return {"error": f"HTTP request failed: {str(e)}"}
#             except asyncio.TimeoutError:
#                 self.logger.error(f"Request timed out after {self.timeout} seconds")
#                 return {"error": f"Request timed out after {self.timeout} seconds"}
#             except Exception as e:
#                 return {"error": f"Unexpected error: {str(e)}"}

#     def _format_prompt(self, prompt: str, output_format: Optional[str]) -> tuple[str, str]:
#         """Format prompt and system message based on desired output format"""
#         formatted_prompt = prompt
#         system_message = "You are a helpful AI assistant specialized in coding tasks."
        
#         if output_format == "json":
#             formatted_prompt = f"{prompt}\n\nRespond with valid JSON only, no additional text or explanations."
#             system_message = "You are a helpful AI assistant that always responds with valid, properly formatted JSON."
#         elif output_format == "code":
#             formatted_prompt = f"{prompt}\n\nRespond with code only, no explanations, comments, or markdown formatting."
#             system_message = "You are a helpful AI assistant that always responds with clean, correct code without any additional text."
        
#         return formatted_prompt, system_message

#     def _parse_json_response(self, text: str) -> Dict[str, Any]:
#         """More robust JSON parsing with multiple strategies"""
#         # Strategy 1: Direct parse
#         try:
#             return json.loads(text)
#         except json.JSONDecodeError:
#             pass
        
#         # Strategy 2: Extract from markdown
#         json_str = self._extract_from_markdown(text, "json")
#         if json_str:
#             try:
#                 return json.loads(json_str)
#             except json.JSONDecodeError:
#                 pass
        
#         # Strategy 3: Find JSON object in text
#         try:
#             # Find the first { and last }
#             start = text.find('{')
#             end = text.rfind('}') + 1
#             if start != -1 and end != -1:
#                 return json.loads(text[start:end])
#         except Exception:
#             pass
        
#         # Strategy 4: Try parsing as JSON lines
#         try:
#             lines = [line for line in text.split('\n') if line.strip()]
#             if len(lines) == 1:
#                 return json.loads(lines[0])
#             return [json.loads(line) for line in lines if line.strip()]
#         except Exception:
#             pass
        
#         # Final fallback
#         self.logger.error("All JSON parsing strategies failed")
#         return {"error": "Invalid JSON response", "raw_response": text[:500] + "..."}

#     def _extract_code(self, text: str) -> str:
#         """Extract clean code from response"""
#         # Remove markdown code blocks if present
#         if "```" in text:
#             try:
#                 # Extract code between markdown code blocks
#                 parts = text.split("```")
#                 # Get all code blocks (every second part after first split)
#                 code_blocks = [parts[i].strip() for i in range(1, len(parts), 2)]
#                 if code_blocks:
#                     # Take the longest code block
#                     code = max(code_blocks, key=len)
#                     # Remove language identifier if present
#                     if '\n' in code:
#                         first_line, rest = code.split('\n', 1)
#                         if any(first_line.startswith(lang) for lang in ["python", "javascript", "bash", "json"]):
#                             return rest.strip()
#                     return code.strip()
#             except Exception as e:
#                 self.logger.error(f"Failed to extract code from markdown: {str(e)}")
        
#         return text.strip()

#     def _extract_from_markdown(self, text: str, lang: Optional[str] = None) -> Optional[str]:
#         """Extract content from markdown code blocks"""
#         try:
#             if lang and f"```{lang}" in text:
#                 parts = text.split(f"```{lang}")
#                 if len(parts) > 1:
#                     return parts[1].split("```")[0].strip()
#             elif "```" in text:
#                 parts = text.split("```")
#                 if len(parts) > 1:
#                     return parts[1].split("```")[0].strip()
#         except Exception as e:
#             self.logger.error(f"Error extracting from markdown: {str(e)}")
#         return None

"""
LLM adapter for the AI Coding Agent with async support
"""

import logging
import json
import aiohttp
import asyncio
from typing import Dict, List, Optional, Any, Union
from utils.logger import get_logger
from aiolimiter import AsyncLimiter

# Global limiter (15 requests per minute)
gemini_rate_limiter = AsyncLimiter(10, 60)  # 15 requests per minute

class LLMAdapter:
    def __init__(self, config: Dict[str, Any]):
        # Initialize the logger
        self.logger = get_logger(__name__)
        # Set the configuration
        self.config = config

        # Gemini API configuration
        self.api_key = config["api_key"]
        self.model = config.get("model", "gemini-2.0-flash")
        self.api_url = config.get(
                        "api_url", 
                        f"https://generativelanguage.googleapis.com/v1/models/{self.model}:generateContent"
                        )
        self.max_output_tokens = config.get("max_output_tokens", 4000) # Gemini uses max_output_tokens
        self.temperature = config.get("temperature", 0.7)
        self.timeout = config.get("timeout", 30)  # timeout in seconds

        # Rate limiting
        self.semaphore = asyncio.Semaphore(5)  # Limit concurrent API calls

    async def generate(self, prompt: str, formated_output: Optional[str] = None) -> Union[str, Dict[str, Any]]:
        """Generate text from LLM with robust output handling"""
        headers = {
            "Content-Type": "application/json",
        }
        params = {"key": self.api_key}

        # Format prompt based on desired output
        formatted_prompt, system_message = self._format_prompt(prompt, formated_output)

        data = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": system_message}]
                },
                {
                    "role": "model",
                    "parts": [{"text": "Okay, I understand."}] # Initial response from the model
                },
                {
                    "role": "user",
                    "parts": [{"text": formatted_prompt}]
                }
            ],
            "generationConfig": {
                "maxOutputTokens": self.max_output_tokens,
                "temperature": self.temperature
            }
        }

        async with self.semaphore, gemini_rate_limiter:
            try:
                self.logger.debug(f"Sending request to Gemini API: {self.api_url}")

                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        self.api_url,
                        headers=headers,
                        params=params,
                        json=data,
                        timeout=aiohttp.ClientTimeout(total=self.timeout)
                    ) as response:

                        if response.status != 200:
                            error_msg = await response.text()
                            self.logger.error(f"API request failed with status {response.status}: {error_msg}")
                            return {"error": f"API request failed: {error_msg}"}

                        result = await response.json()
                        # Gemini response structure is different
                        if "candidates" in result and result["candidates"]:
                            generated_text = result["candidates"][0]["content"]["parts"][0]["text"]

                            # Process output based on requested format
                            if formated_output == "json":
                                return self._parse_json_response(generated_text)
                            elif formated_output == "code":
                                return self._extract_code(generated_text)
                            return generated_text
                        else:
                            self.logger.warning(f"No candidates found in Gemini API response: {result}")
                            return {"error": "No response from the model"}

            except aiohttp.ClientError as e:
                self.logger.error(f"HTTP request failed: {str(e)}")
                return {"error": f"HTTP request failed: {str(e)}"}
            except asyncio.TimeoutError:
                self.logger.error(f"Request timed out after {self.timeout} seconds")
                return {"error": f"Request timed out after {self.timeout} seconds"}
            except Exception as e:
                return {"error": f"Unexpected error: {str(e)}"}

    def _format_prompt(self, prompt: str, output_format: Optional[str]) -> tuple[str, str]:
        """Format prompt and system message based on desired output format"""
        formatted_prompt = prompt
        system_message = "You are a helpful AI assistant specialized in coding tasks."

        if output_format == "json":
            formatted_prompt = f"{prompt}\n\nRespond with valid JSON only, no additional text or explanations."
            system_message = "You are a helpful AI assistant that always responds with valid, properly formatted JSON."
        elif output_format == "code":
            formatted_prompt = f"{prompt}\n\nRespond with code only, no explanations, comments, or markdown formatting."
            system_message = "You are a helpful AI assistant that always responds with clean, correct code without any additional text."

        return formatted_prompt, system_message

    def _parse_json_response(self, text: str) -> Dict[str, Any]:
        """More robust JSON parsing with multiple strategies"""
        # Strategy 1: Direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Strategy 2: Extract from markdown
        json_str = self._extract_from_markdown(text, "json")
        if json_str:
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass

        # Strategy 3: Find JSON object in text
        try:
            # Find the first { and last }
            start = text.find('{')
            end = text.rfind('}') + 1
            if start != -1 and end != -1:
                return json.loads(text[start:end])
        except Exception:
            pass

        # Strategy 4: Try parsing as JSON lines
        try:
            lines = [line for line in text.split('\n') if line.strip()]
            if len(lines) == 1:
                return json.loads(lines[0])
            return [json.loads(line) for line in lines if line.strip()]
        except Exception:
            pass

        # Final fallback
        self.logger.error("All JSON parsing strategies failed")
        return {"error": "Invalid JSON response", "raw_response": text[:500] + "..."}

    def _extract_code(self, text: str) -> str:
        """Extract clean code from response"""
        # Remove markdown code blocks if present
        if "```" in text:
            try:
                # Extract code between markdown code blocks
                parts = text.split("```")
                # Get all code blocks (every second part after first split)
                code_blocks = [parts[i].strip() for i in range(1, len(parts), 2)]
                if code_blocks:
                    # Take the longest code block
                    code = max(code_blocks, key=len)
                    # Remove language identifier if present
                    if '\n' in code:
                        first_line, rest = code.split('\n', 1)
                        if any(first_line.startswith(lang) for lang in ["python", "javascript", "bash", "json"]):
                            return rest.strip()
                    return code.strip()
            except Exception as e:
                self.logger.error(f"Failed to extract code from markdown: {str(e)}")

        return text.strip()

    def _extract_from_markdown(self, text: str, lang: Optional[str] = None) -> Optional[str]:
        """Extract content from markdown code blocks"""
        try:
            if lang and f"```{lang}" in text:
                parts = text.split(f"```{lang}")
                if len(parts) > 1:
                    return parts[1].split("```")[0].strip()
            elif "```" in text:
                parts = text.split("```")
                if len(parts) > 1:
                    return parts[1].split("```")[0].strip()
        except Exception as e:
            self.logger.error(f"Error extracting from markdown: {str(e)}")
        return None