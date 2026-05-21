#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path


SCHEMA = "knowledge-maintenance-change-draft-v1"
CHANGE_TYPE_BY_PROPOSAL_TYPE = {
    "metadata_update_proposal": "metadata_change_draft",
    "evidence_collection_plan": "evidence_collection_draft",
    "external_task_brief": "external_task_draft",
}


def proposals_jsonl_path(root: Path) -> Path:
    return root / "00-global" / "state" / "maintenance-proposals.jsonl"


def proposal_review_registry_path(root: Path) -> Path:
    return root / "00-global" / "maintenance-proposal-review-registry.md"


def draft_review_registry_path(root: Path) -> Path:
    return root / "00-global" / "maintenance-change-draft-review-registry.md"


def drafts_markdown_path(root: Path) -> Path:
    return root / "00-global" / "maintenance-change-drafts.md"


def drafts_jsonl_path(root: Path) -> Path:
    return root / "00-global" / "state" / "maintenance-change-drafts.jsonl"


def draft_id(proposal_id: str, proposal_type: str, path: str) -> str:
    raw = "\n".join([proposal_id, proposal_type, path])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


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


def read_proposal_review_registry(root: Path) -> dict[str, dict]:
    path = proposal_review_registry_path(root)
    if not path.exists():
        return {}
    decisions: dict[str, dict] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 7 or cells[0] in {"Proposal ID", "---"}:
            continue
        proposal_id_value, proposal_path, proposal_type, decision, reviewed_at, reason, next_action = cells
        decisions[proposal_id_value] = {
            "proposal_id": proposal_id_value,
            "path": proposal_path,
            "proposal_type": proposal_type,
            "decision": decision,
            "reviewed_at": reviewed_at,
            "reason": reason,
            "next_action": next_action,
        }
    return decisions


def read_draft_review_registry(root: Path) -> dict[str, dict]:
    path = draft_review_registry_path(root)
    if not path.exists():
        return {}
    decisions: dict[str, dict] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 8 or cells[0] in {"Draft ID", "---"}:
            continue
        draft_id_value, proposal_id_value, draft_path, change_type, decision, reviewed_at, reason, apply_constraints = cells
        decisions[draft_id_value] = {
            "draft_id": draft_id_value,
            "proposal_id": proposal_id_value,
            "path": draft_path,
            "change_type": change_type,
            "decision": decision,
            "reviewed_at": reviewed_at,
            "reason": reason,
            "apply_constraints": apply_constraints,
        }
    return decisions


def apply_draft_review_registry(drafts: list[dict], root: Path) -> list[dict]:
    prior = read_draft_review_registry(root)
    filtered: list[dict] = []
    for draft in drafts:
        decision = prior.get(draft.get("draft_id", ""))
        if decision and decision.get("decision") in {"ready_to_apply", "rejected"}:
            continue
        item = dict(draft)
        if decision:
            item["prior_review_decision"] = decision.get("decision", "")
            item["prior_reviewed_at"] = decision.get("reviewed_at", "")
        filtered.append(item)
    return filtered


def approved_proposals(root: Path) -> list[dict]:
    reviews = read_proposal_review_registry(root)
    proposals = read_jsonl(proposals_jsonl_path(root))
    approved: list[dict] = []
    for proposal in proposals:
        review = reviews.get(proposal.get("proposal_id", ""))
        if not review or review.get("decision") != "approved":
            continue
        item = dict(proposal)
        item["approved_at"] = review.get("reviewed_at", "")
        item["approval_reason"] = review.get("reason", "")
        approved.append(item)
    return sorted(approved, key=lambda item: (item.get("proposal_type", ""), item.get("path", ""), item.get("proposal_id", "")))


def draft_steps_for(proposal: dict, change_type: str) -> list[str]:
    if change_type == "metadata_change_draft":
        return [
            "Open the target note and compare current metadata against the proposal rationale.",
            "Draft explicit frontmatter or scope edits only where evidence supports them.",
            "Keep any trust-status change behind a separate final approval step.",
        ]
    if change_type == "evidence_collection_draft":
        return [
            "Collect the evidence types listed in evidence_needed.",
            "Record source, date/version, and validation limits before proposing any note edit.",
            "Escalate unresolved gaps instead of upgrading trust status.",
        ]
    if change_type == "external_task_draft":
        return [
            "Create an external work brief using the proposal rationale and source task.",
            "Track completion outside the vault until evidence is available.",
            "Bring completed results back as reviewed evidence before editing knowledge.",
        ]
    return ["Prepare a concrete human-reviewed change plan before editing knowledge."]


def draft_from_proposal(proposal: dict) -> dict:
    proposal_type = proposal.get("proposal_type", "")
    change_type = CHANGE_TYPE_BY_PROPOSAL_TYPE.get(proposal_type, "manual_change_draft")
    return {
        "schema": SCHEMA,
        "draft_id": draft_id(proposal.get("proposal_id", ""), proposal_type, proposal.get("path", "")),
        "proposal_id": proposal.get("proposal_id", ""),
        "source_task_id": proposal.get("source_task_id", ""),
        "path": proposal.get("path", ""),
        "proposal_type": proposal_type,
        "change_type": change_type,
        "status": "draft",
        "summary": proposal.get("rationale", ""),
        "draft_steps": draft_steps_for(proposal, change_type),
        "suggested_changes": proposal.get("proposed_changes", []),
        "evidence_to_check": proposal.get("evidence_needed", []),
        "risk_notes": proposal.get("risk_notes", []),
        "approved_at": proposal.get("approved_at", ""),
        "approval_reason": proposal.get("approval_reason", ""),
        "final_approval_required": True,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }


def existing_draft_ids(root: Path) -> set[str]:
    return {row.get("draft_id", "") for row in read_jsonl(drafts_jsonl_path(root))}


def generate_drafts(root: Path) -> list[dict]:
    existing = existing_draft_ids(root)
    drafts = [draft_from_proposal(proposal) for proposal in approved_proposals(root)]
    new_drafts = [draft for draft in drafts if draft["draft_id"] not in existing]
    return sorted(apply_draft_review_registry(new_drafts, root), key=lambda item: (item["change_type"], item["path"]))


def all_drafts(root: Path) -> list[dict]:
    drafts = apply_draft_review_registry(read_jsonl(drafts_jsonl_path(root)), root)
    return sorted(drafts, key=lambda item: (item.get("change_type", ""), item.get("path", "")))


def render_list(values: list[str]) -> list[str]:
    return [f"  - {value}" for value in values] or ["  - None"]


def render_markdown(root: Path, drafts: list[dict]) -> str:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for draft in drafts:
        grouped[draft.get("change_type", "unknown")].append(draft)
    lines = [
        "---",
        "type: maintenance",
        "domain: global",
        "status: draft",
        "confidence: high",
        "source: maintenance-change-drafts.py",
        f"updated: {date.today().isoformat()}",
        "---",
        "",
        "# Maintenance Change Drafts",
        "",
        f"- vault_root: `{root}`",
        f"- draft_count: {len(drafts)}",
        "- policy: concrete draft only; no patch is applied automatically",
        "",
    ]
    for change_type in ("metadata_change_draft", "evidence_collection_draft", "external_task_draft", "manual_change_draft"):
        lines.extend([f"## {change_type}", ""])
        items = grouped.get(change_type, [])
        if not items:
            lines.extend(["- None", ""])
            continue
        for draft in items:
            lines.extend(
                [
                    f"### `{draft['path']}`",
                    "",
                    f"- draft_id: `{draft['draft_id']}`",
                    f"- proposal_id: `{draft['proposal_id']}`",
                    f"- status: `{draft['status']}`",
                    f"- final_approval_required: `{str(draft['final_approval_required']).lower()}`",
                    f"- prior_review_decision: `{draft.get('prior_review_decision', 'none')}`",
                    f"- summary: {draft['summary']}",
                    "- draft_steps:",
                    *render_list(draft.get("draft_steps", [])),
                    "- suggested_changes:",
                    *render_list(draft.get("suggested_changes", [])),
                    "- evidence_to_check:",
                    *render_list(draft.get("evidence_to_check", [])),
                    "- risk_notes:",
                    *render_list(draft.get("risk_notes", [])),
                    "",
                ]
            )
    return "\n".join(lines).rstrip() + "\n"


def raw_draft(draft: dict) -> dict:
    item = dict(draft)
    item.pop("prior_review_decision", None)
    item.pop("prior_reviewed_at", None)
    return item


def write_outputs(root: Path, new_drafts: list[dict]) -> dict[str, Path]:
    existing = read_jsonl(drafts_jsonl_path(root))
    by_id = {draft.get("draft_id", ""): draft for draft in existing}
    ordered_ids = [draft.get("draft_id", "") for draft in existing]
    for draft in new_drafts:
        draft_key = draft["draft_id"]
        if draft_key not in by_id:
            ordered_ids.append(draft_key)
        by_id[draft_key] = draft
    merged = [by_id[draft_key] for draft_key in ordered_ids if draft_key in by_id]
    visible = apply_draft_review_registry(merged, root)
    markdown = drafts_markdown_path(root)
    jsonl = drafts_jsonl_path(root)
    markdown.parent.mkdir(parents=True, exist_ok=True)
    jsonl.parent.mkdir(parents=True, exist_ok=True)
    markdown.write_text(render_markdown(root, visible), encoding="utf-8")
    jsonl.write_text("".join(json.dumps(raw_draft(draft), ensure_ascii=False, sort_keys=True) + "\n" for draft in merged), encoding="utf-8")
    return {"markdown": markdown, "jsonl": jsonl}


def print_summary(drafts: list[dict]) -> None:
    counts: dict[str, int] = defaultdict(int)
    for draft in drafts:
        counts[draft.get("change_type", "unknown")] += 1
    print(f"draft_count: {len(drafts)}")
    for key in sorted(counts):
        print(f"{key}: {counts[key]}")
    for draft in drafts[:20]:
        print(f"- {draft.get('change_type')} `{draft.get('path')}`: {draft.get('summary')}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate and list approved maintenance change drafts.")
    parser.add_argument("--root", required=True)
    subparsers = parser.add_subparsers(dest="action", required=True)
    generate = subparsers.add_parser("generate", help="Generate change drafts from approved proposals")
    generate.add_argument("--write", action="store_true", help="Write maintenance change draft reports")
    subparsers.add_parser("list", help="List existing maintenance change drafts")
    args = parser.parse_args()

    root = Path(args.root)
    if args.action == "generate":
        drafts = generate_drafts(root)
        print_summary(drafts)
        if args.write:
            outputs = write_outputs(root, drafts)
            print(f"wrote_markdown: {outputs['markdown']}")
            print(f"wrote_jsonl: {outputs['jsonl']}")
    elif args.action == "list":
        print_summary(all_drafts(root))


if __name__ == "__main__":
    main()
