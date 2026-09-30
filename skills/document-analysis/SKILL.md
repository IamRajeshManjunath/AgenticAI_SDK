---
name: document-analysis
description: Analyze documents (PDF, Word, text, HTML) for insights, summaries, entity extraction, and key information. Use when you need to understand, summarize, or extract structured data from documents.
license: MIT
compatibility: Requires document loaders (PyPDF, python-docx, unstructured); LLM with large context window
metadata:
  author: AgenticAI
  version: "1.0"
  category: nlp
allowed_tools: PythonREPL, DocumentLoader
---

# Document Analysis

## Overview

This skill enables the agent to process and analyze various document formats (PDF, DOCX, TXT, HTML, Markdown) to extract insights, generate summaries, identify entities, and answer questions about document content.

## Instructions

### 1. Load Document
- Identify document format and choose appropriate loader
- Handle multi-page documents appropriately
- Extract text content and metadata (page count, author, dates)

### 2. Analyze Content
Based on the analysis type requested:

**Summary**: Generate concise summary capturing key points
**Entity Extraction**: Identify people, organizations, dates, locations, amounts
**Key Points**: Extract main arguments, decisions, action items
**Sentiment**: Assess tone and sentiment (positive/negative/neutral)
**Q&A**: Answer specific questions about document content
**Structure Analysis**: Identify headings, sections, tables, lists

### 3. Process Large Documents
For documents exceeding context window:
- Chunk document into overlapping segments
- Process each chunk independently
- Synthesize results across chunks
- Maintain cross-chunk references

### 4. Extract Structured Data
- Convert tables to structured format (JSON, CSV)
- Extract form fields and values
- Identify key-value pairs in forms

### 5. Generate Output
Format results based on use case:
- **Executive Summary**: 2-3 paragraph overview
- **Bullet Points**: Key findings with page references
- **Structured JSON**: For programmatic consumption
- **Annotated Excerpts**: Relevant passages with context

## Supported Formats
- PDF (text extraction, OCR for scanned)
- Microsoft Word (DOCX)
- Plain Text (TXT, MD)
- HTML/Web pages
- PowerPoint (PPTX)
- Spreadsheets (XLSX, CSV)

## Examples

### Example 1: Contract Review
**Input**: 50-page legal contract PDF
**Analysis**: Summary, key terms, obligations, termination clauses, liability
**Output**: Structured summary with clause references

### Example 2: Research Paper Analysis
**Input**: Academic paper (PDF)
**Analysis**: Abstract, methodology, findings, limitations, citations
**Output**: Structured summary with key contributions

### Example 3: Invoice Processing
**Input**: Invoice PDF/Image
**Analysis**: Vendor, amount, date, line items, tax, payment terms
**Output**: Structured data (JSON) for accounting system

### Example 4: Meeting Notes
**Input**: Meeting transcript or notes
**Analysis**: Decisions, action items, owners, deadlines
**Output**: Action items list with assignees and due dates