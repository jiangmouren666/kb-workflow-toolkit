---
type: standard
domain: global
status: draft
confidence: high
source: system-design
updated: 2026-05-17
use_when:
  - ask user to review imported notes
  - decide draft reviewed verified stale deprecated rejected
  - generate review queue options
  - minimize human review burden
---

# Review Decision Questions

## Core Rule

Human review should be small, explicit, and decision-oriented. Ask at most 1-3 questions per note or scan batch. Do not ask the user to re-read or re-organize the whole note.

Human answers are high-priority intent signals, not factual proof. Default to `reviewed`, not `verified`, unless external evidence or experiments support the claim.

## Import-Time Minimum Questions

When importing new material, ask only the questions that change future retrieval or answer behavior. Prefer 2-3 questions from this set:

```text
Q1. 这条资料以后主要用来回答什么问题？
A 学习/理解
B 生成方案/checklist
C 做决策审查
D 作为反例/风险提醒
```

```text
Q2. 它的主归属应该是哪一个？
A quant
B machine-learning
C ai-agent
D programming / other / inbox
```

```text
Q3. 你希望 Agent 引用它时的语气是什么？
A 只能作为灵感
B 可以作为参考经验
C 可以作为流程建议
D 必须先提醒未验证/有风险
```

```text
Q4. 这条资料最容易被误用在哪里？
A 被当成事实
B 被当成当前 API/版本
C 被当成实盘/生产建议
D 被过度泛化到其他场景
```

```text
Q5. 这条资料缺什么会明显影响回答？
A 原始来源
B 版本/时间
C 实验或运行证据
D 适用范围和边界
```

## Main Judgment Dimensions

### Direction Fit

```text
这条笔记是否符合你的长期方向？
A 保留
B 保留但降权
C 暂存 inbox
D 删除候选/不入库
```

### Trust Level

```text
你愿意让 Agent 以后引用这条笔记吗？
A 只能作为灵感
B 可以作为 reviewed 参考
C 可以作为 verified 强依据
D 不能引用，只能作为反例
```

### Classification Fit

```text
这条笔记分类是否正确？
A 正确
B 主库正确，但需要 related_domains
C 应移动到另一个库
D 不确定，留在 inbox
```

### Evidence Gap

```text
这条笔记要变得更可信，最缺什么？
A 原始来源/官方文档
B 版本/API 核对
C 最小可运行实验
D 回测/评估结果
E 人工经验判断即可
```

### Freshness Risk

```text
这条笔记是否有时效性风险？
A 低，不需要定期复查
B 中，180 天复查
C 高，30-90 天复查
D 已可能过期，标记 stale
```

### Actionability

```text
这条笔记后续应该怎么用？
A 生成回答时参考
B 转成 checklist
C 转成实验计划
D 只保留为历史记录
```

## Human Review Verification

After the user answers, run a consistency check before changing metadata:

- Does the decision conflict with domain standards?
- Does the suggested status exceed available evidence?
- Does classification match `use_when`, `scope`, and `should_not_use_for`?
- Are key risks or unknowns still missing?
- Should the note be `reviewed` rather than `verified`?

Default rule:

```text
人工认可 -> reviewed
人工认可 + 外部证据/实验/官方文档 -> verified
```

Record human decisions:

```yaml
human_review:
  reviewer: user
  decision: <e.g. 1B 2A 3D>
  reviewed_at: <YYYY-MM-DD>
  confidence: medium
```

Also add:

```markdown
## Review History

- <YYYY-MM-DD> user decision: <decision>
  - system_check:
  - result:
```

## Batch Review Template

```markdown
## 待你判断

### 1. <note title>
- path:
- current_status:
- suggested_status:
- reason:
- question:
  - A ...
  - B ...
  - C ...
  - D ...

请直接回复：`1A 2B 3D`
```

## Status Mapping

| User Choice | Suggested Metadata |
|---|---|
| Keep as idea | `status: draft`, `confidence: low` |
| Lightly accepted | `status: reviewed`, `confidence: medium` |
| Evidence-backed | `status: verified`, `confidence: high` |
| Possibly outdated | `status: stale`, lower confidence if needed |
| No longer recommended | `status: deprecated` with `replacement` if possible |
| Confirmed wrong | `status: rejected` with `rejected_reason` |

## Guardrails

- Do not upgrade to `verified` from preference alone.
- Do not mark `rejected` unless the user confirms or there is clear evidence.
- If the user says "基本认同", prefer `reviewed`, not `verified`.
- If the user says "先留着", keep `draft`.
- If the user says "不适合我的方向", mark `deprecated` or keep outside the main vault.
