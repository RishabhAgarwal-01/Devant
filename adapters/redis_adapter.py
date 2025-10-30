"""
Redis adapter for context and memory management
"""
import redis.asyncio as redis
from typing import Dict, List, Optional, Any
import json
from utils.logger import get_logger
import hashlib
import time
from utils.schema import Step  # Import Step class

class RedisAdapter:
    def __init__(self, config: Dict[str, Any]):
        self.client = redis.Redis(
            host=config.get("host", "localhost"),
            port=config.get("port", 6379),
            db=config.get("db", 0),
            decode_responses=True
        )
        self.logger = get_logger(__name__)
        self.namespace = config.get("namespace", "ai_agent")
        
    async def store_context(self, key: str, data: Any, ttl: Optional[int] = None) -> bool:
        """Store context data in Redis with namespace"""
        try:
            from utils.schema import Step  # Import Step class
            
            def default_serializer(obj):
                if isinstance(obj, Step):
                    return obj.__dict__
                raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
                
            full_key = f"{self.namespace}:context:{key}"
            serialized = json.dumps(data, default=default_serializer)
            if ttl:
                await self.client.setex(full_key, ttl, serialized)
            else:
                await self.client.set(full_key, serialized)
            return True
        except Exception as e:
            self.logger.error(f"Error storing context: {str(e)}")
            return False
            
    async def get_context(self, key: str) -> Optional[Dict]:
        """Retrieve context data from Redis with namespace"""
        try:
            full_key = f"{self.namespace}:context:{key}"
            data = await self.client.get(full_key)
            if not data:
                return None

            parsed = json.loads(data)

            # If 'steps' is present, rehydrate Step objects
            if isinstance(parsed, dict) and 'steps' in parsed:
                parsed['steps'] = [Step.from_dict(step) for step in parsed['steps']]

            return parsed
        except Exception as e:
            self.logger.error(f"Error retrieving context: {str(e)}")
            return None
            
    async def store_execution_state(self, task_id: str, state: Dict) -> bool:
        """Store execution state for a task with extended metadata"""
        state_key = f"{self.namespace}:execution:{task_id}"
        try:
            # Convert Steps to dictionaries if present
            if 'plan' in state and state['plan']:
                plan = state['plan']
                state['plan'] = {
                    'understanding': plan.get('understanding'),
                    'files': plan.get('file'),
                    'steps': [step.to_dict() if hasattr(step, 'to_dict') else step for step in plan.get('steps', [])]
                }
            
            if 'completed_steps' in state:
                state['completed_steps'] = [
                    step.to_dict() if hasattr(step, 'to_dict') else step 
                    for step in state['completed_steps']
                ]

            full_state = {
                "state": state,
                "timestamp": int(time.time()),
                "task_id": task_id
            }
            await self.client.set(state_key, json.dumps(full_state))
            return True
        except Exception as e:
            self.logger.error(f"Error storing execution state: {str(e)}")
            return False
            
    async def get_execution_state(self, task_id: str) -> Optional[Dict]:
        """Retrieve execution state for a task"""
        try:
            state_key = f"{self.namespace}:execution:{task_id}"
            data = await self.client.get(state_key)
            if data:
                full_state = json.loads(data)
                return full_state.get("state")
            return None
        except Exception as e:
            self.logger.error(f"Error retrieving execution state: {str(e)}")
            return None
            
    # In redis_adapter.py, modify track_file method
    async def track_file(self, file_path: str, metadata: Dict) -> bool:
        try:
            # Convert metadata to JSON string
            metadata_str = json.dumps(metadata)
            file_key = f"{self.namespace}:file:{hashlib.sha256(file_path.encode()).hexdigest()}"
            await self.client.hset(file_key, "metadata", metadata_str)
            return True
        except Exception as e:
            self.logger.error(f"Error tracking file: {str(e)}")
            return False
            
    async def get_file_metadata(self, file_path: str) -> Optional[Dict]:
        """Get metadata for a file with enhanced lookup"""
        try:
            file_key = f"{self.namespace}:file:{hashlib.sha256(file_path.encode()).hexdigest()}"
            data = await self.client.hgetall(file_key)
            if data and data.get("metadata"):
                return json.loads(data["metadata"])
            return None
        except Exception as e:
            self.logger.error(f"Error getting file metadata: {str(e)}")
            return None
            
    async def track_code_snippet(self, snippet_hash: str, metadata: Dict) -> bool:
        """Track a code snippet and its metadata with relationships"""
        try:
            snippet_key = f"{self.namespace}:snippet:{snippet_hash}"
            
            # Store full metadata
            full_metadata = {
                "hash": snippet_hash,
                "metadata": metadata,
                "timestamp": int(time.time())
            }
            
            # Store in Redis
            await self.client.hset(snippet_key, mapping=full_metadata)
            
            # If the snippet is associated with a file, create relationship
            if "file_path" in metadata:
                file_key = f"{self.namespace}:file:{hashlib.sha256(metadata['file_path'].encode()).hexdigest()}"
                await self.client.sadd(f"{file_key}:snippets", snippet_key)
                
            return True
        except Exception as e:
            self.logger.error(f"Error tracking code snippet: {str(e)}")
            return False
            
    async def get_code_snippet(self, snippet_hash: str) -> Optional[Dict]:
        """Get a code snippet by its hash with metadata"""
        try:
            snippet_key = f"{self.namespace}:snippet:{snippet_hash}"
            data = await self.client.hgetall(snippet_key)
            if data and data.get("metadata"):
                return json.loads(data["metadata"])
            return None
        except Exception as e:
            self.logger.error(f"Error getting code snippet: {str(e)}")
            return None
            
    async def get_related_snippets(self, file_path: str) -> List[Dict]:
        """Get all code snippets related to a file"""
        try:
            file_key = f"{self.namespace}:file:{hashlib.sha256(file_path.encode()).hexdigest()}"
            snippet_keys = await self.client.smembers(f"{file_key}:snippets")
            
            snippets = []
            for key in snippet_keys:
                data = await self.client.hgetall(key)
                if data and data.get("metadata"):
                    snippets.append(data["metadata"])
                    
            return snippets
        except Exception as e:
            self.logger.error(f"Error getting related snippets: {str(e)}")
            return []
            
    async def search_context(self, query: str, limit: int = 10) -> List[Dict]:
        """Search through stored context using pattern matching"""
        try:
            pattern = f"{self.namespace}:context:*{query}*"
            keys = await self.client.keys(pattern)
            
            results = []
            for key in keys[:limit]:
                data = await self.client.get(key)
                if data:
                    try:
                        results.append(json.loads(data))
                    except json.JSONDecodeError:
                        continue
                        
            return results
        except Exception as e:
            self.logger.error(f"Error searching context: {str(e)}")
            return []
            
    async def close(self):
        """Close the Redis connection"""
        await self.client.close()