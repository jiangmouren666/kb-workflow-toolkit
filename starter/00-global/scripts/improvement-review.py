#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import date
from pathlib import Path


DECISION_MAP = {
    "A": "accepted_for_review",
    "B": "needs_more_evidence",
    "C": "deferred",
    "D": "rejected",
    "E": "converted_to_task",
}
REGISTRY_HEADER = """---
type: registry
domain: global
status: draft
confidence: high
source: improvement-review.py
updated: {today}
---

# Improvement Review Registry

This registry records human decisions about improvement candidates. It is not a trust-status overlay and must not be used to upgrade or downgrade note status automatically.

| Candidate ID | Path | Candidate Type | Decision | Reviewed At | Reason | Next Action |
|---|---|---|---|---|---|---|
"""


def candidate_id(candidate: dict) -> str:
    raw = "\n".join(
        [
            str(candidate.get("path", "")),
            str(candidate.get("candidate_type", "")),
            str(candidate.get("reason", "")),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def registry_path(root: Path) -> Path:
    return root / "00-global" / "improvement-review-registry.md"


def candidates_path(root: Path) -> Path:
    return root / "00-global" / "state" / "improvement-candidates.jsonl"


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def load_candidates(root: Path) -> list[dict]:
    return read_jsonl(candidates_path(root))


def parse_decisions(text: str) -> dict[int, str]:
    decisions: dict[int, str] = {}
    for index, code in re.findall(r"(\d+)\s*([A-Ea-e])", text):
        decisions[int(index)] = DECISION_MAP[code.upper()]
    return decisions


def render_batch(candidates: list[dict], limit: int = 5) -> str:
    selected = candidates[:limit]
    lines = [
        "## Improvement Candidates Review",
        "",
        "Reply with compact decisions such as `1A 2C 3E`.",
        "",
        "Options:",
        "- A accepted_for_review",
        "- B needs_more_evidence",
        "- C deferred",
        "- D rejected",
        "- E converted_to_task",
        "",
    ]
    if not selected:
        lines.append("- No pending improvement candidates.")
        return "\n".join(lines) + "\n"
    for idx, item in enumerate(selected, start=1):
        lines.extend(
            [
                f"### {idx}. `{item.get('path', '')}`",
                "",
                f"- candidate_id: `{candidate_id(item)}`",
                f"- type: `{item.get('candidate_type', '')}`",
                f"- severity: `{item.get('severity', '')}`",
                f"- reason: {item.get('reason', '')}",
                f"- suggested_action: {item.get('suggested_action', '')}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def escape_cell(value: object) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", " ").strip()


def parse_registry(root: Path) -> dict[str, dict]:
    path = registry_path(root)
    if not path.exists():
        return {}
    entries: dict[str, dict] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith("| `"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 7:
            continue
        cid = cells[0].strip("`")
        entries[cid] = {
            "candidate_id": cid,
            "path": cells[1].strip("`"),
            "candidate_type": cells[2],
            "decision": cells[3],
            "reviewed_at": cells[4],
            "reason": cells[5],
            "next_action": cells[6],
        }
    return entries


def render_registry(entries: dict[str, dict]) -> str:
    lines = [REGISTRY_HEADER.format(today=date.today().isoformat()).rstrip()]
    for cid in sorted(entries):
        item = entries[cid]
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{cid}`",
                    f"`{escape_cell(item.get('path'))}`",
                    escape_cell(item.get("candidate_type")),
                    escape_cell(item.get("decision")),
                    escape_cell(item.get("reviewed_at")),
                    escape_cell(item.get("reason")),
                    escape_cell(item.get("next_action")),
                ]
            )
            + " |"
        )
    return "\n".join(lines).rstrip() + "\n"


def decision_reason(candidate: dict, decision: str, note: str = "") -> str:
    return note or f"User marked candidate as {decision}"


def next_action_for(decision: str) -> str:
    return {
        "accepted_for_review": "Queue for manual knowledge maintenance; do not auto-change trust status.",
        "needs_more_evidence": "Collect source, version, experiment, backtest, or production evidence.",
        "deferred": "Keep as a future candidate and revisit later.",
        "rejected": "Suppress this exact candidate unless the reason changes.",
        "converted_to_task": "Track as an external task; do not auto-edit notes.",
    }.get(decision, "No automatic action.")


def write_registry_decisions(root: Path, candidates: list[dict], decisions: dict[int, str], note: str = "") -> Path:
    entries = parse_registry(root)
    for index, decision in decisions.items():
        if index < 1 or index > len(candidates):
            continue
        item = candidates[index - 1]
        cid = candidate_id(item)
        entries[cid] = {
            "candidate_id": cid,
            "path": item.get("path", ""),
            "candidate_type": item.get("candidate_type", ""),
            "decision": decision,
            "reviewed_at": date.today().isoformat(),
            "reason": decision_reason(item, decision, note),
            "next_action": next_action_for(decision),
        }
    path = registry_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_registry(entries), encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Review improvement candidates and record human decisions.")
    parser.add_argument("--root", required=True)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--decisions", default="", help='Compact decisions, e.g. "1A 2C".')
    parser.add_argument("--note", default="", help="Optional reason to store with decisions.")
    args = parser.parse_args()
    root = Path(args.root)
    candidates = load_candidates(root)
    selected = candidates[: args.limit]
    print(render_batch(selected, limit=args.limit), end="")
    if args.decisions:
        decisions = parse_decisions(args.decisions)
        path = write_registry_decisions(root, selected, decisions, note=args.note)
        print(f"decisions_recorded: {len(decisions)}")
        print(f"registry: {path}")


if __name__ == "__main__":
    main()
