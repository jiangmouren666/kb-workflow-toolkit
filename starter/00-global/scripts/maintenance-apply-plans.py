#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path


SCHEMA = "knowledge-maintenance-apply-plan-v1"
ACTIONABLE_DECISIONS = {"accepted_for_review", "needs_more_evidence", "converted_to_task"}


def candidates_jsonl_path(root: Path) -> Path:
    return root / "00-global" / "state" / "improvement-candidates.jsonl"


def review_registry_path(root: Path) -> Path:
    return root / "00-global" / "improvement-review-registry.md"


def plans_markdown_path(root: Path) -> Path:
    return root / "00-global" / "maintenance-apply-plans.md"


def plans_jsonl_path(root: Path) -> Path:
    return root / "00-global" / "state" / "maintenance-apply-plans.jsonl"


def plan_id(candidate_id: str, decision: str, path: str) -> str:
    raw = "\n".join([candidate_id, decision, path])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def parse_review_registry(root: Path) -> list[dict]:
    path = review_registry_path(root)
    if not path.exists():
        return []
    entries: list[dict] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith("| `"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 7:
            continue
        entries.append(
            {
                "candidate_id": cells[0].strip("`"),
                "path": cells[1].strip("`"),
                "candidate_type": cells[2],
                "decision": cells[3],
                "reviewed_at": cells[4],
                "reason": cells[5],
                "next_action": cells[6],
            }
        )
    return entries


def safe_target_path(root: Path, relpath: str) -> Path | None:
    candidate_rel = Path(relpath)
    if candidate_rel.is_absolute() or candidate_rel.suffix != ".md":
        return None
    root_resolved = root.resolve()
    candidate = (root_resolved / candidate_rel).resolve()
    try:
        candidate.relative_to(root_resolved)
    except ValueError:
        return None
    return candidate


def plan_type_for(entry: dict) -> str:
    decision = entry.get("decision", "")
    if decision == "needs_more_evidence":
        return "evidence_collection_plan"
    if decision == "converted_to_task":
        return "external_task_plan"
    return "metadata_review_plan"


def proposed_operations_for(entry: dict, target_exists: bool) -> list[str]:
    if not target_exists:
        return ["Resolve target note availability before any future apply command."]
    path = str(entry.get("path", ""))
    if path.startswith("fiction-reasoning/"):
        return [
            "Review whether this fiction note should be split into worldbuilding, ability-system, character, faction, and plot-arc cards.",
            "Check ability boundary, cost, failure mode, and escalation logic before treating the outline as reusable canon.",
            "Separate draft outline ideas from verified source-text facts, and keep speculative plot reasoning clearly marked.",
            "Prepare explicit metadata or split-note edits in a later apply command only after target_sha256 matches.",
        ]
    if path.startswith("programming/"):
        return [
            "Record the runnable command, dependency versions, environment assumptions, and expected output for this code note.",
            "Separate source-code facts from interpretation, and link to official docs or upstream source when possible.",
            "If this programming note is a quant workflow, verify data window, benchmark, transaction costs, and future leakage risks before reuse.",
            "Prepare explicit metadata or split-note edits in a later apply command only after target_sha256 matches.",
        ]
    if path.startswith("quant/"):
        return [
            "Check train/test split, rebalance window, benchmark, universe, and data availability before treating results as reusable evidence.",
            "Review future leakage, survivorship bias, lookahead bias, and label construction assumptions.",
            "Record transaction cost, slippage, limit-up/down handling, and execution price assumptions for any backtest.",
            "Prepare explicit metadata or split-note edits in a later apply command only after target_sha256 matches.",
        ]
    decision = entry.get("decision", "")
    if decision == "needs_more_evidence":
        return [
            "Collect and attach evidence before changing trust status or metadata.",
            "Prepare note edits only after evidence satisfies the domain standard.",
        ]
    if decision == "converted_to_task":
        return [
            "Track external work outside the vault until results are available.",
            "Bring reviewed results back before editing the note.",
        ]
    return [
        "Review note metadata, scope, failure modes, and suggested action.",
        "Prepare explicit note edits in a later apply command only after target_sha256 matches.",
    ]


def evidence_requirements_for(entry: dict) -> list[str]:
    path = str(entry.get("path", ""))
    if path.startswith("fiction-reasoning/"):
        return [
            "human_review",
            "version",
            "spoiler_scope",
            "timeline_position",
            "source_chapter_or_outline_section",
            "canon_vs_outline_boundary",
        ]
    if path.startswith("programming/"):
        return [
            "human_review",
            "official_doc",
            "source_code",
            "runnable_command",
            "dependency_versions",
            "expected_output",
        ]
    if path.startswith("quant/"):
        return [
            "human_review",
            "data_availability",
            "train_test_split",
            "benchmark",
            "transaction_costs",
            "leakage_check",
        ]
    if entry.get("decision") == "needs_more_evidence":
        return ["official_doc", "source_code", "experiment", "backtest", "production_result", "human_review"]
    return ["human_review", "domain_standard_consistency_check", "scope_boundary_check"]


def preflight_checks_for(target_path_valid: bool, target_exists: bool) -> list[str]:
    if not target_path_valid:
        return [
            "target_path_invalid",
            "blocked_until_target_path_is_relative_markdown_inside_vault",
            "explicit_apply_confirmation_required",
        ]
    if not target_exists:
        return [
            "target_missing",
            "blocked_until_target_exists",
            "explicit_apply_confirmation_required",
        ]
    return [
        "target_exists",
        "target_sha256_recorded",
        "apply_requires_matching_target_sha256",
        "explicit_apply_confirmation_required",
    ]


def rollback_notes_for(target_exists: bool) -> list[str]:
    if target_exists:
        return [
            "Verify target_sha256 before any future apply.",
            "Capture full original file content immediately before applying.",
        ]
    return ["No rollback snapshot is available until the target file exists."]


def split_scaffold_path(relpath: str) -> str:
    path = Path(relpath)
    return path.with_name(f"{path.stem}-split-notes.md").as_posix()


def safe_operations_for(entry: dict, target_exists: bool) -> list[dict]:
    if not target_exists:
        return []
    relpath = str(entry.get("path", ""))
    operations: list[dict] = [
        {
            "operation": "metadata_patch",
            "mode": "missing_only",
            "fields": {
                "review_cycle": "180d",
                "time_sensitivity": "medium",
            },
        },
        {"operation": "append_review_note"},
    ]
    if relpath.startswith("fiction-reasoning/"):
        operations.append(
            {
                "operation": "split_draft_scaffold",
                "scaffolds": [
                    {
                        "path": split_scaffold_path(relpath),
                        "title": f"{Path(relpath).stem.replace('-', ' ').title()} Split Notes",
                    }
                ],
            }
        )
    return operations


def plan_from_review_entry(root: Path, entry: dict) -> dict:
    relpath = entry.get("path", "")
    target = safe_target_path(root, relpath)
    target_path_valid = target is not None
    target_exists = target.is_file() if target else False
    if not target_path_valid:
        status = "blocked_invalid_target_path"
    elif not target_exists:
        status = "blocked_missing_target"
    elif entry.get("decision") == "needs_more_evidence":
        status = "blocked_needs_more_evidence"
    else:
        status = "ready_preview"
    return {
        "schema": SCHEMA,
        "plan_id": plan_id(entry.get("candidate_id", ""), entry.get("decision", ""), relpath),
        "source_candidate_id": entry.get("candidate_id", ""),
        "source_candidate_type": entry.get("candidate_type", ""),
        "review_decision": entry.get("decision", ""),
        "reviewed_at": entry.get("reviewed_at", ""),
        "path": relpath,
        "plan_type": plan_type_for(entry),
        "status": status,
        "target_path_valid": target_path_valid,
        "target_exists": target_exists,
        "target_sha256": sha256(target) if target_exists else "",
        "target_size": target.stat().st_size if target_exists else 0,
        "reason": entry.get("reason", ""),
        "next_action": entry.get("next_action", ""),
        "proposed_operations": proposed_operations_for(entry, target_exists),
        "evidence_requirements": evidence_requirements_for(entry),
        "risk_notes": [
            "This is an apply plan preview only.",
            "Do not edit notes unless a later explicit apply command verifies target_sha256.",
        ],
        "preflight_checks": preflight_checks_for(target_path_valid, target_exists),
        "rollback_notes": rollback_notes_for(target_exists),
        "apply_requires_explicit_confirmation": True,
        "safe_operations": safe_operations_for(entry, target_exists),
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }


def generate_plans(root: Path) -> list[dict]:
    plans = [
        plan_from_review_entry(root, entry)
        for entry in parse_review_registry(root)
        if entry.get("decision") in ACTIONABLE_DECISIONS
    ]
    return sorted(plans, key=lambda item: (item["status"], item["path"], item["plan_type"]))


def all_plans(root: Path) -> list[dict]:
    return sorted(read_jsonl(plans_jsonl_path(root)), key=lambda item: (item.get("status", ""), item.get("path", ""), item.get("plan_type", "")))


def status_summary(root: Path) -> dict[str, int]:
    plans = all_plans(root)
    return {
        "candidate_count": len(read_jsonl(candidates_jsonl_path(root))),
        "review_decision_count": len(parse_review_registry(root)),
        "apply_plan_count": len(plans),
        "ready_plan_count": sum(1 for plan in plans if plan.get("status") == "ready_preview"),
        "blocked_plan_count": sum(1 for plan in plans if str(plan.get("status", "")).startswith("blocked_")),
    }


def render_list(values: list[str]) -> list[str]:
    return [f"  - {value}" for value in values] or ["  - None"]


def render_markdown(root: Path, plans: list[dict]) -> str:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for plan in plans:
        grouped[plan.get("status", "unknown")].append(plan)
    lines = [
        "---",
        "type: maintenance",
        "domain: global",
        "status: draft",
        "confidence: high",
        "source: maintenance-apply-plans.py",
        f"updated: {date.today().isoformat()}",
        "---",
        "",
        "# Maintenance Apply Plans",
        "",
        f"- vault_root: `{root}`",
        f"- apply_plan_count: {len(plans)}",
        "- policy: consolidated apply plan preview only; no patch is applied automatically",
        "",
    ]
    for status in ("ready_preview", "blocked_needs_more_evidence", "blocked_missing_target", "blocked_invalid_target_path"):
        lines.extend([f"## {status}", ""])
        items = grouped.get(status, [])
        if not items:
            lines.extend(["- None", ""])
            continue
        for plan in items:
            lines.extend(
                [
                    f"### `{plan['path']}`",
                    "",
                    f"- plan_id: `{plan['plan_id']}`",
                    f"- source_candidate_id: `{plan['source_candidate_id']}`",
                    f"- plan_type: `{plan['plan_type']}`",
                    f"- target_sha256: `{plan['target_sha256']}`",
                    f"- apply_requires_explicit_confirmation: `{str(plan['apply_requires_explicit_confirmation']).lower()}`",
                    "- proposed_operations:",
                    *render_list(plan.get("proposed_operations", [])),
                    "- evidence_requirements:",
                    *render_list(plan.get("evidence_requirements", [])),
                    "- preflight_checks:",
                    *render_list(plan.get("preflight_checks", [])),
                    "- rollback_notes:",
                    *render_list(plan.get("rollback_notes", [])),
                    "",
                ]
            )
    return "\n".join(lines).rstrip() + "\n"


def write_outputs(root: Path, plans: list[dict]) -> dict[str, Path]:
    markdown = plans_markdown_path(root)
    jsonl = plans_jsonl_path(root)
    markdown.parent.mkdir(parents=True, exist_ok=True)
    jsonl.parent.mkdir(parents=True, exist_ok=True)
    markdown.write_text(render_markdown(root, plans), encoding="utf-8")
    jsonl.write_text("".join(json.dumps(plan, ensure_ascii=False, sort_keys=True) + "\n" for plan in plans), encoding="utf-8")
    return {"markdown": markdown, "jsonl": jsonl}


def print_plan_summary(plans: list[dict]) -> None:
    counts: dict[str, int] = defaultdict(int)
    for plan in plans:
        counts[plan.get("status", "unknown")] += 1
    print(f"apply_plan_count: {len(plans)}")
    for key in sorted(counts):
        print(f"{key}: {counts[key]}")
    for plan in plans[:20]:
        print(f"- {plan.get('status')} `{plan.get('path')}`: {plan.get('plan_type')}")


def print_status(root: Path) -> None:
    for key, value in status_summary(root).items():
        print(f"{key}: {value}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate consolidated maintenance apply plan previews.")
    parser.add_argument("--root", required=True)
    subparsers = parser.add_subparsers(dest="action", required=True)
    generate = subparsers.add_parser("generate", help="Generate consolidated apply plans from reviewed improvements")
    generate.add_argument("--write", action="store_true", help="Write maintenance apply plan reports")
    subparsers.add_parser("list", help="List existing maintenance apply plans")
    subparsers.add_parser("status", help="Summarize candidates, review decisions, and apply plans")
    args = parser.parse_args()

    root = Path(args.root)
    if args.action == "generate":
        plans = generate_plans(root)
        print_plan_summary(plans)
        if args.write:
            outputs = write_outputs(root, plans)
            print(f"wrote_markdown: {outputs['markdown']}")
            print(f"wrote_jsonl: {outputs['jsonl']}")
    elif args.action == "list":
        print_plan_summary(all_plans(root))
    elif args.action == "status":
        print_status(root)


if __name__ == "__main__":
    main()
