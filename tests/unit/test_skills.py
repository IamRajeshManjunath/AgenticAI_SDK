"""Tests for the Skills system."""

import pytest
from agenticai_sdk.skills import (
    SkillMetadata,
    SkillParameter,
    SkillResult,
    SkillType,
    SkillsRegistry,
    get_skills_registry,
    SkillContext,
    SkillPipeline,
    PipelineStep,
    SkillComposer,
    PIPELINE_TEMPLATES,
    get_pipeline_template,
    list_pipeline_templates,
)


class TestSkillBase:
    """Test base skill classes."""

    def test_skill_metadata_creation(self):
        """Test SkillMetadata creation."""
        metadata = SkillMetadata(
            name="test_skill",
            description="A test skill",
            type=SkillType.SEARCH,
            modified_at=datetime.utcnow(),
        )
        assert metadata.name == "test_skill"
        assert metadata.type == SkillType.SEARCH

    def test_skill_parameter_validation(self):
        """Test SkillParameter validation."""
        param = SkillParameter(
            name="count",
            type="number",
            description="Count",
            required=True,
            default=10,
        )
        assert param.type == "number"
        assert param.default == 10

    def test_skill_result(self):
        """Test SkillResult."""
        result = SkillResult(
            success=True,
            data={"key": "value"},
            metadata={"provider": "test"},
            tokens_used=100,
            cost=0.001,
        )
        assert result.success is True
        assert result.data["key"] == "value"
        assert result.tokens_used == 100

    def test_skill_context(self):
        """Test SkillContext."""
        context = SkillContext(
            workspace_id="ws_1",
            user_id="user_1",
            agent_id="agent_1",
            credentials={"openai": "sk-..."},
            config={"model": "gpt-4o"},
        )
        assert context.workspace_id == "ws_1"
        assert context.credentials["openai"] == "sk-..."


class TestSkillRegistry:
    """Test SkillRegistry."""

    def test_registry_creation(self):
        """Test registry creation."""
        registry = SkillsRegistry()
        assert registry is not None
        assert len(registry._skills) == 0

    def test_register_builtin_skills(self):
        """Test registering all builtin skills."""
        registry = SkillsRegistry()
        registry.initialize()
        
        assert len(registry._skills) == 7
        expected_skills = [
            "web_search",
            "code_execution",
            "document_analysis",
            "data_processing",
            "api_integration",
            "reasoning",
            "planning",
        ]
        for skill_name in expected_skills:
            assert skill_name in registry._skills


class TestSkillPipeline:
    """Test SkillPipeline."""

    def test_pipeline_creation(self):
        """Test pipeline creation."""
        pipeline = SkillPipeline(name="test_pipeline", description="Test")
        assert pipeline.name == "test_pipeline"

    def test_add_step(self):
        """Test adding steps."""
        pipeline = SkillPipeline(name="test")
        step_id = pipeline.add_step(
            skill_name="web_search",
            params={"query": "test"},
        )
        assert len(pipeline.steps) == 1
        assert pipeline.steps[0].id == step_id
        assert pipeline.steps[0].skill_name == "web_search"

    def test_pipeline_validation(self):
        """Test pipeline validation."""
        pipeline = SkillPipeline(name="test")
        step1_id = pipeline.add_step("web_search")
        step2_id = pipeline.add_step("code_execution", dependencies=[step1_id])

        valid, errors = pipeline.validate()
        assert valid is True
        assert len(errors) == 0

    def test_pipeline_cycle_detection(self):
        """Test cycle detection."""
        pipeline = SkillPipeline(name="test")
        step1_id = pipeline.add_step("web_search")
        step2_id = pipeline.add_step("code_execution", dependencies=[step1_id])

        # Manually create a cycle by modifying dependencies
        step1 = pipeline.get_step(step1_id)
        step1.dependencies = [step2_id]

        valid, errors = pipeline.validate()
        assert valid is False
        assert any("circular" in e.lower() for e in errors)


class TestSkillComposer:
    """Test SkillComposer."""

    def test_composer_creation(self):
        """Test composer creation."""
        registry = SkillsRegistry()
        registry.initialize()
        composer = SkillComposer(registry)
        assert composer is not None

    def test_register_pipeline(self):
        """Test pipeline registration."""
        registry = SkillsRegistry()
        registry.initialize()
        composer = SkillComposer(registry)

        pipeline = SkillPipeline(name="test_pipeline")
        pipeline.add_step("web_search")
        composer.register_pipeline(pipeline)

        assert "test_pipeline" in composer._pipelines

    def test_get_pipeline_template(self):
        """Test getting pipeline templates."""
        template = get_pipeline_template("rag_qa")
        assert template is not None
        assert template["name"] == "rag_qa"
        assert len(template["steps"]) == 3

    def test_list_pipeline_templates(self):
        """Test listing pipeline templates."""
        templates = list_pipeline_templates()
        assert "rag_qa" in templates
        assert "research_report" in templates
        assert "data_analysis" in templates


class TestPipelineExecution:
    """Test pipeline execution (mocked)."""

    @pytest.mark.asyncio
    async def test_simple_pipeline_execution(self):
        """Test executing a simple pipeline."""
        registry = SkillsRegistry()
        registry.initialize()
        composer = SkillComposer(registry)

        pipeline = SkillPipeline(name="simple")
        search_id = pipeline.add_step("web_search", params={"query": "test"})
        reason_id = pipeline.add_step("reasoning", params={"problem": "analyze"}, dependencies=[search_id])
        composer.register_pipeline(pipeline)

        context = SkillContext(workspace_id="ws_1", user_id="user_1")
        execution = await composer.execute_pipeline("simple", context)

        assert execution.status == "completed"
        assert search_id in execution.step_results
        assert reason_id in execution.step_results
        assert execution.step_results[search_id].status == "completed"
        assert execution.step_results[reason_id].status == "completed"

    @pytest.mark.asyncio
    async def test_pipeline_with_failed_step(self):
        """Test pipeline with a failing step."""
        registry = SkillsRegistry()
        registry.initialize()

        # Create a skill that always fails
        class FailingSkill:
            def _get_metadata(self):
                from agenticai_sdk.skills import SkillMetadata, SkillType
                return SkillMetadata(
                    name="failing",
                    display_name="Failing",
                    description="Always fails",
                    type=SkillType.CUSTOM,
                )

            async def execute(self, context, **params):
                return SkillResult(success=False, error="Intentional failure")

        registry.register_skill(FailingSkill)

        composer = SkillComposer(registry)

        pipeline = SkillPipeline(name="fail_test")
        fail_step_id = pipeline.add_step("failing")
        composer.register_pipeline(pipeline)

        context = SkillContext(workspace_id="ws_1", user_id="user_1")
        execution = await composer.execute_pipeline("fail_test", context)

        assert execution.status == "failed"
        assert execution.step_results[fail_step_id].status == "failed"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])