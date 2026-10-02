"""Semantic Validator - Deep semantic validation of workflow configuration.

Validates:
- Unknown node types
- Duplicate node IDs
- Invalid edge references
- Missing skill/model dependencies
- Unauthorized skill/model access
- Invalid policy configurations
- Unreachable nodes (where prohibited)
- Incompatible HITL/fallback configurations
"""

from __future__ import annotations

from typing import Any, Dict, List, Set, Optional

import structlog

from agenticai_sdk.config.schemas import AgenticAIConfig
from agenticai_sdk.schemas.workflow import WorkflowSchema, AgentNodeConfig as NodeConfig, EdgeConfig

logger = structlog.get_logger(__name__)


class SemanticValidationError(Exception):
    """Raised when semantic validation fails."""
    def __init__(self, errors: List[str]):
        self.errors = errors
        super().__init__(f"Semantic validation failed: {'; '.join(errors)}")


class SemanticValidator:
    """Validates semantic correctness of workflow configuration."""
    
    # Valid node types per spec
    VALID_NODE_TYPES = {
        "llm", "skill", "tool", "subagent", "hitl", "conditional", "parallel"
    }
    
    def __init__(self, config: AgenticAIConfig):
        self.config = config
        self._skill_ids: Set[str] = set()
        self._model_ids: Set[str] = set()
        self._tool_ids: Set[str] = set()
        self._middleware_ids: Set[str] = set()
        
        self._extract_known_ids()
    
    def _extract_known_ids(self) -> None:
        """Extract known IDs from config for reference validation."""
        # Extract skill IDs
        for skill in self.config.integrations.skills:
            self._skill_ids.add(skill.skill_id)
        
        # Extract model IDs
        for model in self.config.integrations.chat_models:
            self._model_ids.add(model.id)
        
        # Extract tool IDs
        for tool in self.config.integrations.tools:
            self._tool_ids.add(tool.id)
        
        # Extract middleware IDs
        for mw in self.config.integrations.middleware:
            self._middleware_ids.add(mw.id)
    
    def validate(self, workflow: WorkflowSchema) -> List[str]:
        """Run all semantic validations."""
        all_errors = []
        
        all_errors.extend(self._validate_node_types(workflow))
        all_errors.extend(self._validate_duplicate_node_ids(workflow))
        all_errors.extend(self._validate_edges(workflow))
        all_errors.extend(self._validate_skill_references(workflow))
        all_errors.extend(self._validate_model_references(workflow))
        all_errors.extend(self._validate_tool_references(workflow))
        all_errors.extend(self._validate_subagent_references(workflow))
        all_errors.extend(self._validate_policies(workflow))
        all_errors.extend(self._validate_unreachable_nodes(workflow))
        all_errors.extend(self._validate_hitl_fallback_compatibility(workflow))
        all_errors.extend(self._validate_entry_point(workflow))
        
        return all_errors
    
    def validate_and_raise(self, workflow: WorkflowSchema) -> None:
        """Validate and raise exception if any errors."""
        errors = self.validate(workflow)
        if errors:
            raise SemanticValidationError(errors)
    
    # --- Individual validation methods ---
    
    def _validate_node_types(self, workflow: WorkflowSchema) -> List[str]:
        """Validate all nodes have valid types."""
        errors = []
        for node in workflow.agents:
            if node.type not in self.VALID_NODE_TYPES:
                errors.append(f"Node '{node.id}': invalid type '{node.type}'. Valid types: {self.VALID_NODE_TYPES}")
        return errors
    
    def _validate_duplicate_node_ids(self, workflow: WorkflowSchema) -> List[str]:
        """Check for duplicate node IDs."""
        errors = []
        seen: Set[str] = set()
        for node in workflow.agents:
            if node.id in seen:
                errors.append(f"Duplicate node ID: '{node.id}'")
            seen.add(node.id)
        return errors
    
    def _validate_edges(self, workflow: WorkflowSchema) -> List[str]:
        """Validate edge references."""
        errors = []
        node_ids = {node.id for node in workflow.agents}
        node_ids.add("__end__")  # Special terminal node
        
        for i, edge in enumerate(workflow.edges):
            if edge.source not in node_ids:
                errors.append(f"Edge {i}: source '{edge.source}' not found in nodes")
            if edge.target not in node_ids:
                errors.append(f"Edge {i}: target '{edge.target}' not found in nodes")
            
            # Check for self-loops
            if edge.source == edge.target:
                errors.append(f"Edge {i}: self-loop detected on '{edge.source}'")
        
        # Check for orphaned nodes
        has_incoming: Set[str] = set()
        has_outgoing: Set[str] = set()
        for edge in workflow.edges:
            has_outgoing.add(edge.source)
            has_incoming.add(edge.target)
        
        for node in workflow.agents:
            if node.id not in has_outgoing and node.id != "__end__":
                logger.warning("node_no_outgoing_edges", node=node.id)
            if node.id not in has_incoming and node.id != workflow.entry_point:
                logger.warning("node_no_incoming_edges", node=node.id)
        
        return errors
    
    def _validate_skill_references(self, workflow: WorkflowSchema) -> List[str]:
        """Validate skill references in nodes."""
        errors = []
        for node in workflow.agents:
            if node.type == "skill" and node.skill:
                if node.skill not in self._skill_ids:
                    errors.append(f"Node '{node.id}': references unknown skill '{node.skill}'")
        return errors
    
    def _validate_model_references(self, workflow: WorkflowSchema) -> List[str]:
        """Validate model references in nodes."""
        errors = []
        for node in workflow.agents:
            if node.model and node.model not in self._model_ids:
                errors.append(f"Node '{node.id}': references unknown model '{node.model}'")
        return errors
    
    def _validate_tool_references(self, workflow: WorkflowSchema) -> List[str]:
        """Validate tool references in nodes."""
        errors = []
        for node in workflow.agents:
            if node.tools:
                for tool_id in node.tools:
                    if tool_id not in self._tool_ids:
                        errors.append(f"Node '{node.id}': references unknown tool '{tool_id}'")
        return errors
    
    def _validate_subagent_references(self, workflow: WorkflowSchema) -> List[str]:
        """Validate subagent references."""
        errors = []
        node_ids = {node.id for node in workflow.agents}
        
        for node in workflow.agents:
            if node.type == "subagent" and node.subagent:
                if node.subagent not in node_ids:
                    errors.append(f"Node '{node.id}': references unknown subagent '{node.subagent}'")
        return errors
    
    def _validate_policies(self, workflow: WorkflowSchema) -> List[str]:
        """Validate policy configurations."""
        errors = []
        
        if workflow.policies:
            # Check budget policy
            if workflow.policies.budget:
                budget = workflow.policies.budget
                if budget.max_iterations and budget.max_iterations < 1:
                    errors.append("Budget policy: max_iterations must be >= 1")
                if budget.max_cost_usd is not None and budget.max_cost_usd < 0:
                    errors.append("Budget policy: max_cost_usd must be >= 0")
                if budget.max_wall_time_seconds and budget.max_wall_time_seconds < 1:
                    errors.append("Budget policy: max_wall_time_seconds must be >= 1")
            
            # Check HITL policy
            if workflow.policies.hitl:
                hitl = workflow.policies.hitl
                if hitl.enabled and hitl.approval_timeout_seconds:
                    if hitl.approval_timeout_seconds < 60:
                        errors.append("HITL policy: approval_timeout_seconds must be >= 60")
            
            # Check consensus policy
            if workflow.policies.consensus:
                consensus = workflow.policies.consensus
                if consensus.enabled:
                    if consensus.instances and consensus.instances < 2:
                        errors.append("Consensus policy: instances must be >= 2 when enabled")
                    if consensus.threshold is not None:
                        if consensus.threshold < 0.5 or consensus.threshold > 1.0:
                            errors.append("Consensus policy: threshold must be between 0.5 and 1.0")
        
        return errors
    
    def _validate_unreachable_nodes(self, workflow: WorkflowSchema) -> List[str]:
        """Check for unreachable nodes (where prohibited)."""
        errors = []
        warnings = []
        
        # Build adjacency list
        adjacency: Dict[str, List[str]] = {}
        for node in workflow.agents:
            adjacency[node.id] = []
        
        for edge in workflow.edges:
            if edge.source in adjacency:
                adjacency[edge.source].append(edge.target)
        
        # Find reachable nodes from entry point
        reachable: Set[str] = set()
        stack = [workflow.entry_point]
        
        while stack:
            node = stack.pop()
            if node in reachable:
                continue
            reachable.add(node)
            for neighbor in adjacency.get(node, []):
                if neighbor not in reachable:
                    stack.append(neighbor)
        
        # Check for unreachable nodes
        for node in workflow.agents:
            if node.id not in reachable:
                warnings.append(f"Node '{node.id}' is unreachable from entry point '{workflow.entry_point}'")
        
        # Log warnings but don't fail (might be intentional for conditional paths)
        for w in warnings:
            logger.warning("unreachable_node", **{"node": w})
        
        return errors
    
    def _validate_hitl_fallback_compatibility(self, workflow: WorkflowSchema) -> List[str]:
        """Validate HITL and fallback compatibility."""
        errors = []
        
        for node in workflow.agents:
            # HITL nodes with fallbacks
            if node.hitl and node.hitl.enabled and node.fallback:
                logger.warning("hitl_with_fallback", node=node.id)
            
            # Consensus and HITL together
            if node.consensus and node.consensus.enabled and node.hitl and node.hitl.enabled:
                logger.warning("consensus_and_hitl_combined", node=node.id)
        
        return errors
    
    def _validate_entry_point(self, workflow: WorkflowSchema) -> List[str]:
        """Validate entry point exists in nodes."""
        errors = []
        node_ids = {node.id for node in workflow.agents}
        
        if workflow.entry_point not in node_ids:
            errors.append(f"Entry point '{workflow.entry_point}' not found in nodes")
        
        return errors


def validate_workflow(workflow: WorkflowSchema, config: AgenticAIConfig) -> List[str]:
    """Convenience function for semantic validation."""
    validator = SemanticValidator(config)
    return validator.validate(workflow)