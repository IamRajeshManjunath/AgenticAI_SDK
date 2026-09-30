---
name: web-research
description: Search the web for current information and synthesize findings. Use when you need up-to-date information, fact-checking, or gathering sources for a topic.
license: MIT
compatibility: Requires Tavily integration (tavily API key)
metadata:
  author: AgenticAI
  version: "1.0"
  category: search
allowed_tools: TavilySearch
---

# Web Research

## Overview

This skill enables the agent to search the web for current information, gather multiple sources, and synthesize findings into a coherent answer. It uses the Tavily search API to perform AI-powered web searches.

## Instructions

### 1. Analyze the Request
- Identify what information is needed
- Determine the type of search required (general, news, academic, etc.)
- Extract key terms and concepts for the search query

### 2. Execute Search
Use the Tavily search tool with appropriate parameters:
- `query`: The search query (be specific and use relevant keywords)
- `max_results`: Number of results to return (default: 5, max: 20)
- `search_depth`: "basic" for quick results, "advanced" for comprehensive research
- `include_domains`: Optional list of domains to restrict search
- `exclude_domains`: Optional list of domains to exclude

### 3. Evaluate Sources
- Check credibility of sources (reputable domains, recent dates)
- Cross-reference information across multiple sources
- Note any conflicting information

### 4. Synthesize Findings
- Organize findings by theme or subtopic
- Provide citations with URLs
- Highlight key insights and actionable information
- Note any limitations or gaps in available information

### 5. Format Output
Structure the response with:
- **Summary**: Brief overview of findings
- **Key Findings**: Organized by subtopic with citations
- **Sources**: List of all sources with URLs and credibility notes
- **Confidence**: Assessment of reliability (High/Medium/Low)

## Examples

### Example 1: Technology Research
**Query**: "Latest developments in quantum computing 2024"
**Parameters**: max_results=10, search_depth="advanced"

### Example 2: Fact Checking
**Query**: "Did company X announce product Y in January 2024"
**Parameters**: max_results=5, search_depth="basic"

### Example 3: Market Research
**Query**: "Market size for AI agents 2024 2025 forecast"
**Parameters**: max_results=8, search_depth="advanced"