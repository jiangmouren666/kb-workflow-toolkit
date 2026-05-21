---
type: standard
domain: global
status: draft
confidence: high
source: system-design
updated: 2026-05-17
use_when:
  - answer from incomplete knowledge
  - detect missing critical evidence
  - avoid overclaiming from draft notes
  - explain why a knowledge-based answer is limited
---

# Answer Risk Reminders

## Core Rule

If the knowledge base lacks evidence that materially affects the answer, do not fill the gap with confident language. State the missing evidence, explain why it matters, and downgrade the answer to a plan, checklist, or conditional recommendation.

## Missing Evidence That Must Be Called Out

### Quant Research

When answering factor, backtest, or live trading questions, call out missing:

- stock universe and point-in-time membership
- sample period and train / validation / holdout split
- data availability dates and signal / trade date lag
- return label horizon and execution price
- transaction costs, slippage, impact, and turnover
- suspension, limit up/down, ST, delisting, and new-listing rules
- benchmark and risk exposure controls
- out-of-sample or paper-trading evidence

If these are missing, do not say a factor is ready for live trading.

### Machine Learning

When answering ML experiment questions, call out missing:

- target definition and label horizon
- feature availability time
- train / validation / holdout split
- leakage prevention rules
- preprocessing fit scope
- baseline model and evaluation metrics
- deployment or distribution-shift assumptions

If temporal prediction is involved, do not recommend random splits unless the note proves there is no temporal leakage risk.

### AI Agent Workflows

When answering agent or automation questions, call out missing:

- tool permissions and execution environment
- verification loop and success criteria
- failure recovery and human review points
- memory or knowledge source trust level
- logging, reproducibility, and rollback plan

If a workflow has no validation step, treat it as a proposal, not a reliable process.

### Engineering / API Notes

When answering from implementation notes, call out missing:

- library or framework version
- official documentation or source-code confirmation
- minimal runnable example
- dependency and environment requirements
- failure modes and rollback plan

If API compatibility is not verified, say the note is an architecture hint, not an implementation spec.

## Answer Downgrade Rules

Use these phrases when evidence is incomplete:

- "当前只能作为 `draft` 参考，不能作为强结论。"
- "这个回答依赖以下未确认前提..."
- "缺少这些字段会直接影响结论..."
- "更稳妥的输出是验证计划，而不是最终判断。"
- "这条笔记适合作为线索，不适合作为当前 API 事实。"

## Trust Labels

| Evidence State | Allowed Answer |
|---|---|
| `verified` + complete fields | recommendation with caveats |
| `reviewed` | reference with caveats; do not treat as proof |
| `draft` + partial fields | conditional plan |
| `stale` | historical note plus recheck request |
| `raw` | summary only |
| conflicting sources | conflict report, no forced synthesis |

## Response Pattern

```markdown
## 可回答部分
<what the knowledge base supports>

## 关键缺口
<missing evidence and why it matters>

## 降级后的结论
<conditional answer, plan, or checklist>

## 下一步补证
<minimal evidence needed to upgrade confidence>
```
