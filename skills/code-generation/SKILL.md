---
name: code-generation
description: Generate code from specifications, requirements, or natural language descriptions. Use for creating new code, refactoring, writing tests, or implementing algorithms.
license: MIT
compatibility: Requires E2B sandbox for execution testing; works with any LLM that supports code generation
metadata:
  author: AgenticAI
  version: "1.0"
  category: development
allowed_tools: E2BSandbox, PythonREPL
---

# Code Generation

## Overview

This skill enables the agent to generate, refactor, and test code based on natural language specifications. It supports multiple programming languages and can execute code in a secure sandbox for validation.

## Instructions

### 1. Analyze Requirements
- Understand the problem domain and constraints
- Identify the target language, framework, and libraries
- Clarify inputs, outputs, and edge cases
- Determine performance requirements

### 2. Design Solution
- Break down the problem into components
- Choose appropriate algorithms and data structures
- Plan the code structure (functions, classes, modules)
- Consider error handling and validation

### 3. Generate Code
Write clean, well-documented code following best practices:
- Use meaningful variable and function names
- Add type hints (Python) or type annotations (TypeScript)
- Include docstrings and comments
- Follow language-specific style guides (PEP 8, etc.)

### 4. Test and Validate
- Write unit tests for critical functionality
- Execute in sandbox to verify correctness
- Test edge cases and error conditions
- Profile performance if needed

### 5. Refactor and Optimize
- Improve code clarity and maintainability
- Optimize performance bottlenecks
- Ensure proper error handling
- Add logging and monitoring hooks

## Supported Languages
- Python (primary)
- JavaScript/TypeScript
- SQL
- Bash/Shell
- Dockerfile
- YAML/JSON configuration

## Code Templates
Reference templates are available in `templates/`:
- `python_function.py` - Standard function template
- `python_class.py` - Class with common patterns
- `async_function.py` - Async/await patterns
- `test_template.py` - Pytest structure
- `api_endpoint.py` - FastAPI/Flask endpoint

## Examples

### Example 1: Data Processing Function
**Request**: "Write a Python function that reads a CSV, filters rows where status='active', groups by category, and returns sum of amount per category"
**Output**: Complete function with pandas, type hints, docstring, and error handling

### Example 2: REST API Endpoint
**Request**: "Create a FastAPI endpoint that accepts JSON, validates with Pydantic, calls a service, and returns standardized response"
**Output**: Complete endpoint with request/response models, validation, error handling

### Example 3: Algorithm Implementation
**Request**: "Implement Dijkstra's shortest path algorithm for a weighted graph"
**Output**: Complete implementation with priority queue, type hints, and tests