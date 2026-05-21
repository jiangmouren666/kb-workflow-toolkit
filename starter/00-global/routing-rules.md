---
type: standard
domain: global
status: draft
confidence: high
source: system-design
updated: 2026-05-17
use_when:
  - route knowledge ingestion
  - route knowledge-based answers
  - combine multiple vaults
---

# Routing Rules

## Ingestion Routing

Choose `primary_domain` first, then `related_domains`.

| Signal | Primary Domain |
|---|---|
| 因子、回测、实盘、RankIC、ICIR、交易成本、股票池、未来函数 | `quant` |
| 模型训练、交叉验证、特征工程、过拟合、指标、数据泄漏 | `machine-learning` |
| Agent、Prompt、工具调用、自动化研究、多智能体、工作流 | `ai-agent` |

If confidence is low, write to the most relevant domain's `00-inbox/`. If no domain is clear, ask one placement question.

## Answer Routing

For user questions:

1. Identify task type and risk level.
2. Read global routing rules.
3. Read relevant domain indexes.
4. Read domain standards before cases or drafts.
5. Build a Context Pack with only the relevant evidence.

## Cross-Domain Examples

- "用机器学习预测股票收益" -> `quant` + `machine-learning`.
- "用 Agent 自动复现因子论文" -> `quant` + `ai-agent`.
- "QuantaAlpha 这类项目怎么学" -> `quant` + `ai-agent`.

## Conflict Priority

1. Safety and timing constraints.
2. Global standards.
3. Domain standards.
4. Verified notes.
5. Current methods/templates.
6. Draft notes.
7. Raw or stale notes.

When sources conflict, state the conflict and avoid forcing a fake synthesis.
