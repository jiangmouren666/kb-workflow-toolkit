#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path


SCHEMA = "knowledge-maintenance-task-v1"
ACTIONABLE_DECISIONS = {
    "accepted_for_review": "manual_knowledge_review",
    "needs_more_evidence": "evidence_collection",
    "converted_to_task": "external_task",
}
PRIORITY_BY_TASK_TYPE = {
    "evidence_collection": "high",
    "manual_knowledge_review": "medium",
    "external_task": "medium",
}


def review_registry_path(root: Path) -> Path:
    return root / "00-global" / "improvement-review-registry.md"


def tasks_markdown_path(root: Path) -> Path:
    return root / "00-global" / "maintenance-tasks.md"


def tasks_jsonl_path(root: Path) -> Path:
    return root / "00-global" / "state" / "maintenance-tasks.jsonl"


def task_id(candidate_id: str, decision: str, path: str) -> str:
    raw = "\n".join([candidate_id, decision, path])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


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


def existing_task_ids(root: Path) -> set[str]:
    return {row.get("task_id", "") for row in read_jsonl(tasks_jsonl_path(root))}


def verification_for(task_type: str) -> str:
    return {
        "manual_knowledge_review": "Human review should confirm scope, status proposal, and boundary before any note edit.",
        "evidence_collection": "Collect official docs, source code, experiment, backtest, or production evidence before trust changes.",
        "external_task": "Track externally and bring results back as evidence before editing knowledge status.",
    }.get(task_type, "Human verification required before any knowledge change.")


def task_from_entry(entry: dict) -> dict | None:
    decision = entry.get("decision", "")
    task_type = ACTIONABLE_DECISIONS.get(decision)
    if not task_type:
        return None
    path = entry.get("path", "")
    cid = entry.get("candidate_id", "")
    return {
        "schema": SCHEMA,
        "task_id": task_id(cid, decision, path),
        "source_candidate_id": cid,
        "path": path,
        "task_type": task_type,
        "status": "open",
        "priority": PRIORITY_BY_TASK_TYPE.get(task_type, "medium"),
        "reason": entry.get("reason", ""),
        "recommended_action": entry.get("next_action", ""),
        "verification_needed": verification_for(task_type),
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }


def generate_tasks(root: Path) -> list[dict]:
    existing = existing_task_ids(root)
    tasks: list[dict] = []
    for entry in parse_review_registry(root):
        task = task_from_entry(entry)
        if not task or task["task_id"] in existing:
            continue
        tasks.append(task)
    return sorted(tasks, key=lambda item: (item["priority"], item["path"], item["task_type"]))


def all_tasks(root: Path) -> list[dict]:
    return sorted(read_jsonl(tasks_jsonl_path(root)), key=lambda item: (item.get("status", ""), item.get("priority", ""), item.get("path", "")))


def render_markdown(root: Path, tasks: list[dict]) -> str:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for task in tasks:
        grouped[task.get("task_type", "unknown")].append(task)
    lines = [
        "---",
        "type: maintenance",
        "domain: global",
        "status: draft",
        "confidence: high",
        "source: maintenance-tasks.py",
        f"updated: {date.today().isoformat()}",
        "---",
        "",
        "# Maintenance Tasks",
        "",
        f"- vault_root: `{root}`",
        f"- task_count: {len(tasks)}",
        "- policy: task queue only; do not auto-modify notes, registries, or trust status",
        "",
    ]
    for task_type in ("evidence_collection", "manual_knowledge_review", "external_task"):
        lines.extend([f"## {task_type}", ""])
        items = grouped.get(task_type, [])
        if not items:
            lines.extend(["- None", ""])
            continue
        for task in items:
            lines.extend(
                [
                    f"### `{task['path']}`",
                    "",
                    f"- task_id: `{task['task_id']}`",
                    f"- source_candidate_id: `{task['source_candidate_id']}`",
                    f"- status: `{task['status']}`",
                    f"- priority: `{task['priority']}`",
                    f"- reason: {task['reason']}",
                    f"- recommended_action: {task['recommended_action']}",
                    f"- verification_needed: {task['verification_needed']}",
                    "",
                ]
            )
    return "\n".join(lines).rstrip() + "\n"


def write_outputs(root: Path, new_tasks: list[dict]) -> dict[str, Path]:
    existing = read_jsonl(tasks_jsonl_path(root))
    by_id = {task.get("task_id", ""): task for task in existing}
    for task in new_tasks:
        by_id[task["task_id"]] = task
    merged = sorted(by_id.values(), key=lambda item: (item.get("priority", ""), item.get("path", ""), item.get("task_type", "")))
    markdown = tasks_markdown_path(root)
    jsonl = tasks_jsonl_path(root)
    markdown.parent.mkdir(parents=True, exist_ok=True)
    jsonl.parent.mkdir(parents=True, exist_ok=True)
    markdown.write_text(render_markdown(root, merged), encoding="utf-8")
    jsonl.write_text("".join(json.dumps(task, ensure_ascii=False, sort_keys=True) + "\n" for task in merged), encoding="utf-8")
    return {"markdown": markdown, "jsonl": jsonl}


def print_summary(tasks: list[dict]) -> None:
    counts: dict[str, int] = defaultdict(int)
    for task in tasks:
        counts[task.get("task_type", "unknown")] += 1
    print(f"task_count: {len(tasks)}")
    for key in sorted(counts):
        print(f"{key}: {counts[key]}")
    for task in tasks[:20]:
        print(f"- [{task.get('priority')}] {task.get('task_type')} `{task.get('path')}`: {task.get('recommended_action')}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate and list maintenance tasks from improvement review decisions.")
    parser.add_argument("--root", required=True)
    subparsers = parser.add_subparsers(dest="action", required=True)
    generate = subparsers.add_parser("generate", help="Generate maintenance tasks from review decisions")
    generate.add_argument("--write", action="store_true", help="Write maintenance task reports")
    subparsers.add_parser("list", help="List existing maintenance tasks")
    args = parser.parse_args()
    root = Path(args.root)
    if args.action == "generate":
        tasks = generate_tasks(root)
        print_summary(tasks)
        if args.write:
            outputs = write_outputs(root, tasks)
            print(f"wrote_markdown: {outputs['markdown']}")
            print(f"wrote_jsonl: {outputs['jsonl']}")
    elif args.action == "list":
        print_summary(all_tasks(root))


if __name__ == "__main__":
    main()
