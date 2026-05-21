# Example: Maintain Plan Output

This is a shortened synthetic example of what `maintain plan` can produce after improvement review.

## Fiction Reasoning

```markdown
### `fiction-reasoning/20-notes/broken-compass-excerpt.md`

- plan_type: `metadata_review_plan`
- status: `ready_preview`
- proposed_operations:
  - Review whether this fiction note should be split into worldbuilding, ability-system, character, faction, and plot-arc cards.
  - Check ability boundary, cost, failure mode, and escalation logic before treating the outline as reusable canon.
  - Separate draft outline ideas from verified source-text facts, and keep speculative plot reasoning clearly marked.
- evidence_requirements:
  - human_review
  - version
  - spoiler_scope
  - timeline_position
  - source_chapter_or_outline_section
  - canon_vs_outline_boundary
```

## Programming

```markdown
### `programming/20-notes/example-api-client.md`

- plan_type: `metadata_review_plan`
- status: `ready_preview`
- proposed_operations:
  - Record the runnable command, dependency versions, environment assumptions, and expected output for this code note.
  - Separate source-code facts from interpretation, and link to official docs or upstream source when possible.
  - If this programming note is a quant workflow, verify data window, benchmark, transaction costs, and future leakage risks before reuse.
- evidence_requirements:
  - human_review
  - official_doc
  - source_code
  - runnable_command
  - dependency_versions
  - expected_output
```

## Quant

```markdown
### `quant/20-notes/example-factor.md`

- plan_type: `metadata_review_plan`
- status: `ready_preview`
- proposed_operations:
  - Check train/test split, rebalance window, benchmark, universe, and data availability before treating results as reusable evidence.
  - Review future leakage, survivorship bias, lookahead bias, and label construction assumptions.
  - Record transaction cost, slippage, limit-up/down handling, and execution price assumptions for any backtest.
- evidence_requirements:
  - human_review
  - data_availability
  - train_test_split
  - benchmark
  - transaction_costs
  - leakage_check
```

## Important

These plans are previews. They do not edit notes and do not change trust status.
