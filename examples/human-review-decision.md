# Example: Human Review Decision

Compact human review decisions keep the review process fast while preserving important boundaries.

## Input

```text
确认 Broken Compass S=A,U=C,R=C,E=A,Split=Y
```

## Meaning

- `S=A`: keep the note as `draft`.
- `U=C`: use it for decision or risk review.
- `R=C`: high misuse risk.
- `E=A`: source text exists, but review structure is incomplete.
- `Split=Y`: split into smaller notes before upgrading.

## Registry Row

```markdown
| `fiction-reasoning/20-notes/broken-compass-excerpt.md` | draft | `S=A,U=C,R=C,E=A,Split=Y` | 2026-05-21 | decision/risk review | high misuse risk | source/docs | Keep as raw source excerpt; split rule mechanics, character motivation, and plot-turn notes before upgrading |
```

## Boundary

This row records that the note is useful as raw material. It does not make the note `reviewed` or `verified`.
