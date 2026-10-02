"""
Basic AgenticAI Workflow Example

This example demonstrates how to run a simple workflow using the AgenticAI SDK.
"""

import asyncio
import os
from agenticai_sdk.client import AgenticAIClient


async def main():
    # Initialize client
    client = AgenticAIClient(
        base_url=os.getenv("AGENTICAI_URL", "http://localhost:8000"),
        api_key=os.getenv("AGENTICAI_API_KEY"),
    )

    # Run a simple workflow
    result = await client.run(
        workflow="basic_qa",
        input={"question": "What is the capital of France?"},
    )

    print(f"Workflow ID: {result.workflow_id}")
    print(f"Status: {result.status}")
    print(f"Output: {result.output}")


if __name__ == "__main__":
    asyncio.run(main())