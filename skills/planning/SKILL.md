---
name: planning
description: Create detailed execution plans for complex tasks. Decompose goals into actionable steps, identify dependencies, estimate resources, and define success criteria.
license: MIT
compatibility: Requires LLM with planning capabilities; integrates with task management tools
metadata:
  author: AgenticAI
  version: "1.0"
  category: planning
allowed_tools: PythonREPL, TaskManager
---

# Planning

## Overview

This skill enables the agent to create detailed, executable plans for complex tasks and projects. It decomposes high-level goals into actionable steps with dependencies, resource estimates, and success criteria.

## Instructions

### 1. Understand the Goal
- Clarify the objective and desired outcome
- Identify constraints (time, budget, resources, technology)
- Define success criteria and acceptance criteria
- Identify stakeholders and their requirements

### 2. Decompose into Tasks
Break the goal into manageable work units:
- **Hierarchical Decomposition**: Epics -> Stories -> Tasks
- **Dependency Mapping**: Identify task dependencies and critical path
- **Parallelization**: Identify tasks that can run concurrently
- **Milestone Definition**: Key checkpoints and deliverables

### 3. Estimate Resources
For each task, estimate:
- **Time**: Hours/days for completion
- **Skills Required**: Required expertise/roles
- **Tools/Infrastructure**: Needed environments, APIs, data
- **Budget**: Cost estimates if applicable

### 4. Risk Assessment
- Identify technical, schedule, and resource risks
- Assess probability and impact
- Define mitigation strategies
- Define contingency plans

### 5. Create Execution Plan
Structure the plan with:
- **Phases/Milestones**: High-level timeline
- **Task List**: Detailed tasks with owners, estimates, dependencies
- **Gantt Chart / Timeline**: Visual schedule
- **Resource Allocation**: Who does what, when
- **Success Metrics**: How to measure progress and completion

### 6. Review and Refine
- Validate with stakeholders
- Adjust based on feedback
- Establish change control process
- Define communication cadence

## Planning Templates

Reference templates in `templates/`:
- `project_plan.md` - Full project plan structure
- `sprint_plan.md` - Agile sprint planning
- `task_breakdown.md` - Task decomposition worksheet
- `risk_register.md` - Risk assessment template

## Examples

### Example 1: Feature Development
**Goal**: "Add user authentication to web app"
**Plan**: Phase 1: Design (2 days), Phase 2: Backend API (5 days), Phase 3: Frontend (3 days), Phase 4: Testing (2 days), Phase 5: Deploy (1 day)
**Dependencies**: Frontend depends on Backend API contract

### Example 2: Data Migration
**Goal**: "Migrate 10M records from PostgreSQL to Snowflake"
**Plan**: Phase 1: Schema mapping (1 day), Phase 2: ETL pipeline (3 days), Phase 3: Validation (2 days), Phase 4: Cutover (1 day)
**Risks**: Data loss, downtime, schema mismatch

### Example 3: Research Project
**Goal**: "Evaluate vector databases for RAG system"
**Plan**: Phase 1: Requirements (1 day), Phase 2: Shortlist (2 days), Phase 3: Benchmarking (5 days), Phase 4: Report (2 days)
**Milestones**: Shortlist complete, Benchmarks done, Recommendation delivered