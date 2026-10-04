# Per-Agent JSON Schema Contracts

Each workflow agent may optionally define `input_schema` and `output_schema` on its `AgentNodeConfig`. Both values must be valid JSON Schema documents using Draft 2020-12. These schemas are stored as part of the workflow definition and are optional; agents without them retain existing behavior.

## Input contract

Before invoking an agent with an `input_schema`, the runtime validates this JSON object:

```json
{
  "input_message": "The most recent human message",
  "scratchpad": {},
  "retrieved_context": []
}
```

`input_message` is the latest human message content. `scratchpad` and `retrieved_context` are the current workflow values. The schema applies to this JSON-safe envelope, not the full LangGraph state or framework message objects.

## Output contract

When an agent has an `output_schema`, the runtime selects its final assistant response (ignoring intermediate tool-call messages), parses the response content as JSON, and validates the parsed value against the schema. Non-JSON output, missing final assistant content, or a schema mismatch fails that agent step; the runtime does not repair or silently coerce the response.

This is runtime validation, not provider-native constrained decoding. The model is not guaranteed to produce conforming JSON, so use prompt instructions and provider features as appropriate, while treating runtime validation as the enforcement boundary.

## Audit behavior

Validation passes and failures are written to `schema_audit_trails` with agent, workflow, and workspace identifiers. To avoid storing sensitive prompt/context/response values in a second copy, the audit payload stores a SHA-256 fingerprint and top-level key names rather than the raw value. The configured schema and validation outcome/error are retained. Existing unscoped audit rows remain with null workspace/workflow identifiers after migration `002`.
