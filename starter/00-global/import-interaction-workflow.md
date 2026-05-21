---
type: workflow
domain: global
status: reviewed
confidence: high
evidence_level: user_experience
source: system-design
updated: 2026-05-18
use_for:
  - import_interaction
  - human_in_the_loop_ingestion
  - quick_import
scope: user-facing import confirmation flow for reusable knowledge vault packaging
should_not_use_for: replacing domain standards, external verification, or post-import maintenance scans
time_sensitivity: medium
review_cycle: 180d
human_review:
  reviewer: user
  decision: import should ask in chat before final write, with quick-import escape hatch
  reviewed_at: 2026-05-18
  result: accepted as user-facing import workflow
usage_count: 0
last_used:
last_feedback:
failure_modes: []
improvement_notes: []
---

# Import Interaction Workflow

## Core Rule

Ingestion should ask the user before the final write when the answer affects future retrieval, citation strength, trust status, or folder placement.

Do not hide all review questions inside the saved note. The user should see the important decisions in the chat window first.

## Two Supported Paths

### 1. Guided Import

Use when the user has time to answer a few questions.

Flow:

1. Read the material.
2. Propose target path, domain, status, use, and risk.
3. Ask 2-3 high-impact questions.
4. Explain every option, recommendation, and effect.
5. Apply the answers before writing the note.
6. Save the note and report the final metadata.

### 2. Quick Import

Use when the user says `快速导入`, `默认处理`, `先导入`, `不想回答`, `跳过问题`, or equivalent wording.

Flow:

1. Do not block the user with questions.
2. Save as low-trust `draft`.
3. Use `evidence_level: source_claim`.
4. Add clear `risks`, `unknowns`, `scope`, and `should_not_use_for`.
5. Add skipped review questions under `Human Review Needed` or to a review queue.
6. Never mark the note `reviewed` or `verified`.

## Prompt Template

```markdown
## 入库前确认
我建议这样入库：
- target:
- domain:
- status:
- use_for:
- risk:
- why:

请回复选项，例如 `1C 2A 3Q`。
如果不想细答，回复 `Q` 或 `快速导入`，我会按低信任草稿入库，并保留后续人工审核提醒。

1. 这条资料以后主要用来回答什么？
- A. 学习/理解：以后用于解释概念，引用强度低。
- B. checklist/流程：以后用于生成步骤和检查表。
- C. 决策审查：以后优先用于提醒风险、缺口和验证步骤。
- D. 反例/风险提醒：以后主要用于避免误用。
- Q. 快速导入：先按低信任草稿保存，之后再审核。
- 推荐：<option>，因为 <reason>。
```

## Metadata Mapping

| User Signal | Metadata Effect |
|---|---|
| 学习/理解 | `use_for: learning`, low citation strength |
| checklist/流程 | `use_for: checklist` or `workflow_reference` |
| 决策审查 | `use_for: decision_review`, stronger risk warnings |
| 反例/风险提醒 | `use_for: risk_warning`, do not use as positive recommendation |
| 快速导入 | `status: draft`, `confidence: low`, `evidence_level: source_claim` |
| 人工认可但无外部证据 | may become `reviewed`, not `verified` |
| 官方文档/源码/实验/回测已核验 | may become `verified` if domain standard allows |

## Guardrails

- Ask fewer questions, but ask them before writing.
- The user can always skip.
- Human approval improves usefulness and scope, not factual proof.
- High-risk or time-sensitive material should default to `draft` unless evidence is strong.
- If quick import is used repeatedly, batch the skipped questions into the next human review session.
