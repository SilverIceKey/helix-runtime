# MCP Server Integration Spec (Claude Code First, Multi-Client Compatible)

## 1. Overview
This MCP server is designed for:
- Claude Code local integration (primary)
- Generic MCP clients
- Remote agent gateways

Supported capabilities:
- Tools
- Resources
- Prompts

Supported transports:
- stdio
- Streamable HTTP

Protocol:
- JSON-RPC 2.0
- UTF-8

---

## 2. Compatibility
### Recommended Priority
1. stdio (Claude Code)
2. HTTP (remote deployment)
3. gateway / multi-agent routing

---

## 3. Tool Contract Template

## Tool: search_docs

### Purpose
Search internal documentation.

### Risk Level
Read-only

### Input Schema
```json
{
  "type": "object",
  "properties": {
    "query": { "type": "string" },
    "top_k": {
      "type": "integer",
      "minimum": 1,
      "maximum": 20,
      "default": 5
    }
  },
  "required": ["query"],
  "additionalProperties": false
}
```

### Output Schema
```json
{
  "type": "object",
  "properties": {
    "results": {
      "type": "array"
    }
  },
  "required": ["results"]
}
```

### Failure Codes
- INVALID_QUERY
- BACKEND_TIMEOUT
- INDEX_UNAVAILABLE

---

## 4. Resource URI Spec
```text
docs://product/{path}
docs://runbooks/{path}
dbschema://{database}/{table}
```

Rules:
- stable URI
- immutable identifiers
- chunk-friendly

---

## 5. Prompt Contract
## Prompt: summarize_incident

Arguments:
- incident_id
- output_style

Expected output:
- summary
- root cause
- action items

---

## 6. Error Model
```json
{
  "error": {
    "code": "BACKEND_TIMEOUT",
    "message": "request timeout",
    "retryable": true
  }
}
```

---

## 7. Claude Code Access Notes
Recommended config:
- local stdio
- explicit allowlist tools
- timeout control
- retry <= 2
