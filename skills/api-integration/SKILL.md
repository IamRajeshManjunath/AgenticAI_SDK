---
name: api-integration
description: Connect to and interact with external REST APIs, GraphQL endpoints, and web services. Handles authentication, rate limiting, error handling, and data transformation.
license: MIT
compatibility: Requires httpx/requests; OAuth2/client credentials for auth
metadata:
  author: AgenticAI
  version: "1.0"
  category: integration
allowed_tools: HTTPRequest, PythonREPL
---

# API Integration

## Overview

This skill enables the agent to connect to and interact with external APIs including REST, GraphQL, and SOAP services. It handles authentication, request/response handling, rate limiting, and data transformation.

## Instructions

### 1. Analyze API Documentation
- Identify base URL, endpoints, authentication method
- Review rate limits, pagination, error codes
- Understand request/response schemas
- Note required headers and parameters

### 2. Configure Authentication
Support multiple auth types:
- **API Key**: Header or query parameter
- **Bearer Token**: JWT/OAuth2 access token
- **Basic Auth**: Username/password
- **OAuth2**: Client credentials, authorization code, refresh tokens
- **Custom**: Signature-based (AWS, etc.)

### 3. Build Requests
- Construct URL with path parameters and query strings
- Set appropriate headers (Content-Type, Accept, Auth)
- Build request body (JSON, form-data, multipart)
- Handle pagination (cursor, offset, link headers)

### 4. Execute with Resilience
- Implement retry with exponential backoff
- Handle rate limits (429) with backoff
- Circuit breaker for repeated failures
- Timeout configuration (connect, read, total)

### 5. Process Responses
- Validate status codes
- Parse JSON/XML/other formats
- Handle pagination (follow next links)
- Transform to standardized format
- Extract relevant fields

### 6. Error Handling
- Map HTTP errors to meaningful exceptions
- Log request/response for debugging
- Implement fallback strategies
- Alert on critical failures

## Supported Patterns
- REST (GET, POST, PUT, PATCH, DELETE)
- GraphQL (queries, mutations, subscriptions)
- Webhooks (receive and verify)
- Server-Sent Events (SSE)
- gRPC (via HTTP/2)

## Examples

### Example 1: GitHub API
**Task**: List repos for organization, get commit stats
**Auth**: Bearer token
**Endpoints**: GET /orgs/{org}/repos, GET /repos/{owner}/{repo}/stats/commit_activity

### Example 2: Payment Gateway
**Task**: Create payment intent, handle webhook
**Auth**: Secret key
**Endpoints**: POST /payment_intents, POST /webhooks

### Example 3: Data Sync
**Task**: Pull data from CRM, transform, push to warehouse
**Auth**: OAuth2 client credentials
**Flow**: Paginated GET -> Transform -> Batch POST