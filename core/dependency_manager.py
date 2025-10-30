"""
Enhanced Dependency management using NetworkX with Redis persistence
Now leveraging graph_utils for common operations
"""
import networkx as nx
from typing import Dict, List, Optional
from utils.logger import get_logger
from adapters.redis_adapter import RedisAdapter
import json
import hashlib
from utils.graph_utils import (
    build_dependency_graph,
    find_execution_order,
    find_circular_dependencies,
    find_impacted_files,
    visualize_graph
)

class DependencyManager:
    def __init__(self, redis_adapter: Optional[RedisAdapter] = None):
        self.graph = nx.DiGraph()
        self.redis = redis_adapter
        self.logger = get_logger(__name__)
        
    async def load_from_redis(self, project_id: str) -> bool:
        """Load dependency graph from Redis"""
        if not self.redis:
            return False
            
        try:
            graph_data = await self.redis.get_context(f"depgraph:{project_id}")
            if graph_data:
                self.graph = nx.node_link_graph(json.loads(graph_data))
                return True
        except Exception as e:
            self.logger.error(f"Error loading graph from Redis: {str(e)}")
        return False
        
    async def save_to_redis(self, project_id: str) -> bool:
        """Save dependency graph to Redis"""
        if not self.redis:
            return False
            
        try:
            graph_data = json.dumps(nx.node_link_data(self.graph))
            return await self.redis.store_context(
                f"depgraph:{project_id}",
                graph_data
            )
        except Exception as e:
            self.logger.error(f"Error saving graph to Redis: {str(e)}")
            return False
        
    def add_file(self, file_path: str, dependencies: List[str] = None):
        """Add a file with its dependencies to the graph"""
        self.graph.add_node(file_path)
        if dependencies:
            for dep in dependencies:
                if dep in self.graph:  # Only add edges for existing files
                    self.graph.add_edge(file_path, dep)
        self.logger.debug(f"Added file to dependency graph: {file_path}")
        
    def remove_file(self, file_path: str):
        """Remove a file from the dependency graph"""
        if file_path in self.graph:
            self.graph.remove_node(file_path)
            self.logger.debug(f"Removed file from dependency graph: {file_path}")
            
    def get_dependencies(self, file_path: str) -> List[str]:
        """Get all dependencies for a file"""
        if file_path not in self.graph:
            return []
        return list(self.graph.successors(file_path))
        
    def get_dependents(self, file_path: str) -> List[str]:
        """Get all files that depend on this file"""
        if file_path not in self.graph:
            return []
        return list(self.graph.predecessors(file_path))
        
    def find_impact(self, file_path: str) -> List[str]:
        """Find all files that would be impacted by changes to this file"""
        if file_path not in self.graph:
            return []
        return list(nx.descendants(self.graph, file_path))
        
    def find_cycles(self) -> List[List[str]]:
        """Find circular dependencies in the graph"""
        return find_circular_dependencies(self.graph)
        
    def get_execution_order(self) -> List[str]:
        """Get optimal execution order (topological sort)"""
        try:
            return find_execution_order(self.graph)
        except ValueError as e:
            self.logger.warning(str(e))
            return []
        
    async def visualize(self, output_path: str = "dependencies.png"):
        """Visualize the dependency graph with Redis caching"""
        try:
            cache_key = None
            if self.redis:
                cache_key = f"depgraph_viz:{hashlib.sha256(output_path.encode()).hexdigest()}"
            
            await visualize_graph(
                self.graph, 
                output_path,
                self.redis,
                cache_key
            )
            self.logger.info(f"Dependency graph visualized at {output_path}")
        except Exception as e:
            self.logger.error(f"Error visualizing graph: {str(e)}")