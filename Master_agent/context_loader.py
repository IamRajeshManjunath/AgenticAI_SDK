"""Context loader — scans markdown files to enrich Master Agent context."""

from __future__ import annotations

import os
import re
from typing import Any


class AgentContextLoader:
    """Scans a configured directory for agent.md and skill.md files
    and returns structured context blocks for Master Agent prompt injection."""

    def __init__(self, agents_dir: str = "agents") -> None:
        self.agents_dir = agents_dir

    def load_all_contexts(self) -> list[dict[str, Any]]:
        """Scan agents/ subdirectories and load all agent.md and skill.md files."""
        contexts: list[dict[str, Any]] = []
        if not os.path.isdir(self.agents_dir):
            return contexts

        for entry in sorted(os.listdir(self.agents_dir)):
            agent_path = os.path.join(self.agents_dir, entry)
            if not os.path.isdir(agent_path):
                continue

            agent_md_path = os.path.join(agent_path, "agent.md")
            skill_md_path = os.path.join(agent_path, "skill.md")

            if os.path.isfile(agent_md_path):
                try:
                    with open(agent_md_path, encoding="utf-8") as f:
                        contexts.append({
                            "agent_id": entry,
                            "type": "agent.md",
                            "content": f.read(),
                            "source": agent_md_path,
                        })
                except OSError:
                    pass

            if os.path.isfile(skill_md_path):
                try:
                    with open(skill_md_path, encoding="utf-8") as f:
                        contexts.append({
                            "agent_id": entry,
                            "type": "skill.md",
                            "content": f.read(),
                            "source": skill_md_path,
                        })
                except OSError:
                    pass

        return contexts

    def format_context_block(self, contexts: list[dict[str, Any]]) -> str:
        """Format loaded contexts into a single structured prompt block."""
        if not contexts:
            return ""

        lines: list[str] = ["=== Agent Context Files ===", ""]
        for ctx in contexts:
            lines.append(f"[{ctx['agent_id']}/{ctx['type']}]")
            lines.append(ctx["content"])
            lines.append("")
        lines.append("=== End Agent Context ===")
        return "\n".join(lines)

    @staticmethod
    def extract_yaml_frontmatter(content: str) -> tuple[dict[str, Any], str]:
        """Extract YAML-like frontmatter from markdown content."""
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
