---
type: standard
domain: quant-factor
status: reviewed
confidence: high
evidence_level: user_experience
use_for:
  - quant_research_standard
  - lookahead_checklist
  - backtest_review
scope: factor research, backtests, portfolio construction, and signal timing checks
should_not_use_for: approving live trading without independent validation, costs, and execution checks
time_sensitivity: medium
review_cycle: 180d
source: research-practice
use_when:
  - factor reproduction
  - backtest validation
  - code generation
updated: 2026-05-16
usage_count: 0
last_used: 
last_feedback: 
failure_modes:
improvement_notes:
human_review:
  reviewer: user
  decision: S=B,U=C,R=B,E=E
  reviewed_at: 2026-05-17
  result: registry overlay restored; Default anti-lookahead standard, not external proof
---

# Anti-lookahead Rules

## Principle

任何因子值只能使用信号时点已经可获得的数据。不能用未来价格、未来成分股、未来财报、未来修正数据或测试集反馈。

## Required Checks

- [ ] 财务数据使用公告日或可得日，不使用报告期直接对齐。
- [ ] 股票池是 point-in-time，不使用事后幸存股票池。
- [ ] 行业、市值、指数成分按当时可得版本处理。
- [ ] 复权价格和收益率没有使用未来调整信息造成泄漏。
- [ ] 因子标准化和中性化只使用当日横截面信息。
- [ ] 模型训练、调参、选因子不查看最终 holdout 结果。

## Red Flags

- 论文只写 reporting period，没有公告日处理。
- 代码直接 merge 财报期末日期和交易日期。
- 使用当前指数成分回测历史。
- 多次查看测试集后改因子。
- 用全样本均值、标准差、分位点处理历史因子。

## Output Requirement

复现或生成代码时，必须说明每个字段的 `data_date`、`available_date` 和 `signal_date` 关系。
