---
type: standard
domain: quant-factor
status: reviewed
confidence: high
evidence_level: user_experience
use_for:
  - factor_validation
  - research_checklist
  - pre_live_review
scope: factor research validation before considering simulation, paper trading, or live deployment
should_not_use_for: using a single metric such as Sharpe or RankIC as sufficient live-trading evidence
time_sensitivity: medium
review_cycle: 180d
source: research-practice
use_when:
  - validate factor
  - review backtest
  - compare factor variants
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
  result: registry overlay restored; Default factor validation checklist, not live-trading approval
---

# Factor Validation Checklist

## Minimum Outputs

- [ ] 因子值表：`date, asset, factor_value`。
- [ ] 覆盖率：每日有效股票数量和缺失比例。
- [ ] RankIC 和 ICIR。
- [ ] 分组收益和多空收益。
- [ ] 换手率和成本后收益。
- [ ] 行业、市值、风格暴露检查。
- [ ] 分年度或分市场环境稳定性。

## Reliability Checks

- [ ] 因子方向与论文或经济逻辑一致。
- [ ] 极值处理和标准化没有使用未来信息。
- [ ] 结果不是由少数极端日期贡献。
- [ ] 高收益组合不是不可交易小盘或停牌股票驱动。
- [ ] 参数选择没有在测试集上反复调优。

## Decision Labels

- `promising`：通过基本稳健性检查，可以继续研究。
- `needs-review`：有信号但存在口径或风险问题。
- `rejected`：无稳定信号或存在不可接受的数据问题。
