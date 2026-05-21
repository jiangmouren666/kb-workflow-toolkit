---
type: standard
domain: quant-factor
status: reviewed
confidence: high
evidence_level: user_experience
use_for:
  - backtest_review
  - strategy_validation
  - risk_checklist
scope: research backtests for equity factors and systematic strategies
should_not_use_for: guaranteeing real-world performance or replacing paper/live trading validation
time_sensitivity: medium
review_cycle: 180d
source: research-practice
human_review:
  reviewer: user
  decision: 1B
  reviewed_at: 2026-05-17
  result: accepted as reviewed default backtest standard, not verified external fact
use_when:
  - design backtest
  - evaluate factor performance
  - generate validation plan
updated: 2026-05-16
usage_count: 0
last_used: 
last_feedback: 
failure_modes:
improvement_notes:
---

# Backtest Standards

## Splits

默认使用时间序列切分：

- train：用于研究和初始参数选择。
- validation：用于有限次数模型/因子选择。
- holdout：最终确认，不能反复查看。

## Portfolio Construction

必须说明：

- 股票池和排除规则。
- 调仓频率。
- 持仓权重。
- 行业/市值中性化方式。
- 交易成本和滑点。
- 停牌、涨跌停、退市处理。

## Metrics

至少报告：

- 年化收益、波动、夏普、最大回撤。
- 多空收益和分组单调性。
- RankIC、ICIR。
- 换手率和成本后表现。

## Reporting

不要只报告最佳样本。必须展示分年度、分市场状态或滚动窗口表现。

## Review History

- 2026-05-17 user decision: `1B`
  - reviewed_item: Backtest Standards
  - result: upgraded from `draft` to `reviewed` as the default quant backtest review standard.
  - system_check: This is accepted as a user-reviewed research standard, not as externally verified evidence.
