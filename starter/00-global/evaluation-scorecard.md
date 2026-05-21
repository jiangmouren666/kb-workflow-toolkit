---
type: evaluation
domain: global
status: draft
confidence: high
source: system-design
updated: 2026-05-17
use_when:
  - evaluate knowledge base effect
  - compare baseline and knowledge-guided answers
---

# Evaluation Scorecard

Score each answer from 0 to 10.

| Item | 0 | 1 | 2 |
|---|---|---|---|
| Knowledge basis | no saved-note basis | vague basis | cites relevant vault notes or standards |
| Workflow fit | generic | partly follows workflow | follows domain workflow and output contract |
| Risk detection | misses key risks | mentions common risks | identifies domain-specific risks and conflicts |
| Uncertainty handling | invents missing facts | partial caveats | clearly separates facts, assumptions, and unknowns |
| Executability | vague advice | partial steps | concrete next steps and validation plan |

## Effective Knowledge Test

Use the same prompt twice:

- A group: no knowledge base instruction.
- B group: "基于我的知识库..." and require references.

If B average score is at least 2 points higher than A across several prompts, the vault is improving answers.
