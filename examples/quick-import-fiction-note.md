# Example: Quick Import A Fiction Note

This example uses synthetic text. It is not copied from a real novel.

## Source

```text
Chapter 1: The apprentice finds a broken compass that always points toward the choice he most wants to avoid.
```

## Imported Draft Note

```markdown
---
type: source-note
domain: fiction-reasoning
status: draft
confidence: low
evidence_level: source_claim
source: synthetic-example
ingested: 2026-05-21
updated: 2026-05-21
use_for:
  - fiction_source_excerpt
  - plot_mechanics_review
scope: short synthetic excerpt for demonstrating quick import
should_not_use_for: treating this example as canon, final analysis, or writing advice
time_sensitivity: low
review_cycle: 180d
source_chapter: chapter-1
quote_location: opening premise
character_perspective: narrator
narrator_reliability: unknown
spoiler_scope: chapter-1
failure_modes:
  - confusing source text with interpretation
  - using the excerpt without tracking chapter scope
improvement_notes:
  - identify the compass rule boundary
  - split ability mechanics from character motivation if reused
---

# Broken Compass Excerpt

## Import Summary

Low-trust draft imported from synthetic example text.

## Source Text

Chapter 1: The apprentice finds a broken compass that always points toward the choice he most wants to avoid.
```

## Why Draft

The excerpt is a raw source note. It has not been reviewed, split, or connected to a larger timeline.
