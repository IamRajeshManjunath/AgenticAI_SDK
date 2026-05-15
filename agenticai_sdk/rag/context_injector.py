"""
ContextInjector — utility for formatting retrieved vector documents into
structured text blocks for inclusion in agent prompts.
"""

from __future__ import annotations

from langchain_core.documents import Document


class ContextInjector:
    """Formats retrieved documents into structured context blocks for prompt injection.

    Usage::

        injector = ContextInjector()
        context_text = injector.format_documents(documents)
        # Produces: "[Source: doc_title] Content..."
    """

    SECTION_HEADER = "=== Retrieved Knowledge Context ==="
    SECTION_FOOTER = "=== End Knowledge Context ==="

    @staticmethod
    def format_documents(
        documents: list[Document],
        *,
        max_chars_per_doc: int = 2000,
        include_scores: bool = True,
    ) -> str:
        """Format a list of LangChain Documents into a structured text block.

        Args:
            documents: Retrieved documents to format.
            max_chars_per_doc: Maximum characters to include per document.
            include_scores: Whether to include similarity scores in the output.

        Returns:
            A formatted string block ready for prompt injection.
        """
        if not documents:
            return ""

        lines: list[str] = [ContextInjector.SECTION_HEADER, ""]

        for idx, doc in enumerate(documents, start=1):
            source = doc.metadata.get("source", doc.metadata.get("title", f"Document {idx}"))
            score = doc.metadata.get("similarity_score")
            content = doc.page_content[:max_chars_per_doc]

            header = f"[Source: {source}]"
            if include_scores and score is not None:
                header += f" (relevance: {score:.3f})"

            lines.append(header)
            lines.append(content)
            lines.append("")  # blank separator

        lines.append(ContextInjector.SECTION_FOOTER)
        return "\n".join(lines)

    @staticmethod
    def format_as_dicts(documents: list[Document]) -> list[dict]:
        """Convert documents to serializable dicts for state storage.

        Args:
            documents: Retrieved documents.

        Returns:
            List of dicts with 'content', 'source', and 'score' keys.
        """
        return [
            {
                "content": doc.page_content,
                "source": doc.metadata.get("source", "unknown"),
                "score": doc.metadata.get("similarity_score", 0.0),
                "metadata": {k: v for k, v in doc.metadata.items() if k != "similarity_score"},
            }
            for doc in documents
        ]
