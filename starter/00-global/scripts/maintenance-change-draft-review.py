#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path


DECISION_BY_CODE = {
    "A": "ready_to_apply",
    "B": "needs_more_evidence",
    "C": "request_changes",
    "D": "rejected",
    "E": "deferred",
}
APPLY_CONSTRAINTS_BY_DECISION = {
    "ready_to_apply": "May enter a later explicit apply workflow; this review still does not edit notes.",
    "needs_more_evidence": "Collect missing evidence before apply preparation.",
    "request_changes": "Revise or regenerate the change draft before apply preparation.",
    "rejected": "Suppress this exact change draft unless superseded.",
    "deferred": "Keep draft available for future review.",
}


def drafts_jsonl_path(root: Path) -> Path:
    return root / "00-global" / "state" / "maintenance-change-drafts.jsonl"


def registry_path(root: Path) -> Path:
    return root / "00-global" / "maintenance-change-draft-review-registry.md"


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


def sanitize_cell(value: object) -> str:
    return str(value or "").replace("|", "/").replace("\n", " ").strip()


def parse_decisions(text: str) -> dict[int, str]:
    decisions: dict[int, str] = {}
    for token in (text or "").split():
        match = re.fullmatch(r"(\d+)([A-Ea-e])", token)
        if not match:
            raise SystemExit(f"invalid decision token: {token}")
        raw_index, raw_code = match.groups()
        index = int(raw_index)
        if index < 1:
            raise SystemExit(f"invalid decision index: {index}")
        decisions[index] = DECISION_BY_CODE[raw_code.upper()]
    if (text or "").strip() and not decisions:
        raise SystemExit("no valid decisions found; use compact forms such as `1A 2D`")
    return decisions


def read_review_registry(root: Path) -> dict[str, dict]:
    path = registry_path(root)
    if not path.exists():
        return {}
    decisions: dict[str, dict] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 8 or cells[0] in {"Draft ID", "---"}:
            continue
        draft_id, proposal_id, draft_path, change_type, decision, reviewed_at, reason, apply_constraints = cells
        decisions[draft_id] = {
            "draft_id": draft_id,
            "proposal_id": proposal_id,
            "path": draft_path,
            "change_type": change_type,
            "decision": decision,
            "reviewed_at": reviewed_at,
            "reason": reason,
            "apply_constraints": apply_constraints,
        }
    return decisions


def apply_prior_decisions(drafts: list[dict], prior: dict[str, dict]) -> list[dict]:
    reviewable: list[dict] = []
    for draft in drafts:
        decision = prior.get(draft.get("draft_id", ""))
        if decision and decision.get("decision") in {"ready_to_apply", "rejected"}:
            continue
        item = dict(draft)
        if decision:
            item["prior_review_decision"] = decision.get("decision", "")
            item["prior_reviewed_at"] = decision.get("reviewed_at", "")
        reviewable.append(item)
    return reviewable


def reviewable_drafts(root: Path, limit: int) -> list[dict]:
    drafts = sorted(
        read_jsonl(drafts_jsonl_path(root)),
        key=lambda item: (item.get("change_type", ""), item.get("path", ""), item.get("draft_id", "")),
    )
    return apply_prior_decisions(drafts, read_review_registry(root))[:limit]


def render_batch(drafts: list[dict], limit: int = 5) -> str:
    lines = [
        "# Maintenance Change Draft Review",
        "",
        "Decision options: A ready_to_apply, B needs_more_evidence, C request_changes, D rejected, E deferred",
        "Reply format: `1A 2C 3E`",
        "",
    ]
    for index, draft in enumerate(drafts[:limit], start=1):
        lines.extend(
            [
                f"### {index}. `{draft.get('path', '')}`",
                "",
                f"- draft_id: `{draft.get('draft_id', '')}`",
                f"- proposal_id: `{draft.get('proposal_id', '')}`",
                f"- change_type: `{draft.get('change_type', '')}`",
                f"- summary: {draft.get('summary', '')}",
            ]
        )
        if draft.get("prior_review_decision"):
            lines.append(f"- prior_review_decision: `{draft.get('prior_review_decision')}`")
        lines.extend(["- draft_steps:"])
        for step in draft.get("draft_steps", []) or ["None"]:
            lines.append(f"  - {step}")
        lines.extend(["- evidence_to_check:"])
        for evidence in draft.get("evidence_to_check", []) or ["None"]:
            lines.append(f"  - {evidence}")
        lines.extend([""])
    if not drafts:
        lines.append("No reviewable maintenance change drafts.")
    return "\n".join(lines).rstrip() + "\n"


def registry_header() -> str:
    return (
        "# Maintenance Change Draft Review Registry\n\n"
        "This registry records human final-approval decisions on maintenance change drafts. It authorizes later apply workflow preparation only; it does not apply patches or modify knowledge notes.\n\n"
        "| Draft ID | Proposal ID | Path | Change Type | Decision | Reviewed At | Reason | Apply Constraints |\n"
        "| --- | --- | --- | --- | --- | --- | --- | --- |\n"
    )


def registry_row(draft: dict, decision: str, reviewed_at: str, reason: str) -> str:
    cells = [
        draft.get("draft_id", ""),
        draft.get("proposal_id", ""),
        draft.get("path", ""),
        draft.get("change_type", ""),
        decision,
        reviewed_at,
        reason,
        APPLY_CONSTRAINTS_BY_DECISION[decision],
    ]
    return "| " + " | ".join(sanitize_cell(cell) for cell in cells) + " |\n"


def write_registry_decisions(root: Path, drafts: list[dict], decisions: dict[int, str], note: str = "") -> Path:
    path = registry_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(registry_header(), encoding="utf-8")
    existing_text = path.read_text(encoding="utf-8")
    if not existing_text.strip():
        existing_text = registry_header()
    if not existing_text.endswith("\n"):
        existing_text += "\n"
    reviewed_at = datetime.now().isoformat(timespec="seconds")
    rows: list[str] = []
    for index, decision in sorted(decisions.items()):
        if index > len(drafts):
            raise SystemExit(f"decision index {index} exceeds displayed draft count {len(drafts)}")
        rows.append(registry_row(drafts[index - 1], decision, reviewed_at, note))
    path.write_text(existing_text + "".join(rows), encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Review maintenance change drafts and record final approval decisions.")
    parser.add_argument("--root", required=True)
    parser.add_argument("--limit", type=int, default=5, help="Number of drafts to show")
    parser.add_argument("--decisions", default="", help='Compact decisions such as "1A 2D"')
    parser.add_argument("--note", default="", help="Optional reason stored with decisions")
    args = parser.parse_args()

    root = Path(args.root)
    drafts = reviewable_drafts(root, args.limit)
    if not args.decisions:
        print(render_batch(drafts, args.limit), end="")
        return

    decisions = parse_decisions(args.decisions)
    path = write_registry_decisions(root, drafts, decisions, note=args.note)
    print(f"decisions_recorded: {len(decisions)}")
    print(f"registry: {path}")


if __name__ == "__main__":
    main()
