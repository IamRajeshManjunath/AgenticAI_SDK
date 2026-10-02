"""
Human-in-the-Loop (HITL) Example

This example demonstrates how to use the HITL approval workflow.
"""

import asyncio
import os
from agenticai_sdk.client import AgenticAIClient


async def main():
    client = AgenticAIClient(
        base_url=os.getenv("AGENTICAI_URL", "http://localhost:8000"),
        api_key=os.getenv("AGENTICAI_API_KEY"),
    )

    # Run a workflow that requires human approval
    print("Starting workflow with HITL...")
    result = await client.run(
        workflow="code_review",
        input={
            "code": "def hello():\n    print('Hello, World!')",
            "language": "python",
        },
    )

    print(f"Workflow ID: {result.workflow_id}")
    print(f"Status: {result.status}")

    if result.status == "awaiting_approval":
        print(f"Approval required: {result.approval_request}")
        print(f"Approval ID: {result.approval_id}")

        # Simulate human approval
        print("\nApproving...")
        approval_result = await client.approve(
            approval_id=result.approval_id,
            approved=True,
            feedback="Code looks good, approved.",
        )

        print(f"Approval result: {approval_result}")

        # Get final result
        final_result = await client.get_run(result.workflow_id)
        print(f"Final status: {final_result.status}")
        print(f"Final output: {final_result.output}")


if __name__ == "__main__":
    asyncio.run(main())