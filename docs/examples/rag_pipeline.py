"""
RAG Pipeline Example

This example demonstrates how to use the RAG (Retrieval-Augmented Generation) pipeline.
"""

import asyncio
import os
from agenticai_sdk.client import AgenticAIClient


async def main():
    client = AgenticAIClient(
        base_url=os.getenv("AGENTICAI_URL", "http://localhost:8000"),
        api_key=os.getenv("AGENTICAI_API_KEY"),
    )

    # Upload documents first
    print("Uploading documents...")
    upload_result = await client.upload_documents(
        files=[
            "docs/guide.pdf",
            "docs/api_reference.md",
        ],
        metadata={"source": "documentation", "version": "1.0"},
    )
    print(f"Uploaded {upload_result.document_count} documents")

    # Run RAG query
    print("\nRunning RAG query...")
    result = await client.run(
        workflow="rag_qa",
        input={
            "question": "How do I configure the database connection?",
            "top_k": 5,
        },
    )

    print(f"Workflow ID: {result.workflow_id}")
    print(f"Answer: {result.output.get('answer')}")
    print(f"Sources: {result.output.get('sources')}")
    print(f"Confidence: {result.output.get('confidence')}")


if __name__ == "__main__":
    asyncio.run(main())