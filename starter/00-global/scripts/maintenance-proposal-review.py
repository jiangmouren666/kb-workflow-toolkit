#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path


DECISION_BY_CODE = {
    "A": "approved",
    "B": "needs_more_evidence",
    "C": "request_changes",
    "D": "rejected",
    "E": "deferred",
}
NEXT_ACTION_BY_DECISION = {
    "approved": "May enter a later execution-preparation stage; no patch is applied by this review.",
    "needs_more_evidence": "Collect missing evidence, then review again.",
    "request_changes": "Revise the proposal before any execution preparation.",
    "rejected": "Suppress this exact proposal unless a new task/proposal supersedes it.",
    "deferred": "Keep proposal available for future review.",
}


def proposals_jsonl_path(root: Path) -> Path:
    return root / "00-global" / "state" / "maintenance-proposals.jsonl"


def registry_path(root: Path) -> Path:
    return root / "00-global" / "maintenance-proposal-review-registry.md"


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
    for raw_index, raw_code in re.findall(r"(\d+)\s*([A-Ea-e])", text or ""):
        index = int(raw_index)
        if index < 1:
            raise SystemExit(f"invalid decision index: {index}")
        decisions[index] = DECISION_BY_CODE[raw_code.upper()]
    if text.strip() and not decisions:
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
        if len(cells) != 7 or cells[0] in {"Proposal ID", "---"}:
            continue
        proposal_id, proposal_path, proposal_type, decision, reviewed_at, reason, next_action = cells
        decisions[proposal_id] = {
            "proposal_id": proposal_id,
            "path": proposal_path,
            "proposal_type": proposal_type,
            "decision": decision,
            "reviewed_at": reviewed_at,
            "reason": reason,
            "next_action": next_action,
        }
    return decisions


def apply_prior_decisions(proposals: list[dict], prior: dict[str, dict]) -> list[dict]:
    reviewable: list[dict] = []
    for proposal in proposals:
        decision = prior.get(proposal.get("proposal_id", ""))
        if decision and decision.get("decision") in {"approved", "rejected"}:
            continue
        item = dict(proposal)
        if decision:
            item["prior_review_decision"] = decision.get("decision", "")
            item["prior_reviewed_at"] = decision.get("reviewed_at", "")
        reviewable.append(item)
    return reviewable


def reviewable_proposals(root: Path, limit: int) -> list[dict]:
    proposals = sorted(
        read_jsonl(proposals_jsonl_path(root)),
        key=lambda item: (item.get("proposal_type", ""), item.get("path", ""), item.get("proposal_id", "")),
    )
    reviewable = apply_prior_decisions(proposals, read_review_registry(root))
    return reviewable[:limit]


def render_batch(proposals: list[dict], limit: int = 5) -> str:
    lines = [
        "# Maintenance Proposal Review",
        "",
        "Decision options: A approved, B needs_more_evidence, C request_changes, D rejected, E deferred",
        "Reply format: `1A 2C 3E`",
        "",
    ]
    for index, proposal in enumerate(proposals[:limit], start=1):
        lines.extend(
            [
                f"### {index}. `{proposal.get('path', '')}`",
                "",
                f"- proposal_id: `{proposal.get('proposal_id', '')}`",
                f"- proposal_type: `{proposal.get('proposal_type', '')}`",
                f"- rationale: {proposal.get('rationale', '')}",
            ]
        )
        if proposal.get("prior_review_decision"):
            lines.append(f"- prior_review_decision: `{proposal.get('prior_review_decision')}`")
        lines.extend(["- proposed_changes:"])
        for change in proposal.get("proposed_changes", []) or ["None"]:
            lines.append(f"  - {change}")
        lines.extend(["- evidence_needed:"])
        for evidence in proposal.get("evidence_needed", []) or ["None"]:
            lines.append(f"  - {evidence}")
        lines.extend([""])
    if not proposals:
        lines.append("No reviewable maintenance proposals.")
    return "\n".join(lines).rstrip() + "\n"


def registry_header() -> str:
    return (
        "# Maintenance Proposal Review Registry\n\n"
        "This registry records human decisions on maintenance proposals. It authorizes later review stages only; it does not apply patches or modify knowledge notes.\n\n"
        "| Proposal ID | Path | Proposal Type | Decision | Reviewed At | Reason | Next Action |\n"
        "| --- | --- | --- | --- | --- | --- | --- |\n"
    )


def registry_row(proposal: dict, decision: str, reviewed_at: str, reason: str) -> str:
    next_action = NEXT_ACTION_BY_DECISION[decision]
    cells = [
        proposal.get("proposal_id", ""),
        proposal.get("path", ""),
        proposal.get("proposal_type", ""),
        decision,
        reviewed_at,
        reason,
        next_action,
    ]
    return "| " + " | ".join(sanitize_cell(cell) for cell in cells) + " |\n"


def write_registry_decisions(root: Path, proposals: list[dict], decisions: dict[int, str], note: str = "") -> Path:
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
        if index > len(proposals):
            raise SystemExit(f"decision index {index} exceeds displayed proposal count {len(proposals)}")
        rows.append(registry_row(proposals[index - 1], decision, reviewed_at, note))
    path.write_text(existing_text + "".join(rows), encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Review maintenance proposals and record approval decisions.")
    parser.add_argument("--root", required=True)
    parser.add_argument("--limit", type=int, default=5, help="Number of proposals to show")
    parser.add_argument("--decisions", default="", help='Compact decisions such as "1A 2D"')
    parser.add_argument("--note", default="", help="Optional reason stored with decisions")
    args = parser.parse_args()

    root = Path(args.root)
    proposals = reviewable_proposals(root, args.limit)
    if not args.decisions:
        print(render_batch(proposals, args.limit), end="")
        return

    decisions = parse_decisions(args.decisions)
    path = write_registry_decisions(root, proposals, decisions, note=args.note)
    print(f"decisions_recorded: {len(decisions)}")
    print(f"registry: {path}")


if __name__ == "__main__":
    main()
