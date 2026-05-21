#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path


SCHEMA = "knowledge-maintenance-proposal-v1"
PROPOSAL_BY_TASK_TYPE = {
    "manual_knowledge_review": "metadata_update_proposal",
    "evidence_collection": "evidence_collection_plan",
    "external_task": "external_task_brief",
}


def tasks_jsonl_path(root: Path) -> Path:
    return root / "00-global" / "state" / "maintenance-tasks.jsonl"


def proposals_markdown_path(root: Path) -> Path:
    return root / "00-global" / "maintenance-proposals.md"


def proposals_jsonl_path(root: Path) -> Path:
    return root / "00-global" / "state" / "maintenance-proposals.jsonl"


def review_registry_path(root: Path) -> Path:
    return root / "00-global" / "maintenance-proposal-review-registry.md"


def proposal_id(task_id: str, task_type: str, path: str) -> str:
    raw = "\n".join([task_id, task_type, path])
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


def existing_proposal_ids(root: Path) -> set[str]:
    return {row.get("proposal_id", "") for row in read_jsonl(proposals_jsonl_path(root))}


def read_review_registry(root: Path) -> dict[str, dict]:
    path = review_registry_path(root)
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


def apply_review_registry(proposals: list[dict], root: Path) -> list[dict]:
    prior = read_review_registry(root)
    filtered: list[dict] = []
    for proposal in proposals:
        decision = prior.get(proposal.get("proposal_id", ""))
        if decision and decision.get("decision") in {"approved", "rejected"}:
            continue
        item = dict(proposal)
        if decision:
            item["prior_review_decision"] = decision.get("decision", "")
            item["prior_reviewed_at"] = decision.get("reviewed_at", "")
        filtered.append(item)
    return filtered


def proposed_changes_for(task: dict, proposal_type: str) -> list[str]:
    if proposal_type == "metadata_update_proposal":
        return [
            "Review scope, should_not_use_for, failure_modes, and improvement_notes.",
            "Draft a status-change request only if evidence and domain standards support it.",
            "Add missing feedback fields if absent; do not change trust status automatically.",
        ]
    if proposal_type == "evidence_collection_plan":
        return [
            "Identify authoritative source, version, official documentation, source code, experiment, backtest, or production evidence.",
            "Record evidence gaps and validation steps before any trust-level change.",
        ]
    if proposal_type == "external_task_brief":
        return [
            "Create or track an external work item using the task reason and recommended action.",
            "Bring completed external results back as evidence before editing knowledge status.",
        ]
    return ["Prepare a human-reviewed maintenance plan before editing knowledge."]


def evidence_needed_for(task: dict, proposal_type: str) -> list[str]:
    if proposal_type == "evidence_collection_plan":
        return ["official_doc", "source_code", "experiment", "backtest", "production_result"]
    if proposal_type == "metadata_update_proposal":
        return ["human_review", "domain_standard_consistency_check", "scope_boundary_check"]
    if proposal_type == "external_task_brief":
        return ["external_task_result", "reviewed_evidence_summary"]
    return ["human_review"]


def risk_notes_for(task: dict) -> list[str]:
    return [
        "Do not apply this proposal automatically.",
        "Do not edit note status, registry entries, or domain standards without explicit approval.",
        f"Source task priority is {task.get('priority', 'unknown')}.",
    ]


def proposal_from_task(task: dict) -> dict | None:
    if task.get("status") != "open":
        return None
    proposal_type = PROPOSAL_BY_TASK_TYPE.get(task.get("task_type", ""))
    if not proposal_type:
        return None
    return {
        "schema": SCHEMA,
        "proposal_id": proposal_id(task.get("task_id", ""), task.get("task_type", ""), task.get("path", "")),
        "source_task_id": task.get("task_id", ""),
        "path": task.get("path", ""),
        "proposal_type": proposal_type,
        "status": "proposed",
        "rationale": task.get("reason", ""),
        "proposed_changes": proposed_changes_for(task, proposal_type),
        "evidence_needed": evidence_needed_for(task, proposal_type),
        "risk_notes": risk_notes_for(task),
        "approval_required": True,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }


def generate_proposals(root: Path) -> list[dict]:
    existing = existing_proposal_ids(root)
    proposals: list[dict] = []
    for task in read_jsonl(tasks_jsonl_path(root)):
        proposal = proposal_from_task(task)
        if not proposal or proposal["proposal_id"] in existing:
            continue
        proposals.append(proposal)
    return sorted(apply_review_registry(proposals, root), key=lambda item: (item["proposal_type"], item["path"]))


def all_proposals(root: Path) -> list[dict]:
    return sorted(read_jsonl(proposals_jsonl_path(root)), key=lambda item: (item.get("status", ""), item.get("proposal_type", ""), item.get("path", "")))


def render_list(values: list[str]) -> list[str]:
    return [f"  - {value}" for value in values] or ["  - None"]


def render_markdown(root: Path, proposals: list[dict]) -> str:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for proposal in proposals:
        grouped[proposal.get("proposal_type", "unknown")].append(proposal)
    lines = [
        "---",
        "type: maintenance",
        "domain: global",
        "status: draft",
        "confidence: high",
        "source: maintenance-proposals.py",
        f"updated: {date.today().isoformat()}",
        "---",
        "",
        "# Maintenance Proposals",
        "",
        f"- vault_root: `{root}`",
        f"- proposal_count: {len(proposals)}",
        "- policy: proposal only; no patch is applied automatically",
        "",
    ]
    for proposal_type in ("metadata_update_proposal", "evidence_collection_plan", "external_task_brief"):
        lines.extend([f"## {proposal_type}", ""])
        items = grouped.get(proposal_type, [])
        if not items:
            lines.extend(["- None", ""])
            continue
        for proposal in items:
            lines.extend(
                [
                    f"### `{proposal['path']}`",
                    "",
                    f"- proposal_id: `{proposal['proposal_id']}`",
                    f"- source_task_id: `{proposal['source_task_id']}`",
                    f"- status: `{proposal['status']}`",
                    f"- approval_required: `{str(proposal['approval_required']).lower()}`",
                    f"- prior_review_decision: `{proposal.get('prior_review_decision', 'none')}`",
                    f"- rationale: {proposal['rationale']}",
                    "- proposed_changes:",
                    *render_list(proposal.get("proposed_changes", [])),
                    "- evidence_needed:",
                    *render_list(proposal.get("evidence_needed", [])),
                    "- risk_notes:",
                    *render_list(proposal.get("risk_notes", [])),
                    "",
                ]
            )
    return "\n".join(lines).rstrip() + "\n"


def write_outputs(root: Path, new_proposals: list[dict]) -> dict[str, Path]:
    existing = read_jsonl(proposals_jsonl_path(root))
    by_id = {proposal.get("proposal_id", ""): proposal for proposal in existing}
    for proposal in new_proposals:
        by_id[proposal["proposal_id"]] = proposal
    merged = sorted(apply_review_registry(list(by_id.values()), root), key=lambda item: (item.get("proposal_type", ""), item.get("path", "")))
    markdown = proposals_markdown_path(root)
    jsonl = proposals_jsonl_path(root)
    markdown.parent.mkdir(parents=True, exist_ok=True)
    jsonl.parent.mkdir(parents=True, exist_ok=True)
    markdown.write_text(render_markdown(root, merged), encoding="utf-8")
    jsonl.write_text("".join(json.dumps(proposal, ensure_ascii=False, sort_keys=True) + "\n" for proposal in merged), encoding="utf-8")
    return {"markdown": markdown, "jsonl": jsonl}


def print_summary(proposals: list[dict]) -> None:
    counts: dict[str, int] = defaultdict(int)
    for proposal in proposals:
        counts[proposal.get("proposal_type", "unknown")] += 1
    print(f"proposal_count: {len(proposals)}")
    for key in sorted(counts):
        print(f"{key}: {counts[key]}")
    for proposal in proposals[:20]:
        print(f"- {proposal.get('proposal_type')} `{proposal.get('path')}`: {proposal.get('rationale')}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate and list maintenance change proposals from open tasks.")
    parser.add_argument("--root", required=True)
    subparsers = parser.add_subparsers(dest="action", required=True)
    generate = subparsers.add_parser("generate", help="Generate maintenance proposals from open tasks")
    generate.add_argument("--write", action="store_true", help="Write maintenance proposal reports")
    subparsers.add_parser("list", help="List existing maintenance proposals")
    args = parser.parse_args()
    root = Path(args.root)
    if args.action == "generate":
        proposals = generate_proposals(root)
        print_summary(proposals)
        if args.write:
            outputs = write_outputs(root, proposals)
            print(f"wrote_markdown: {outputs['markdown']}")
            print(f"wrote_jsonl: {outputs['jsonl']}")
    elif args.action == "list":
        print_summary(all_proposals(root))


if __name__ == "__main__":
    main()
