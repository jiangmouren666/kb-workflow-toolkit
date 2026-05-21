#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path


def plans_jsonl_path(root: Path) -> Path:
    return root / "00-global" / "state" / "maintenance-apply-plans.jsonl"


def rollback_root(root: Path) -> Path:
    return root / "00-global" / "state" / "rollback"


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


def find_plan(root: Path, plan_id: str) -> dict | None:
    for plan in read_jsonl(plans_jsonl_path(root)):
        if plan.get("plan_id") == plan_id:
            return plan
    return None


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


def frontmatter_bounds(text: str) -> tuple[int, int] | None:
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end == -1:
        return None
    return 4, end


def frontmatter_keys(lines: list[str]) -> set[str]:
    return {line.split(":", 1)[0].strip() for line in lines if line and not line.startswith((" ", "-")) and ":" in line}


def patch_frontmatter(text: str, fields: dict[str, str], mode: str) -> str:
    bounds = frontmatter_bounds(text)
    if bounds is None:
        return text
    start, end = bounds
    lines = text[start:end].splitlines()
    keys = frontmatter_keys(lines)
    for key, value in fields.items():
        if mode == "missing_only" and key in keys:
            continue
        replaced = False
        for idx, line in enumerate(lines):
            if line.startswith(f"{key}:"):
                lines[idx] = f"{key}: {value}"
                replaced = True
                break
        if not replaced:
            lines.append(f"{key}: {value}")
            keys.add(key)
    return text[:start] + "\n".join(lines) + text[end:]


def append_review_note(text: str, plan: dict) -> str:
    marker = f"plan_id: {plan.get('plan_id', '')}"
    if marker in text and "## Maintenance Review" in text:
        return text
    lines = [
        "",
        "## Maintenance Review",
        "",
        f"- plan_id: {plan.get('plan_id', '')}",
        f"- reviewed_at: {datetime.now().isoformat(timespec='seconds')}",
        f"- source_candidate_id: {plan.get('source_candidate_id', '')}",
        "- evidence_requirements:",
    ]
    for item in plan.get("evidence_requirements", []):
        lines.append(f"  - {item}")
    lines.extend(["- note: Applied by checksum-gated maintenance workflow.", ""])
    return text.rstrip() + "\n" + "\n".join(lines)


def scaffold_text(title: str, source_path: str, plan_id: str) -> str:
    today = datetime.now().date().isoformat()
    return (
        "---\n"
        "type: note\n"
        "status: draft\n"
        "confidence: low\n"
        "evidence_level: source_claim\n"
        "source: maintenance-apply\n"
        f"ingested: {today}\n"
        f"updated: {today}\n"
        "use_for:\n"
        "  - split_draft\n"
        "scope: scaffold created from a checksum-gated maintenance apply plan\n"
        "should_not_use_for: treating this scaffold as reviewed or verified knowledge\n"
        "time_sensitivity: medium\n"
        "review_cycle: 180d\n"
        "---\n\n"
        f"# {title}\n\n"
        f"Source note: [[{Path(source_path).with_suffix('').as_posix()}]]\n\n"
        f"Apply plan: `{plan_id}`\n\n"
        "## Draft Notes\n\n"
        "- Add reviewed split content here.\n"
    )


def apply_operations(root: Path, target: Path, plan: dict) -> list[str]:
    operations = plan.get("safe_operations") or []
    applied: list[str] = []
    text = target.read_text(encoding="utf-8")
    new_text = text
    for operation in operations:
        op = operation.get("operation")
        if op == "metadata_patch":
            new_text = patch_frontmatter(new_text, operation.get("fields", {}), operation.get("mode", "replace"))
            applied.append("metadata_patch")
        elif op == "append_review_note":
            new_text = append_review_note(new_text, plan)
            applied.append("append_review_note")
        elif op == "split_draft_scaffold":
            for scaffold in operation.get("scaffolds", []):
                relpath = scaffold.get("path", "")
                scaffold_target = safe_target_path(root, relpath)
                if scaffold_target is None:
                    continue
                if not scaffold_target.exists():
                    scaffold_target.parent.mkdir(parents=True, exist_ok=True)
                    scaffold_target.write_text(
                        scaffold_text(scaffold.get("title", Path(relpath).stem), plan.get("path", ""), plan.get("plan_id", "")),
                        encoding="utf-8",
                    )
            applied.append("split_draft_scaffold")
    if new_text != text:
        target.write_text(new_text, encoding="utf-8")
    return applied


def save_rollback(root: Path, target: Path, plan: dict, before_sha: str) -> Path:
    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    rel = target.relative_to(root)
    directory = rollback_root(root) / stamp
    backup = directory / rel
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(target, backup)
    manifest = {
        "schema": "knowledge-maintenance-rollback-v1",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "plan_id": plan.get("plan_id", ""),
        "path": rel.as_posix(),
        "target_before_sha256": before_sha,
        "backup": backup.relative_to(root).as_posix(),
    }
    manifest_path = directory / "rollback-manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest_path


def apply_plan(root: Path, plan_id: str, write: bool = False, confirm: str = "") -> dict:
    root = root.resolve()
    plan = find_plan(root, plan_id)
    if plan is None:
        return {"status": "blocked_missing_plan", "plan_id": plan_id}
    if plan.get("status") != "ready_preview":
        return {"status": "blocked_plan_not_ready", "plan_id": plan_id}
    target = safe_target_path(root, plan.get("path", ""))
    if target is None:
        return {"status": "blocked_invalid_target_path", "plan_id": plan_id}
    if not target.exists():
        return {"status": "blocked_missing_target", "plan_id": plan_id}
    current_sha = sha256(target)
    if current_sha != plan.get("target_sha256"):
        return {"status": "blocked_target_sha256_mismatch", "plan_id": plan_id, "current_sha256": current_sha, "expected_sha256": plan.get("target_sha256", "")}
    if not write:
        return {"status": "dry_run", "plan_id": plan_id, "operation_count": len(plan.get("safe_operations") or [])}
    if confirm != plan_id:
        return {"status": "blocked_missing_confirmation", "plan_id": plan_id}
    rollback_manifest = save_rollback(root, target, plan, current_sha)
    applied = apply_operations(root, target, plan)
    return {
        "status": "applied",
        "plan_id": plan_id,
        "applied_operations": applied,
        "target_after_sha256": sha256(target),
        "rollback_manifest": rollback_manifest.as_posix(),
    }


def print_result(result: dict) -> None:
    print(f"apply_status: {result.get('status')}")
    for key, value in result.items():
        if key == "status":
            continue
        if isinstance(value, list):
            print(f"{key}: {len(value)}")
            for item in value:
                print(f"- {item}")
        else:
            print(f"{key}: {value}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply checksum-gated maintenance plans with rollback snapshots.")
    parser.add_argument("--root", required=True)
    parser.add_argument("--plan-id", required=True)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--confirm", default="", help="Must match --plan-id when --write is used.")
    args = parser.parse_args()

    print_result(apply_plan(Path(args.root), args.plan_id, write=args.write, confirm=args.confirm))


if __name__ == "__main__":
    main()
