"""
Skills Pipeline Example

This example demonstrates how to create and run a custom skills pipeline.
"""

import asyncio
import os
from agenticai_sdk.client import AgenticAIClient
from agenticai_sdk.skills import SkillPipeline, SkillContext


async def main():
    client = AgenticAIClient(
        base_url=os.getenv("AGENTICAI_URL", "http://localhost:8000"),
        api_key=os.getenv("AGENTICAI_API_KEY"),
    )

    # Create a custom pipeline
    pipeline = SkillPipeline(name="research_report")
    search_id = pipeline.add_step("web-research", params={"query": "AI agents 2024 trends"})
    analyze_id = pipeline.add_step("document-analysis", params={"analysis_type": "summary"}, dependencies=[search_id])
    reason_id = pipeline.add_step("reasoning", params={"reasoning_type": "chain_of_thought"}, dependencies=[analyze_id])

    # Register pipeline
    await client.register_pipeline(pipeline)

    # Execute pipeline
    print("Executing research pipeline...")
    context = SkillContext(workspace_id="ws_1", user_id="user_1")
    execution = await client.execute_pipeline("research_report", context)

    print(f"Pipeline execution ID: {execution.pipeline_id}")
    print(f"Status: {execution.status}")

    for step_id, step_result in execution.step_results.items():
        print(f"  Step {step_id}: {step_result.status}")
        if step_result.result:
            print(f"    Output: {step_result.result.data}")


if __name__ == "__main__":
    asyncio.run(main())