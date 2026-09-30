---
name: reasoning
description: Perform multi-step reasoning, chain-of-thought, tree-of-thought, and reflexion for complex problem solving. Use when a task requires deep analysis, logical deduction, or step-by-step thinking.
license: MIT
compatibility: Requires LLM with strong reasoning capabilities (GPT-4, Claude-3.5, etc.)
metadata:
  author: AgenticAI
  version: "1.0"
  category: reasoning
allowed_tools: PythonREPL
---

# Reasoning

## Overview

This skill enables the agent to perform structured, multi-step reasoning for complex problems. It supports various reasoning patterns including chain-of-thought, tree-of-thought, reflexion, and self-consistency.

## Instructions

### 1. Understand the Problem
- Clearly define the problem and goal
- Identify known facts, constraints, and unknowns
- Break down into sub-problems if needed
- Determine the type of reasoning required

### 2. Choose Reasoning Strategy
Select the appropriate approach:

**Chain-of-Thought (CoT)**: Step-by-step reasoning for linear problems
**Tree-of-Thought (ToT)**: Explore multiple reasoning branches, backtrack if needed
**Reflexion**: Iterate on solutions with self-critique
**Self-Consistency**: Generate multiple reasoning paths, take majority
**Program-Aided**: Use code execution for verification

### 3. Execute Reasoning
For each step:
- State the current understanding
- Apply logical inference
- Verify intermediate conclusions
- Track confidence levels
- Note assumptions and uncertainties

### 4. Validate Conclusions
- Check for logical consistency
- Verify against known facts
- Test edge cases
- Consider alternative explanations
- Quantify confidence

### 5. Present Results
Structure the output:
- **Problem Statement**: Clear restatement
- **Reasoning Trace**: Step-by-step logic
- **Key Insights**: Critical findings
- **Conclusion**: Final answer with confidence
- **Limitations**: Known uncertainties

## Reasoning Patterns

### Chain-of-Thought
Linear step-by-step reasoning for straightforward problems.

### Tree-of-Thought
Explore multiple paths, evaluate, and backtrack when needed.

### Reflexion
Generate solution, critique it, refine, repeat until satisfied.

### Self-Consistency
Generate N independent reasoning paths, take majority vote.

## Examples

### Example 1: Mathematical Problem
**Problem**: "If a train travels 60 mph for 2 hours, then 80 mph for 1.5 hours, what's the average speed?"
**CoT**: Calculate total distance, total time, then divide

### Example 2: Debugging Code
**Problem**: "Function returns wrong result for edge case"
**ToT**: Explore multiple hypotheses (off-by-one, type issue, logic error), test each

### Example 3: Strategic Decision
**Problem**: "Should we build or buy this component?"
**Reflexion**: List pros/cons, critique each, refine based on constraints

### Example 4: Logical Puzzle
**Problem**: "Three people, two always lie, one tells truth..."
**ToT**: Explore truth assignments, eliminate contradictions