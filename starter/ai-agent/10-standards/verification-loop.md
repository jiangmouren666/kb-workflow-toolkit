---
type: standard
domain: ai-agent
status: draft
confidence: medium
source: system-design
updated: 2026-05-17
use_when:
  - design agent workflows
  - automate research
  - evaluate agent outputs
---

# Verification Loop

## Rules

- Treat LLM output as a hypothesis until checked.
- Prefer workflows with tool execution, evidence capture, and review.
- Separate generated ideas from validated results.
- Record failed attempts and reasons, not just successful outputs.
- For high-risk domains, require human approval before marking conclusions `verified`.

## Research Agent Pattern

```text
hypothesis -> data availability check -> implementation -> validation -> report -> review -> keep or reject
```
