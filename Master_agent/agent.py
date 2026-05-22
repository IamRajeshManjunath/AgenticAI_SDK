"""Master Agent for intent parsing, strict JSON schema synthesis, and Downstream compiler binding."""

from __future__ import annotations
import os
import uuid
import json
from typing import Any

from agenticai_sdk.schemas.workflow import WorkflowSchema
from agenticai_sdk.schemas.agent_node import AgentNodeConfig
from agenticai_sdk.schemas.edges import EdgeConfig
from agenticai_sdk.schemas.tools import ToolConfig
from agenticai_sdk.schemas.rag import RAGConfig
from agenticai_sdk.schemas.llm import LLMConfig

from Master_agent.rag import MasterAgentRAG

class StructuredMasterAgent:
    """Upstream Master Agent acting as primary system ingress."""
    
    def __init__(self, workspace_root: str | None = None):
        self.rag = MasterAgentRAG(workspace_root=workspace_root)
        
    def generate_proposal(self, user_prompt: str) -> dict[str, Any]:
        """Ingest user automation request, run RAG, and synthesize a strict WorkflowSchema JSON."""
        # 1. Retrieve system-specific context from RAG
        context_chunks = self.rag.retrieve(user_prompt, top_k=2)
        context_str = "\n\n".join([f"Source: {c['source']}\n{c['content']}" for c in context_chunks])
        
        # 2. Synthesize Schema via Structured Decoding / Fallback Rule-based compilation
        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        
        proposal = None
        if api_key and (os.getenv("OPENAI_API_KEY") or "").startswith("sk-"):
            try:
                from langchain_openai import ChatOpenAI
                from langchain_core.prompts import ChatPromptTemplate
                
                # Setup structured LLM call
                llm = ChatOpenAI(model="gpt-4o", temperature=0)
                structured_llm = llm.with_structured_output(WorkflowSchema)
                
                prompt_tpl = ChatPromptTemplate.from_messages([
                    ("system", (
                        "You are the Upstream Master Agent for Harpy.AI. "
                        "Synthesize a strict, valid, end-to-end multi-agent WorkflowSchema "
                        "matching the user's requirements. "
                        "Verify referential integrity:\n"
                        "1. Every edge source and target must be a declared agent_id (target can be __end__).\n"
                        "2. entry_point must match one of the agent_ids.\n"
                        "3. Tools/RAG references inside agents must exist in the global tools/rag_sources lists.\n\n"
                        "System Reference Context:\n{context}"
                    )),
                    ("user", "User Request: {request}")
                ])
                
                chain = prompt_tpl | structured_llm
                proposal = chain.invoke({"request": user_prompt, "context": context_str})
            except Exception as e:
                print(f"Structured LLM synthesis failed: {e}. Falling back to rule-based parser.")
                
        if proposal is None:
            proposal = self._generate_rule_based_fallback(user_prompt)
            
        # Ensure it's returned as a serializable dictionary matching the schema specs
        if isinstance(proposal, WorkflowSchema):
            return proposal.model_dump()
        return proposal

    def _generate_rule_based_fallback(self, user_prompt: str) -> dict[str, Any]:
        """Fallback deterministic synthesis satisfying all Pydantic validators in WorkflowSchema."""
        prompt_lower = user_prompt.lower()
        
        # Determine tools based on query keywords
        tools = []
        agent_tools = []
        if "search" in prompt_lower or "google" in prompt_lower or "web" in prompt_lower:
            tools.append({
                "tool_id": "google_search_api",
                "name": "Google Search",
                "description": "Search the web for real-time information.",
                "type": "rest_api",
                "config": {
                    "endpoint": "https://api.search.com/v1",
                    "method": "GET",
                    "api_key_env_var": "SEARCH_API_KEY"
                }
            })
            agent_tools.append("google_search_api")
            
        if "python" in prompt_lower or "code" in prompt_lower or "script" in prompt_lower or "run" in prompt_lower:
            tools.append({
                "tool_id": "custom_python_script",
                "name": "Python Script Exec",
                "description": "Execute Python code snippets.",
                "type": "custom_python",
                "config": {
                    "code": "def custom_script(data): return data",
                    "arguments": {}
                }
            })
            agent_tools.append("custom_python_script")

        if "weather" in prompt_lower or "temperature" in prompt_lower:
            tools.append({
                "tool_id": "weather_mcp_client",
                "name": "Weather MCP",
                "description": "Fetch weather updates.",
                "type": "mcp",
                "config": {
                    "connection_string": "http://localhost:8001",
                    "arguments": {"mcp_tool_name": "fetch_weather"}
                }
            })
            agent_tools.append("weather_mcp_client")
            
        # Determine RAG sources
        rag_sources = []
        agent_rag = []
        if "rag" in prompt_lower or "kb" in prompt_lower or "knowledge" in prompt_lower or "document" in prompt_lower:
            rag_sources.append({
                "rag_id": "enterprise_kb",
                "vector_db": "qdrant",
                "connection_uri": "http://localhost:6333",
                "api_key_env_var": "QDRANT_API_KEY",
                "embedding_provider": "openai",
                "embedding_model": "text-embedding-3-small",
                "collection_name": "enterprise_docs",
                "top_k": 3,
                "similarity_threshold": 0.7,
                "hybrid_search": True
            })
            agent_rag.append("enterprise_kb")
            
        # Build agents
        agents = []
        if "write" in prompt_lower or "writer" in prompt_lower or "report" in prompt_lower or "summarize" in prompt_lower:
            # Multi-agent flow: Coordinator + Specialist
            agents.append({
                "agent_id": "coordinator_agent",
                "role": "Strategic Orchestrator",
                "input_schema": {"type": "object", "properties": {"task": {"type": "string"}}},
                "prompt_template": {
                    "template_id": "coordinator_prompt",
                    "template_string": "Coordinate the execution of: {task}. Delegate tasks to sub-agents.",
                    "input_variables": ["task"]
                },
                "llm": {
                    "provider": "openai",
                    "model_name": "gpt-4o",
                    "temperature": 0.2,
                    "api_key_env_var": "OPENAI_API_KEY"
                },
                "sub_agents": ["specialist_agent"],
                "tools": [],
                "rag_sources": [],
                "topology": {"orchestration_mode": "model_driven"}
            })
            agents.append({
                "agent_id": "specialist_agent",
                "role": "Technical Specialist",
                "prompt_template": {
                    "template_id": "specialist_prompt",
                    "template_string": "Execute the task using tools and documentation: {task}",
                    "input_variables": ["task"]
                },
                "llm": {
                    "provider": "openai",
                    "model_name": "gpt-4o",
                    "temperature": 0.5,
                    "api_key_env_var": "OPENAI_API_KEY"
                },
                "tools": agent_tools,
                "rag_sources": agent_rag,
                "topology": {"orchestration_mode": "model_driven"}
            })
            edges = [
                {"source": "coordinator_agent", "target": "specialist_agent"},
                {"source": "specialist_agent", "target": "__end__"}
            ]
            entry_point = "coordinator_agent"
        else:
            # Single agent flow
            agents.append({
                "agent_id": "main_agent",
                "role": "General Assistant",
                "input_schema": {"type": "object", "properties": {"task": {"type": "string"}}},
                "prompt_template": {
                    "template_id": "main_prompt",
                    "template_string": "Assist with: {task}",
                    "input_variables": ["task"]
                },
                "llm": {
                    "provider": "openai",
                    "model_name": "gpt-4o",
                    "temperature": 0.5,
                    "api_key_env_var": "OPENAI_API_KEY"
                },
                "tools": agent_tools,
                "rag_sources": agent_rag,
                "topology": {"orchestration_mode": "model_driven"}
            })
            edges = [
                {"source": "main_agent", "target": "__end__"}
            ]
            entry_point = "main_agent"
            
        workflow_data = {
            "workflow_id": f"workflow-{uuid.uuid4().hex[:8]}",
            "name": f"Generated Flow: {user_prompt[:30]}...",
            "description": f"Automatically generated workflow for request: {user_prompt}",
            "tools": tools,
            "rag_sources": rag_sources,
            "agents": agents,
            "edges": edges,
            "entry_point": entry_point,
            "hitl": {
                "interruption_points": [],
                "approval_timeout": 300,
                "notification_channel": "slack"
            }
        }
        
        # Enforce validation and parsing
        validated = WorkflowSchema(**workflow_data)
        return validated.model_dump()
