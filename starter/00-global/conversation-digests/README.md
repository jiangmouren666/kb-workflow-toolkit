---
type: guide
domain: global
status: draft
confidence: high
evidence_level: user_experience
source: starter-template
updated: 2026-05-22
use_for:
  - conversation_distillation
  - agent_memory_review
scope: inbox for manually distilled reusable insights from agent conversations
should_not_use_for: storing full chat transcripts, private secrets, or externally verified facts
time_sensitivity: medium
review_cycle: 90d
usage_count: 0
last_used:
last_feedback:
failure_modes: []
improvement_notes: []
---

# Conversation Digests

Use this folder for manually created conversation digests.

The goal is to preserve reusable insight from agent conversations without saving full transcripts.

## What To Save

- Decisions and why they were made.
- Reusable workflows.
- Failure modes and fixes.
- Prompt or review patterns.
- Domain insights that should be reviewed later.
- Follow-up actions.

## What Not To Save

- Full chat logs.
- API keys, credentials, local private paths, or raw private data.
- Unreviewed agent claims as verified knowledge.
- Long source excerpts that belong in a domain note.

## Recommended Flow

1. User says: `把这段对话沉淀到知识库`.
2. Agent creates a digest using `conversation-digest-template.md`.
3. Save as `draft`.
4. Human later decides whether to split it into domain notes, workflow notes, rules, or skills.
