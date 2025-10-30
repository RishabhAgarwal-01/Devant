"""
Enhanced graph utility functions with Redis support
Now used by DependencyManager
"""
import networkx as nx
from typing import List, Dict, Optional
from adapters.redis_adapter import RedisAdapter
from utils.logger import get_logger
import json
import hashlib

logger = get_logger(__name__)

async def build_dependency_graph(files: List[str], dependencies: Dict[str, List[str]], 
                               redis: Optional[RedisAdapter] = None, 
                               cache_key: Optional[str] = None) -> nx.DiGraph:
    """
    Build a dependency graph with optional Redis caching
    Args:
        files: List of file paths
        dependencies: Dictionary of file to its dependencies
        redis: Optional Redis adapter
        cache_key: Optional Redis key for caching
    """
    # Try to load from cache
    if redis and cache_key:
        try:
            cached = await redis.get_context(f"graph_cache:{cache_key}")
            if cached:
                logger.debug(f"Loaded cached graph for {cache_key}")
                return nx.node_link_graph(json.loads(cached))
        except Exception as e:
            logger.warning(f"Failed to load cached graph: {str(e)}")
    
    # Build fresh graph
    graph = nx.DiGraph()
    
    for file in files:
        graph.add_node(file)
        
    for file, deps in dependencies.items():
        for dep in deps:
            if dep in files:  # Only add edges for existing files
                graph.add_edge(file, dep)
    
    # Store in cache if requested
    if redis and cache_key:
        try:
            await redis.store_context(
                f"graph_cache:{cache_key}",
                json.dumps(nx.node_link_data(graph)))
        except Exception as e:
            logger.warning(f"Failed to cache graph: {str(e)}")
                
    return graph
    
def find_execution_order(graph: nx.DiGraph) -> List[str]:
    """
    Find optimal execution order based on dependencies
    Returns:
        List of files in execution order
    Raises:
        ValueError if graph contains cycles
    """
    if not nx.is_directed_acyclic_graph(graph):
        raise ValueError("Graph contains cycles - cannot determine execution order")
    return list(nx.topological_sort(graph))
    
def find_circular_dependencies(graph: nx.DiGraph) -> List[List[str]]:
    """Find all circular dependencies in the graph"""
    return list(nx.simple_cycles(graph))

def find_impacted_files(graph: nx.DiGraph, changed_files: List[str]) -> Dict[str, List[str]]:
    """
    Find all files impacted by changes to given files
    Returns:
        Dictionary of {changed_file: [impacted_files]}
    """
    impact_map = {}
    for file in changed_files:
        if file in graph:
            impact_map[file] = list(nx.descendants(graph, file))
    return impact_map

async def visualize_graph(graph: nx.DiGraph, output_path: str, 
                         redis: Optional[RedisAdapter] = None,
                         cache_key: Optional[str] = None):
    """
    Visualize graph and optionally cache the visualization
    """
    try:
        import matplotlib.pyplot as plt
        plt.figure(figsize=(16, 12))
        pos = nx.spring_layout(graph, k=0.5, iterations=50)
        nx.draw(graph, pos, with_labels=True, node_size=1200, 
               font_size=8, arrowsize=10)
        plt.savefig(output_path)
        
        # Store visualization in Redis if requested
        if redis and cache_key:
            try:
                with open(output_path, "rb") as f:
                    await redis.store_context(
                        f"graph_viz:{cache_key}",
                        f.read().hex()
                    )
            except Exception as e:
                logger.warning(f"Failed to cache visualization: {str(e)}")
                
    except ImportError:
        logger.warning("Visualization requires matplotlib - skipping")
    except Exception as e:
        logger.error(f"Failed to visualize graph: {str(e)}")