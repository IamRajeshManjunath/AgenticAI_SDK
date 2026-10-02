"""Dependency Resolver - Topological sort and cycle detection for workflow graphs."""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any, Dict, List, Set, Tuple, Optional

import structlog

from agenticai_sdk.schemas.workflow import EdgeConfig, WorkflowSchema

logger = structlog.get_logger(__name__)


class CycleDetectedError(Exception):
    """Raised when a cycle is detected in the workflow graph."""
    def __init__(self, cycle: List[str]):
        self.cycle = cycle
        super().__init__(f"Cycle detected: {' -> '.join(cycle)}")


class DependencyResolver:
    """Resolves dependencies and performs topological sorting on workflow graphs."""
    
    def __init__(self, workflow: WorkflowSchema):
        self.workflow = workflow
        self.node_ids = {node.id for node in workflow.agents}
        self.node_ids.add("__end__")  # Special terminal node
        
        # Build adjacency list and reverse adjacency
        self.adjacency: Dict[str, List[str]] = defaultdict(list)
        self.reverse_adjacency: Dict[str, List[str]] = defaultdict(list)
        self.edge_conditions: Dict[Tuple[str, str], Optional[str]] = {}
        
        self._build_graph()
    
    def _build_graph(self) -> None:
        """Build adjacency lists from edges."""
        for edge in self.workflow.edges:
            self.adjacency[edge.source].append(edge.target)
            self.reverse_adjacency[edge.target].append(edge.source)
            self.edge_conditions[(edge.source, edge.target)] = edge.condition
    
    def topological_sort(self) -> List[str]:
        """Perform topological sort using Kahn's algorithm.
        
        Returns:
            List of node IDs in topological order.
        
        Raises:
            CycleDetectedError: If a cycle is detected.
        """
        # Calculate in-degrees
        in_degree: Dict[str, int] = defaultdict(int)
        for node in self.node_ids:
            in_degree[node] = 0
        
        for edge in self.workflow.edges:
            if edge.target in self.node_ids:
                in_degree[edge.target] += 1
        
        # Initialize queue with nodes having in-degree 0
        queue = deque([node for node in self.node_ids if in_degree[node] == 0])
        result = []
        
        while queue:
            node = queue.popleft()
            result.append(node)
            
            for neighbor in self.adjacency[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        # Check for cycles
        if len(result) != len(self.node_ids):
            # Find the cycle
            cycle = self._find_cycle()
            raise CycleDetectedError(cycle)
        
        return result
    
    def _find_cycle(self) -> List[str]:
        """Find a cycle using DFS."""
        visited: Set[str] = set()
        rec_stack: Set[str] = set()
        parent: Dict[str, Optional[str]] = {}
        
        def dfs(node: str) -> Optional[List[str]]:
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in self.adjacency[node]:
                if neighbor not in visited:
                    parent[neighbor] = node
                    cycle = dfs(neighbor)
                    if cycle:
                        return cycle
                elif neighbor in rec_stack:
                    # Found cycle - reconstruct it
                    cycle = [neighbor]
                    curr = node
                    while curr != neighbor:
                        cycle.append(curr)
                        curr = parent[curr]
                    cycle.append(neighbor)
                    cycle.reverse()
                    return cycle
            
            rec_stack.remove(node)
            return None
        
        for node in self.node_ids:
            if node not in visited:
                parent[node] = None
                cycle = dfs(node)
                if cycle:
                    return cycle
        
        return ["unknown_cycle"]
    
    def get_execution_levels(self) -> List[List[str]]:
        """Get execution levels for parallel execution.
        
        Returns list of levels, where each level contains nodes that can
        execute in parallel (all dependencies satisfied).
        """
        in_degree: Dict[str, int] = defaultdict(int)
        for node in self.node_ids:
            in_degree[node] = 0
        
        for edge in self.workflow.edges:
            if edge.target in self.node_ids:
                in_degree[edge.target] += 1
        
        levels = []
        current_level = [node for node in self.node_ids if in_degree[node] == 0]
        
        while current_level:
            levels.append(current_level)
            next_level = []
            
            for node in current_level:
                for neighbor in self.adjacency[node]:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        next_level.append(neighbor)
            
            current_level = next_level
        
        # Check if all nodes were processed
        total_processed = sum(len(level) for level in levels)
        if total_processed != len(self.node_ids):
            # Cycle detected - return simple order
            logger.warning("cycle_detected_in_levels_fallback")
            return [list(self.node_ids)]
        
        return levels
    
    def get_dependencies(self, node_id: str) -> List[str]:
        """Get direct dependencies (incoming edges) for a node."""
        return list(self.reverse_adjacency.get(node_id, []))
    
    def get_dependents(self, node_id: str) -> List[str]:
        """Get direct dependents (outgoing edges) for a node."""
        return list(self.adjacency.get(node_id, []))
    
    def get_edge_condition(self, source: str, target: str) -> Optional[str]:
        """Get condition expression for an edge."""
        return self.edge_conditions.get((source, target))
    
    def is_reachable(self, from_node: str, to_node: str) -> bool:
        """Check if to_node is reachable from from_node."""
        visited = set()
        stack = [from_node]
        
        while stack:
            node = stack.pop()
            if node == to_node:
                return True
            if node in visited:
                continue
            visited.add(node)
            stack.extend(self.adjacency.get(node, []))
        
        return False
    
    def get_all_paths(self, from_node: str, to_node: str, max_paths: int = 100) -> List[List[str]]:
        """Find all paths from from_node to to_node (limited)."""
        paths = []
        
        def dfs(current: str, path: List[str]) -> None:
            if len(paths) >= max_paths:
                return
            if current == to_node:
                paths.append(path)
                return
            
            for neighbor in self.adjacency.get(current, []):
                if neighbor not in path:  # Avoid cycles
                    dfs(neighbor, path + [neighbor])
        
        dfs(from_node, [from_node])
        return paths


def resolve_dependencies(workflow: WorkflowSchema) -> DependencyResolver:
    """Create and return a DependencyResolver for the workflow."""
    return DependencyResolver(workflow)


def topological_sort(workflow: WorkflowSchema) -> List[str]:
    """Convenience function for topological sort."""
    resolver = DependencyResolver(workflow)
    return resolver.topological_sort()


def get_execution_levels(workflow: WorkflowSchema) -> List[List[str]]:
    """Convenience function for execution levels."""
    resolver = DependencyResolver(workflow)
    return resolver.get_execution_levels()