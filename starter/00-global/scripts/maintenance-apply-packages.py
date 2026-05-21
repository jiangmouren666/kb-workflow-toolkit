#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path


SCHEMA = "knowledge-maintenance-apply-package-v1"


def drafts_jsonl_path(root: Path) -> Path:
    return root / "00-global" / "state" / "maintenance-change-drafts.jsonl"


def draft_review_registry_path(root: Path) -> Path:
    return root / "00-global" / "maintenance-change-draft-review-registry.md"


def packages_markdown_path(root: Path) -> Path:
    return root / "00-global" / "maintenance-apply-packages.md"


def packages_jsonl_path(root: Path) -> Path:
    return root / "00-global" / "state" / "maintenance-apply-packages.jsonl"


def package_id(draft_id: str, change_type: str, path: str) -> str:
    raw = "\n".join([draft_id, change_type, path])
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


def ready_drafts(root: Path) -> list[dict]:
    reviews = read_draft_review_registry(root)
    drafts = read_jsonl(drafts_jsonl_path(root))
    ready: list[dict] = []
    for draft in drafts:
        review = reviews.get(draft.get("draft_id", ""))
        if not review or review.get("decision") != "ready_to_apply":
            continue
        item = dict(draft)
        item["ready_reviewed_at"] = review.get("reviewed_at", "")
        item["ready_reason"] = review.get("reason", "")
        item["apply_constraints"] = review.get("apply_constraints", "")
        item["review_mismatch"] = any(
            [
                review.get("proposal_id", "") != draft.get("proposal_id", ""),
                review.get("path", "") != draft.get("path", ""),
                review.get("change_type", "") != draft.get("change_type", ""),
            ]
        )
        ready.append(item)
    return sorted(ready, key=lambda item: (item.get("change_type", ""), item.get("path", ""), item.get("draft_id", "")))


def proposed_operations_for(draft: dict, target_exists: bool) -> list[str]:
    if draft.get("review_mismatch"):
        return ["Do not apply; align the final-review registry row with the draft before packaging."]
    if not target_exists:
        return ["Do not create or edit the missing target in this phase; resolve the missing file before applying."]
    change_type = draft.get("change_type", "")
    if change_type == "metadata_change_draft":
        return [
            "Review the target note frontmatter against suggested_changes.",
            "Prepare explicit metadata edits in a later apply step only after confirming target_sha256.",
        ]
    if change_type == "evidence_collection_draft":
        return [
            "Attach or summarize verified evidence in a later apply step only after confirming target_sha256.",
            "Do not upgrade trust status without separate evidence-standard confirmation.",
        ]
    if change_type == "external_task_draft":
        return [
            "Record external task results in a later apply step only after confirming target_sha256.",
            "Keep incomplete external work outside note edits.",
        ]
    return ["Prepare a human-reviewed patch in a later explicit apply step only after confirming target_sha256."]


def preflight_checks_for(target_exists: bool) -> list[str]:
    if target_exists:
        return [
            "target_exists",
            "target_sha256_recorded",
            "apply_requires_matching_target_sha256",
            "explicit_apply_confirmation_required",
        ]
    return [
        "target_missing",
        "blocked_until_target_exists",
        "explicit_apply_confirmation_required",
    ]


def preflight_checks_for_package(target_path_valid: bool, target_exists: bool, review_mismatch: bool) -> list[str]:
    if review_mismatch:
        return [
            "review_registry_matches_draft_failed",
            "blocked_until_review_registry_matches_draft",
            "explicit_apply_confirmation_required",
        ]
    if not target_path_valid:
        return [
            "target_path_invalid",
            "blocked_until_target_path_is_relative_markdown_inside_vault",
            "explicit_apply_confirmation_required",
        ]
    return preflight_checks_for(target_exists)


def rollback_notes_for(target_exists: bool) -> list[str]:
    if target_exists:
        return [
            "Use target_sha256 to verify the file has not changed before applying.",
            "Before any future apply command, capture the full original file content for rollback.",
        ]
    return ["No rollback snapshot is available because the target file is missing."]


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


def package_from_draft(root: Path, draft: dict) -> dict:
    relpath = draft.get("path", "")
    target = safe_target_path(root, relpath)
    target_path_valid = target is not None
    target_exists = target.is_file() if target else False
    target_sha = sha256(target) if target_exists else ""
    if draft.get("review_mismatch"):
        status = "blocked_review_mismatch"
    elif not target_path_valid:
        status = "blocked_invalid_target_path"
    elif target_exists:
        status = "ready_preview"
    else:
        status = "blocked_missing_target"
    return {
        "schema": SCHEMA,
        "package_id": package_id(draft.get("draft_id", ""), draft.get("change_type", ""), relpath),
        "draft_id": draft.get("draft_id", ""),
        "proposal_id": draft.get("proposal_id", ""),
        "path": relpath,
        "change_type": draft.get("change_type", ""),
        "status": status,
        "target_path_valid": target_path_valid,
        "target_exists": target_exists,
        "target_sha256": target_sha,
        "target_size": target.stat().st_size if target_exists else 0,
        "preflight_checks": preflight_checks_for_package(target_path_valid, target_exists, bool(draft.get("review_mismatch"))),
        "proposed_operations": proposed_operations_for(draft, target_exists),
        "source_draft_summary": draft.get("summary", ""),
        "suggested_changes": draft.get("suggested_changes", []),
        "evidence_to_check": draft.get("evidence_to_check", []),
        "risk_notes": draft.get("risk_notes", []),
        "rollback_notes": rollback_notes_for(target_exists),
        "ready_reviewed_at": draft.get("ready_reviewed_at", ""),
        "ready_reason": draft.get("ready_reason", ""),
        "apply_constraints": draft.get("apply_constraints", ""),
        "review_mismatch": bool(draft.get("review_mismatch")),
        "apply_requires_explicit_confirmation": True,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }


def generate_packages(root: Path) -> list[dict]:
    packages = [package_from_draft(root, draft) for draft in ready_drafts(root)]
    return sorted(packages, key=lambda item: (item["status"], item["change_type"], item["path"]))


def all_packages(root: Path) -> list[dict]:
    return sorted(read_jsonl(packages_jsonl_path(root)), key=lambda item: (item.get("status", ""), item.get("change_type", ""), item.get("path", "")))


def render_list(values: list[str]) -> list[str]:
    return [f"  - {value}" for value in values] or ["  - None"]


def render_markdown(root: Path, packages: list[dict]) -> str:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for package in packages:
        grouped[package.get("status", "unknown")].append(package)
    lines = [
        "---",
        "type: maintenance",
        "domain: global",
        "status: draft",
        "confidence: high",
        "source: maintenance-apply-packages.py",
        f"updated: {date.today().isoformat()}",
        "---",
        "",
        "# Maintenance Apply Packages",
        "",
        f"- vault_root: `{root}`",
        f"- package_count: {len(packages)}",
        "- policy: apply package preview only; no patch is applied automatically",
        "",
    ]
    for status in ("ready_preview", "blocked_missing_target", "blocked_invalid_target_path", "blocked_review_mismatch"):
        lines.extend([f"## {status}", ""])
        items = grouped.get(status, [])
        if not items:
            lines.extend(["- None", ""])
            continue
        for package in items:
            lines.extend(
                [
                    f"### `{package['path']}`",
                    "",
                    f"- package_id: `{package['package_id']}`",
                    f"- draft_id: `{package['draft_id']}`",
                    f"- change_type: `{package['change_type']}`",
                    f"- target_sha256: `{package['target_sha256']}`",
                    f"- apply_requires_explicit_confirmation: `{str(package['apply_requires_explicit_confirmation']).lower()}`",
                    "- preflight_checks:",
                    *render_list(package.get("preflight_checks", [])),
                    "- proposed_operations:",
                    *render_list(package.get("proposed_operations", [])),
                    "- rollback_notes:",
                    *render_list(package.get("rollback_notes", [])),
                    "",
                ]
            )
    return "\n".join(lines).rstrip() + "\n"


def write_outputs(root: Path, new_packages: list[dict]) -> dict[str, Path]:
    merged = sorted(new_packages, key=lambda item: (item.get("status", ""), item.get("change_type", ""), item.get("path", "")))
    markdown = packages_markdown_path(root)
    jsonl = packages_jsonl_path(root)
    markdown.parent.mkdir(parents=True, exist_ok=True)
    jsonl.parent.mkdir(parents=True, exist_ok=True)
    markdown.write_text(render_markdown(root, merged), encoding="utf-8")
    jsonl.write_text("".join(json.dumps(package, ensure_ascii=False, sort_keys=True) + "\n" for package in merged), encoding="utf-8")
    return {"markdown": markdown, "jsonl": jsonl}


def print_summary(packages: list[dict]) -> None:
    counts: dict[str, int] = defaultdict(int)
    for package in packages:
        counts[package.get("status", "unknown")] += 1
    print(f"package_count: {len(packages)}")
    for key in sorted(counts):
        print(f"{key}: {counts[key]}")
    for package in packages[:20]:
        print(f"- {package.get('change_type')} `{package.get('path')}`: {package.get('status')}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate and list ready-to-apply maintenance package previews.")
    parser.add_argument("--root", required=True)
    subparsers = parser.add_subparsers(dest="action", required=True)
    generate = subparsers.add_parser("generate", help="Generate apply package previews from ready-to-apply drafts")
    generate.add_argument("--write", action="store_true", help="Write maintenance apply package reports")
    subparsers.add_parser("list", help="List existing maintenance apply packages")
    args = parser.parse_args()

    root = Path(args.root)
    if args.action == "generate":
        packages = generate_packages(root)
        print_summary(packages)
        if args.write:
            outputs = write_outputs(root, packages)
            print(f"wrote_markdown: {outputs['markdown']}")
            print(f"wrote_jsonl: {outputs['jsonl']}")
    elif args.action == "list":
        print_summary(all_packages(root))


if __name__ == "__main__":
    main()
