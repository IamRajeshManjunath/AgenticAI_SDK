"""Per-agent context loader — loads agent.md and skill.md for individual agent nodes."""

from __future__ import annotations

import os
import re
from typing import Any


class AgentContextLoader:
    """Loads per-agent context from markdown files for context selection and customisation.

    Directory convention::
        agents/
            <agent_id>/
                agent.md   # Role definition, behavioural guidelines, system prompt extensions
                skill.md   # Dynamic skill rules (IF/THEN)

    Each ``agent.md`` may contain optional YAML frontmatter:
    ---
    role: "Senior Researcher"
    model_preference: "gpt-4o"
    temperature: 0.3
    ---
    Markdown body content...
    """

    def __init__(self, base_dir: str = "agents") -> None:
        self.base_dir = base_dir

    def load_agent_context(self, agent_id: str) -> dict[str, Any]:
        """Load context for a specific agent.

        Returns:
            Dict with keys 'agent_md', 'skill_md', 'frontmatter', 'body'.
        """
        result: dict[str, Any] = {
            "agent_md": None,
            "skill_md": None,
            "frontmatter": {},
            "body": "",
        }

        agent_dir = os.path.join(self.base_dir, agent_id)
        if not os.path.isdir(agent_dir):
            return result

        agent_md_path = os.path.join(agent_dir, "agent.md")
        if os.path.isfile(agent_md_path):
            try:
                with open(agent_md_path, encoding="utf-8") as f:
                    content = f.read()
                frontmatter, body = self._extract_frontmatter(content)
                result["agent_md"] = content
                result["frontmatter"] = frontmatter
                result["body"] = body
            except OSError:
                pass

        skill_md_path = os.path.join(agent_dir, "skill.md")
        if os.path.isfile(skill_md_path):
            try:
                with open(skill_md_path, encoding="utf-8") as f:
                    result["skill_md"] = f.read()
            except OSError:
                pass

        return result

    def load_all_agents(self) -> dict[str, dict[str, Any]]:
        """Load context for every agent directory found under base_dir."""
        agents: dict[str, dict[str, Any]] = {}
        if not os.path.isdir(self.base_dir):
            return agents

        for entry in sorted(os.listdir(self.base_dir)):
            if os.path.isdir(os.path.join(self.base_dir, entry)):
                ctx = self.load_agent_context(entry)
                if ctx["agent_md"] or ctx["skill_md"]:
                    agents[entry] = ctx

        return agents

    def format_agent_system_prompt_extension(self, agent_id: str, context: dict[str, Any]) -> str:
        """Format loaded context into a system prompt extension block."""
        parts: list[str] = []

        if context.get("frontmatter"):
            for key, val in context["frontmatter"].items():
                parts.append(f"{key}: {val}")

        if context.get("body"):
            parts.append(context["body"])

        if context.get("skill_md"):
            parts.append("--- Dynamic Rules ---")
            parts.append(context["skill_md"])

        return "\n".join(parts)

    @staticmethod
    def _extract_frontmatter(content: str) -> tuple[dict[str, Any], str]:
        frontmatter: dict[str, Any] = {}
        body = content

        match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)", content, re.DOTALL)
        if match:
            raw = match.group(1)
            body = match.group(2).strip()
            for line in raw.strip().splitlines():
                if ":" in line:
                    key, _, val = line.partition(":")
                    frontmatter[key.strip()] = val.strip().strip('"').strip("'")

        return frontmatter, body
