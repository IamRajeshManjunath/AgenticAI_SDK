"""
ContextEngine — manages runtime prompt rendering, dynamic system instructions,
and historical message window truncation based on MemoryConfig.
"""

from __future__ import annotations

from typing import Any

import structlog
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from agenticai_sdk.schemas.agent_node import AgentNodeConfig
from agenticai_sdk.schemas.memory import ExecutionMemoryType, MemoryConfig

logger = structlog.get_logger(__name__)


class ContextEngine:
    """Manages prompt rendering and message history management.

    Responsibilities:
    - Render prompt templates with runtime variable values
    - Apply sliding-window truncation based on MemoryConfig
    - Build structured system prompts with optional RAG context injection
    - Format message history for inclusion in prompts

    Usage::

        engine = ContextEngine()
        system_msg = engine.build_system_message(agent_config, context_block="...")
        windowed = engine.apply_memory_window(messages, agent_config.memory)
    """

    def render_prompt(
        self,
        config: AgentNodeConfig,
        variables: dict[str, Any],
    ) -> str:
        """Render the agent's prompt template with runtime variable substitution.

        Args:
            config: Agent node configuration containing the prompt template.
            variables: Dict mapping variable names to their runtime values.

        Returns:
            The rendered prompt string.
        """
        template = config.prompt_template.template_string
        try:
            rendered = template.format(**variables)
            logger.debug(
                "prompt_rendered",
                agent_id=config.agent_id,
                template_id=config.prompt_template.template_id,
                variables=list(variables.keys()),
            )
            return rendered
        except KeyError as exc:
            logger.warning(
                "prompt_render_missing_variable",
                agent_id=config.agent_id,
                missing_var=str(exc),
            )
            # Partial render — leave missing vars as literal placeholders
            return template

    def build_system_message(
        self,
        config: AgentNodeConfig,
        context_block: str = "",
        extra_instructions: str = "",
    ) -> SystemMessage:
        """Construct the SystemMessage for an agent node.

        Args:
            config: Agent node configuration.
            context_block: Pre-formatted RAG context text.
            extra_instructions: Any additional runtime instruction text.

        Returns:
            LangChain ``SystemMessage`` ready for injection into the message list.
        """
        parts: list[str] = []

        # Role declaration
        parts.append(f"# Role\nYou are {config.role}.")

        # Core instructions from template
        if config.prompt_template.template_string:
            parts.append(f"\n# Instructions\n{config.prompt_template.template_string}")

        # RAG context block
        if context_block:
            parts.append(f"\n{context_block}")

        # Extra runtime instructions
        if extra_instructions:
            parts.append(f"\n# Additional Context\n{extra_instructions}")

        # Topology instructions
        if config.topology.reasoning_steps:
            steps_text = "\n".join(
                f"  {i+1}. {step}" for i, step in enumerate(config.topology.reasoning_steps)
            )
            parts.append(f"\n# Reasoning Protocol\nFollow these steps:\n{steps_text}")

        system_content = "\n".join(parts)
        logger.debug("system_message_built", agent_id=config.agent_id, length=len(system_content))
        return SystemMessage(content=system_content)

    def apply_memory_window(
        self,
        messages: list[BaseMessage],
        memory_config: MemoryConfig,
    ) -> list[BaseMessage]:
        """Truncate the message history based on the configured memory strategy.

        Args:
            messages: Full accumulated message list from WorkflowState.
            memory_config: Memory configuration for this agent.

        Returns:
            Truncated message list respecting the window size.
        """
        if memory_config.execution_memory_type == ExecutionMemoryType.EPISODIC:
            # Episodic memory: keep full history
            logger.debug("memory_episodic_full_history", count=len(messages))
            return list(messages)

        # Short-term: sliding window
        window_size = memory_config.window_size or 10
        if len(messages) <= window_size:
            return list(messages)

        windowed = list(messages[-window_size:])
        logger.debug(
            "memory_window_applied",
            original_count=len(messages),
            windowed_count=len(windowed),
            window_size=window_size,
        )
        return windowed

    def build_human_message(self, content: str, metadata: dict[str, Any] | None = None) -> HumanMessage:
        """Create a HumanMessage with optional additional metadata."""
        msg = HumanMessage(content=content)
        if metadata:
            msg.additional_kwargs.update(metadata)
        return msg

    def extract_last_ai_content(self, messages: list[BaseMessage]) -> str:
        """Return the content of the most recent AIMessage in the list."""
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and msg.content:
                return str(msg.content)
        return ""
