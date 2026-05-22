"""RAG pipeline for seeding and retrieving system-specific documentation and context."""

from __future__ import annotations
import os
import json
import re
from typing import Any

class MasterAgentRAG:
    """Simple, robust documentation search and retrieval system for the Master Agent."""
    
    def __init__(self, workspace_root: str | None = None):
        if workspace_root is None:
            # Resolve root directory relative to this file
            workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.workspace_root = workspace_root
        self.documents: list[dict[str, Any]] = []
        self._load_and_seed()

    def _load_and_seed(self):
        """Seed the RAG pipeline with system-specific documentation."""
        paths = [
            ("master_schema_reference.json", "System JSON Schema Reference"),
            ("README.md", "System Overview & SDK Documentation"),
            ("implementation_plan.md", "System Implementation Plan"),
        ]
        
        for rel_path, doc_type in paths:
            abs_path = os.path.join(self.workspace_root, rel_path)
            if os.path.exists(abs_path):
                try:
                    with open(abs_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        
                    # Chunk by headers or structure
                    if rel_path.endswith(".json"):
                        # Parse and chunk JSON schema
                        data = json.loads(content)
                        self.documents.append({
                            "title": doc_type,
                            "source": rel_path,
                            "content": json.dumps(data, indent=2),
                            "keywords": ["schema", "json", "reference", "nodes", "edges", "config"]
                        })
                    else:
                        # Markdown chunking by headers
                        chunks = re.split(r"(^#+\s+.*)", content, flags=re.MULTILINE)
                        current_header = "Intro"
                        for chunk in chunks:
                            chunk = chunk.strip()
                            if not chunk:
                                continue
                            if chunk.startswith("#"):
                                current_header = chunk.strip("#").strip()
                            else:
                                self.documents.append({
                                    "title": f"{doc_type} - {current_header}",
                                    "source": rel_path,
                                    "content": chunk,
                                    "keywords": [w.lower() for w in re.findall(r"\w+", current_header + " " + chunk[:100]) if len(w) > 3]
                                })
                except Exception as e:
                    print(f"Error seeding document {rel_path}: {e}")

    def retrieve(self, query: str, top_k: int = 3) -> list[dict[str, Any]]:
        """Retrieve most relevant documentation chunks based on keyword matching."""
        query_words = [w.lower() for w in re.findall(r"\w+", query) if len(w) > 3]
        if not query_words:
            return self.documents[:top_k]
            
        scored_docs = []
        for doc in self.documents:
            score = 0
            doc_content_lower = doc["content"].lower()
            # Score based on exact match of query words
            for word in query_words:
                if word in doc_content_lower:
                    score += 2
                if word in doc["title"].lower():
                    score += 5
                for kw in doc.get("keywords", []):
                    if word == kw:
                        score += 3
            if score > 0:
                scored_docs.append((score, doc))
                
        # Sort by score descending
        scored_docs.sort(key=lambda x: x[0], reverse=True)
        retrieved = [doc for _, doc in scored_docs[:top_k]]
        
        # Fallback if no matching docs found
        if not retrieved:
            retrieved = self.documents[:top_k]
            
        return retrieved
