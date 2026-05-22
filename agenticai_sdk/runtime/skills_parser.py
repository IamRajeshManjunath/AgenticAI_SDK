import os
import re
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger("agenticai_sdk.skills_parser")

class SkillsParser:
    """Markdown AST parser extracting executable rules and sub-graphs from SKILLS.md.
    
    Enables dynamic, code-free behavior mutations for runtime agent instances.
    """
    
    @classmethod
    def parse_file(cls, filepath: str) -> Dict[str, Any]:
        if not os.path.exists(filepath):
            return {}
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            return cls.parse_content(content)
        except Exception as e:
            logger.error(f"Failed to parse SKILLS.md: {e}", exc_info=True)
            return {}

    @classmethod
    def parse_content(cls, content: str) -> Dict[str, Any]:
        skills = {
            "context_rules": [],
            "situational_boundaries": {},
            "sub_graph_modifications": {}
        }
        
        current_section = None
        
        # Parse line by line to support a simple Markdown AST extraction
        for line in content.splitlines():
            line_str = line.strip()
            if not line_str:
                continue
                
            # Detect sections
            if line_str.startswith("## "):
                section_title = line_str[3:].lower().strip()
                if "context rules" in section_title:
                    current_section = "context_rules"
                elif "situational boundaries" in section_title:
                    current_section = "situational_boundaries"
                elif "execution sub-graph" in section_title or "sub-graph" in section_title:
                    current_section = "sub_graph"
                else:
                    current_section = None
                continue

            if not current_section:
                continue

            # Process list items under sections
            if line_str.startswith("- ") or line_str.startswith("* "):
                item = line_str[2:].strip()
                
                if current_section == "context_rules":
                    # IF field CONTAINS value THEN param = val
                    rule_match = re.match(
                        r"(?i)IF\s+(\w+)\s+(CONTAINS|EQUALS|==)\s+[\"'](.*?)[\"']\s+THEN\s+(\w+(?:\.\w+)*)\s*=\s*(.*?)$",
                        item
                    )
                    if rule_match:
                        field, op, criteria, param, val = rule_match.groups()
                        val = cls._parse_value(val)
                        skills["context_rules"].append({
                            "field": field,
                            "operator": op.upper(),
                            "criteria": criteria,
                            "param": param,
                            "value": val
                        })
                        
                elif current_section == "situational_boundaries":
                    # PARAM = val WHEN field = val
                    boundary_match = re.match(
                        r"(?i)(\w+)\s*=\s*(.*?)\s+WHEN\s+(\w+)\s*(?:=|==)\s*[\"'](.*?)[\"']$",
                        item
                    )
                    if boundary_match:
                        param, val, field, criteria = boundary_match.groups()
                        val = cls._parse_value(val)
                        if param not in skills["situational_boundaries"]:
                            skills["situational_boundaries"][param] = []
                        skills["situational_boundaries"][param].append({
                            "value": val,
                            "field": field,
                            "criteria": criteria
                        })
                        
                elif current_section == "sub_graph":
                    # ENTRY_POINT = "node_id" or node1 -> node2 IF cond
                    entry_match = re.match(r"(?i)ENTRY_POINT\s*=\s*[\"'](.*?)[\"']", item)
                    if entry_match:
                        skills["sub_graph_modifications"]["entry_point"] = entry_match.group(1)
                    else:
                        edge_match = re.match(
                            r"(\w+)\s*->\s*(\w+)(?:\s+IF\s+(.*?))?$",
                            item
                        )
                        if edge_match:
                            source, target, cond = edge_match.groups()
                            if "edges" not in skills["sub_graph_modifications"]:
                                skills["sub_graph_modifications"]["edges"] = []
                            skills["sub_graph_modifications"]["edges"].append({
                                "source": source,
                                "target": target,
                                "condition": cond
                            })

        return skills

    @staticmethod
    def _parse_value(val: str) -> Any:
        val = val.strip().strip("'\"")
        if val.lower() == "true":
            return True
        if val.lower() == "false":
            return False
        if val.lower() == "none" or val.lower() == "null":
            return None
        try:
            if "." in val:
                return float(val)
            return int(val)
        except ValueError:
            return val

    @classmethod
    def apply_skills_to_agent_config(
        cls, agent_id: str, skills: Dict[str, Any], state: Dict[str, Any], agent_config: Any
    ) -> Any:
        """Dynamically hot-swaps active agent config properties based on parsed rule bindings and state."""
        prompt_vars = state.get("scratchpad", {})
        last_message_content = ""
        if state.get("messages"):
            last_message_content = str(state["messages"][-1].content) if hasattr(state["messages"][-1], "content") else str(state["messages"][-1])

        # Evaluate Context Rules
        for rule in skills.get("context_rules", []):
            field = rule["field"]
            val_to_check = prompt_vars.get(field, "") or (last_message_content if field.lower() == "topic" or field.lower() == "prompt" else "")
            
            triggered = False
            if rule["operator"] == "CONTAINS" and rule["criteria"].lower() in str(val_to_check).lower():
                triggered = True
            elif rule["operator"] in ("EQUALS", "==") and str(val_to_check).lower() == rule["criteria"].lower():
                triggered = True
                
            if triggered:
                cls._set_nested_config(agent_config, rule["param"], rule["value"])
                logger.info(f"Dynamic skill trigger applied: {rule['param']} set to {rule['value']}")

        # Evaluate Situational Boundaries
        for param, rules in skills.get("situational_boundaries", {}).items():
            for rule in rules:
                field = rule["field"]
                val_to_check = prompt_vars.get(field, "") or (last_message_content if field.lower() == "topic" or field.lower() == "prompt" else "")
                if rule["criteria"].lower() in str(val_to_check).lower():
                    cls._set_nested_config(agent_config, param, rule["value"])
                    logger.info(f"Dynamic boundary trigger applied: {param} set to {rule['value']} due to {field}")

        return agent_config

    @staticmethod
    def _set_nested_config(config_obj: Any, path: str, value: Any):
        """Sets nested properties (e.g. 'middleware_config.budget.max_loop_iterations') using attribute inspection."""
        parts = path.split(".")
        current = config_obj
        for part in parts[:-1]:
            if hasattr(current, part):
                current = getattr(current, part)
            elif isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return # Path not matching config structure
                
        last_part = parts[-1]
        if hasattr(current, last_part):
            setattr(current, last_part, value)
        elif isinstance(current, dict):
            current[last_part] = value
