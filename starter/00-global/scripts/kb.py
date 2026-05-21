#!/usr/bin/env python3
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterator


TRACKED_SUFFIXES = {".md", ".py"}
EXCLUDED_PARTS = {".git", "__pycache__", "audit-reports", "state"}
LOCK_TTL = timedelta(hours=2)
LEGACY_REVERSE_SYNC_SCRIPT = Path("/usr/local/bin/sync-vaults.sh")
DOMAIN_DIRS = (
    "00-global",
    "quant",
    "ai-agent",
    "machine-learning",
    "programming",
    "framework-optimization",
    "fiction-reasoning",
    "education",
)


def scripts_dir(root: Path) -> Path:
    return root / "00-global" / "scripts"


def state_dir(root: Path) -> Path:
    return root / "00-global" / "state"


def default_vault_root() -> Path:
    return Path(__file__).resolve().parents[2]


def vault_config_path(root: Path) -> Path:
    return state_dir(root) / "vault-config.json"


def snapshots_dir(root: Path) -> Path:
    return state_dir(root) / "snapshots"


def current_manifest_path(root: Path) -> Path:
    return state_dir(root) / "current-manifest.json"


def auto_sync_config_path(root: Path) -> Path:
    return state_dir(root) / "auto-sync.json"


def protected_manifest_path(root: Path) -> Path:
    return state_dir(root) / "protected-files.json"


def protected_baseline_dir(root: Path) -> Path:
    return state_dir(root) / "protected-files"


def lock_path(root: Path) -> Path:
    return state_dir(root) / "kb.lock"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tracked_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if any(part in EXCLUDED_PARTS for part in rel.parts):
            continue
        if path.suffix not in TRACKED_SUFFIXES:
            continue
        files.append(path)
    return files


def build_manifest(root: Path) -> dict:
    files = {}
    for path in tracked_files(root):
        rel = path.relative_to(root).as_posix()
        stat = path.stat()
        files[rel] = {
            "sha256": sha256(path),
            "size": stat.st_size,
            "mtime_ns": stat.st_mtime_ns,
        }
    return {
        "schema": "knowledge-vault-manifest-v1",
        "root": str(root),
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "file_count": len(files),
        "files": files,
    }


def diff_manifests(old: dict, new: dict) -> dict[str, list[str]]:
    old_files = old.get("files", {})
    new_files = new.get("files", {})
    old_keys = set(old_files)
    new_keys = set(new_files)
    common = old_keys & new_keys
    return {
        "added": sorted(new_keys - old_keys),
        "modified": sorted(path for path in common if old_files[path].get("sha256") != new_files[path].get("sha256")),
        "deleted": sorted(old_keys - new_keys),
    }


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def base_vault_config(root: Path, sync_target: Path | str = "", sync_enabled: bool = False) -> dict:
    now = datetime.now().isoformat(timespec="seconds")
    return {
        "schema": "knowledge-vault-config-v1",
        "schema_version": 1,
        "vault_root": str(root),
        "sync_enabled": sync_enabled,
        "sync_target": str(sync_target) if sync_target else "",
        "created_at": now,
        "updated_at": now,
    }


def load_vault_config(root: Path) -> dict:
    path = vault_config_path(root)
    if not path.exists():
        return base_vault_config(root)
    return load_json(path)


def save_vault_config(root: Path, config: dict) -> Path:
    current = load_vault_config(root)
    merged = {**current, **config}
    merged["schema"] = "knowledge-vault-config-v1"
    merged["schema_version"] = 1
    merged["vault_root"] = str(root)
    merged["updated_at"] = datetime.now().isoformat(timespec="seconds")
    if not merged.get("created_at"):
        merged["created_at"] = merged["updated_at"]
    write_json(vault_config_path(root), merged)
    return vault_config_path(root)


def create_base_directories(root: Path) -> None:
    for domain in DOMAIN_DIRS:
        (root / domain).mkdir(parents=True, exist_ok=True)
    for domain in DOMAIN_DIRS:
        if domain == "00-global":
            continue
        (root / domain / "10-standards").mkdir(parents=True, exist_ok=True)
        (root / domain / "20-notes").mkdir(parents=True, exist_ok=True)
    for rel in ("00-global/scripts", "00-global/evaluation", "00-global/state"):
        (root / rel).mkdir(parents=True, exist_ok=True)


def copy_runtime_templates(root: Path, template_root: Path | None = None) -> None:
    source_root = template_root or default_vault_root()
    if source_root.resolve() == root.resolve():
        return
    for rel in ("00-global/scripts", "00-global/evaluation"):
        source_dir = source_root / rel
        target_dir = root / rel
        if not source_dir.exists():
            continue
        target_dir.mkdir(parents=True, exist_ok=True)
        for source in source_dir.iterdir():
            if not source.is_file() or source.suffix != ".py":
                continue
            shutil.copy2(source, target_dir / source.name)


def init_vault(root: Path, sync_target: Path | None = None, sync_enabled: bool = False, template_root: Path | None = None) -> dict:
    root = root.expanduser().resolve()
    create_base_directories(root)
    copy_runtime_templates(root, template_root=template_root)
    config = base_vault_config(root, sync_target or "", sync_enabled=sync_enabled)
    save_vault_config(root, config)
    save_auto_sync_config(root, Path(sync_target or ""), enabled=sync_enabled)
    return load_vault_config(root)


def configure_vault(root: Path, sync_target: Path | None = None, sync_enabled: bool | None = None) -> dict:
    root = root.expanduser().resolve()
    create_base_directories(root)
    current = load_vault_config(root)
    updates: dict = {}
    if sync_target is not None:
        updates["sync_target"] = str(sync_target.expanduser().resolve())
    if sync_enabled is not None:
        updates["sync_enabled"] = sync_enabled
    save_vault_config(root, updates)
    updated = load_vault_config(root)
    save_auto_sync_config(root, Path(updated.get("sync_target") or ""), enabled=bool(updated.get("sync_enabled")))
    return updated


def default_protected_paths(root: Path) -> list[Path]:
    relpaths = [
        "00-global/scripts/kb.py",
        "00-global/scripts/build-starter.py",
        "00-global/scripts/improvement-loop.py",
        "00-global/scripts/improvement-review.py",
        "00-global/scripts/maintenance-tasks.py",
        "00-global/scripts/maintenance-proposals.py",
        "00-global/scripts/maintenance-proposal-review.py",
        "00-global/scripts/maintenance-change-drafts.py",
        "00-global/scripts/maintenance-change-draft-review.py",
        "00-global/scripts/maintenance-apply-packages.py",
        "00-global/scripts/maintenance-apply-plans.py",
        "00-global/scripts/sync-vault.py",
        "00-global/scripts/scan-vault-strict.py",
        "00-global/scripts/apply-registry-overlay.py",
        "00-global/scripts/test_kb.py",
        "00-global/scripts/test_build_starter.py",
        "00-global/scripts/test_improvement_loop.py",
        "00-global/scripts/test_improvement_review.py",
        "00-global/scripts/test_maintenance_tasks.py",
        "00-global/scripts/test_maintenance_proposals.py",
        "00-global/scripts/test_maintenance_proposal_review.py",
        "00-global/scripts/test_maintenance_change_drafts.py",
        "00-global/scripts/test_maintenance_change_draft_review.py",
        "00-global/scripts/test_maintenance_apply_packages.py",
        "00-global/scripts/test_maintenance_apply_plans.py",
        "00-global/scripts/test_sync_vault.py",
        "00-global/evaluation/context_pack_builder_v2.py",
        "00-global/evaluation/test_context_pack_builder_v2.py",
        "00-global/evaluation/run_abc_smoke_test_v3.py",
        "00-global/evaluation/test_run_abc_smoke_test.py",
        "00-global/evaluation/run_context_format_eval_v2.py",
        "00-global/evaluation/test_run_context_format_eval_v2.py",
    ]
    return [root / rel for rel in relpaths if (root / rel).exists()]


def capture_protected_files(root: Path, paths: list[Path] | None = None) -> dict:
    selected = paths or default_protected_paths(root)
    baseline = protected_baseline_dir(root)
    files = {}
    for path in selected:
        rel = path.relative_to(root).as_posix()
        target = baseline / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        files[rel] = {"sha256": sha256(path), "size": path.stat().st_size}
    manifest = {
        "schema": "knowledge-vault-protected-files-v1",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "files": files,
    }
    write_json(protected_manifest_path(root), manifest)
    return manifest


def protected_file_drift(root: Path) -> dict[str, list[str]]:
    manifest_path = protected_manifest_path(root)
    if not manifest_path.exists():
        return {"missing_baseline": [], "modified": [], "deleted": []}
    manifest = load_json(manifest_path)
    missing_baseline: list[str] = []
    modified: list[str] = []
    deleted: list[str] = []
    for rel, info in manifest.get("files", {}).items():
        path = root / rel
        baseline = protected_baseline_dir(root) / rel
        if not baseline.exists():
            missing_baseline.append(rel)
            continue
        if not path.exists():
            deleted.append(rel)
            continue
        if sha256(path) != info.get("sha256"):
            modified.append(rel)
    return {
        "missing_baseline": sorted(missing_baseline),
        "modified": sorted(modified),
        "deleted": sorted(deleted),
    }


def restore_protected_files(root: Path) -> dict[str, list[str]]:
    manifest = load_json(protected_manifest_path(root))
    restored: list[str] = []
    missing_baseline: list[str] = []
    for rel in manifest.get("files", {}):
        baseline = protected_baseline_dir(root) / rel
        target = root / rel
        if not baseline.exists():
            missing_baseline.append(rel)
            continue
        if not target.exists() or sha256(target) != sha256(baseline):
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(baseline, target)
            restored.append(rel)
    return {"restored": sorted(restored), "missing_baseline": sorted(missing_baseline)}


def legacy_reverse_sync_script_status(script: Path = LEGACY_REVERSE_SYNC_SCRIPT) -> str:
    if not script.exists():
        return "missing"
    text = script.read_text(encoding="utf-8", errors="replace")
    if "stale Obsidian-to-local writeback" in text and "exit 2" in text:
        return "disabled"
    if 'rsync -av' in text and '"$OBSIDIAN/" "$LOCAL/"' in text:
        return "unsafe"
    return "unknown"


def sync_target_status(target: Path) -> str:
    if not str(target):
        return "not_configured"
    if not target.exists():
        return "missing"
    for candidate in [target, *target.parents]:
        if os.path.ismount(candidate):
            return "available"
    return "unmounted"


def sync_safety_status(root: Path, legacy_script: Path = LEGACY_REVERSE_SYNC_SCRIPT) -> dict:
    drift = protected_file_drift(root)
    vault_config = load_vault_config(root)
    auto_config = load_auto_sync_config(root)
    target_value = vault_config.get("sync_target") or auto_config.get("target") or ""
    sync_enabled = bool(vault_config.get("sync_enabled") or auto_config.get("enabled"))
    target = Path(target_value) if target_value else Path("")
    return {
        "source_of_truth": str(root),
        "sync_direction": "local_to_optional_target_only",
        "auto_sync_enabled": sync_enabled,
        "auto_sync_target": target_value,
        "auto_sync_target_status": sync_target_status(target),
        "protected_file_drift": sum(len(items) for items in drift.values()),
        "legacy_reverse_sync_script": legacy_reverse_sync_script_status(legacy_script),
    }


def load_auto_sync_config(root: Path) -> dict:
    path = auto_sync_config_path(root)
    if not path.exists():
        return {"enabled": False, "target": ""}
    return load_json(path)


def save_auto_sync_config(root: Path, target: Path | str | None, enabled: bool = True) -> Path:
    path = auto_sync_config_path(root)
    target_value = str(target) if target else ""
    if target_value == ".":
        target_value = ""
    write_json(
        path,
        {
            "enabled": enabled,
            "target": target_value,
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        },
    )
    return path


def latest_snapshot(root: Path) -> Path | None:
    directory = snapshots_dir(root)
    if not directory.exists():
        return None
    snapshots = sorted(directory.glob("*-manifest.json"))
    return snapshots[-1] if snapshots else None


def save_snapshot(root: Path) -> Path:
    manifest = build_manifest(root)
    now = datetime.now().strftime("%Y%m%d-%H%M%S")
    snapshot_path = snapshots_dir(root) / f"{now}-manifest.json"
    write_json(snapshot_path, manifest)
    write_json(current_manifest_path(root), manifest)
    return snapshot_path


def print_diff(diff: dict[str, list[str]]) -> None:
    for key in ("added", "modified", "deleted"):
        items = diff.get(key, [])
        print(f"{key}: {len(items)}")
        for item in items:
            print(f"- {item}")


def is_lock_active(lock: Path) -> bool:
    if not lock.exists():
        return False
    try:
        data = load_json(lock)
        created_at = datetime.fromisoformat(data.get("created_at", ""))
    except Exception:
        return True
    return datetime.now() - created_at < LOCK_TTL


@contextlib.contextmanager
def acquire_lock(root: Path) -> Iterator[None]:
    path = lock_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    if is_lock_active(path):
        raise SystemExit(f"active lock exists: {path}")
    path.write_text(
        json.dumps(
            {
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "pid": os.getpid(),
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    try:
        yield
    finally:
        if path.exists():
            path.unlink()


def run_script(root: Path, script_name: str, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    script = scripts_dir(root) / script_name
    cmd = [sys.executable, str(script), *args]
    return subprocess.run(cmd, text=True, capture_output=True, check=check)


def run_auto_sync(root: Path, reason: str) -> None:
    config = load_auto_sync_config(root)
    if not config.get("enabled"):
        return
    drift = protected_file_drift(root)
    drift_count = sum(len(items) for items in drift.values())
    if drift_count:
        print(f"auto_sync: skipped (protected file drift: {drift_count})")
        return
    target = config.get("target")
    if not target:
        print("auto_sync: disabled (no target)")
        return
    target_path = Path(target)
    if not target_path.exists():
        print(f"auto_sync: skipped (target missing: {target_path})")
        return

    scan = run_script(root, "scan-vault-strict.py", "--root", str(root))
    total, overlays = scan_summary(scan.stdout)
    if total not in (0, None):
        print(f"auto_sync: skipped (scan findings: {total})")
        return
    if overlays:
        print(f"auto_sync: skipped (registry overlay applied: {overlays})")
        return

    result = run_script(root, "sync-vault.py", "--source", str(root), "--target", str(target_path), "--write")
    print(f"auto_sync: {reason}")
    print(result.stdout, end="")


def command_scan(args: argparse.Namespace) -> None:
    root = Path(args.root)
    result = run_script(root, "scan-vault-strict.py", "--root", str(root), *(["--write"] if args.write else []))
    print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, file=sys.stderr, end="")


def print_vault_config(config: dict) -> None:
    for key in ("vault_root", "sync_enabled", "sync_target", "schema_version", "created_at", "updated_at"):
        print(f"{key}: {config.get(key, '')}")


def command_init(args: argparse.Namespace) -> None:
    root = Path(args.root)
    sync_target = Path(args.sync_target) if args.sync_target else None
    config = init_vault(root, sync_target=sync_target, sync_enabled=args.enable_sync)
    print("vault_initialized: true")
    print_vault_config(config)
    print(f"config: {vault_config_path(Path(config['vault_root']))}")


def command_configure(args: argparse.Namespace) -> None:
    root = Path(args.root)
    sync_enabled = None
    if args.enable_sync:
        sync_enabled = True
    elif args.disable_sync:
        sync_enabled = False
    sync_target = Path(args.sync_target) if args.sync_target else None
    config = configure_vault(root, sync_target=sync_target, sync_enabled=sync_enabled)
    print("vault_configured: true")
    print_vault_config(config)
    print(f"config: {vault_config_path(Path(config['vault_root']))}")


def command_repair(args: argparse.Namespace) -> None:
    root = Path(args.root)
    script_args = ["--root", str(root)]
    if args.write:
        script_args.append("--write")
        with acquire_lock(root):
            before = build_manifest(root)
            result = run_script(root, "apply-registry-overlay.py", *script_args)
            after = build_manifest(root)
            print(result.stdout, end="")
            print_write_diff(before, after)
            run_auto_sync(root, "after repair")
        return
    result = run_script(root, "apply-registry-overlay.py", *script_args)
    print(result.stdout, end="")


def command_improve(args: argparse.Namespace) -> None:
    root = Path(args.root)
    script_args = ["--root", str(root)]
    if args.write:
        script_args.append("--write")
        with acquire_lock(root):
            before = build_manifest(root)
            result = run_script(root, "improvement-loop.py", *script_args)
            after = build_manifest(root)
            print(result.stdout, end="")
            print_write_diff(before, after)
            run_auto_sync(root, "after improvement candidates")
        return
    result = run_script(root, "improvement-loop.py", *script_args)
    print(result.stdout, end="")


def command_review_improvements(args: argparse.Namespace) -> None:
    root = Path(args.root)
    script_args = ["--root", str(root), "--limit", str(args.limit)]
    if args.decisions:
        script_args.extend(["--decisions", args.decisions])
    if args.note:
        script_args.extend(["--note", args.note])
    if args.decisions:
        with acquire_lock(root):
            before = build_manifest(root)
            result = run_script(root, "improvement-review.py", *script_args)
            after = build_manifest(root)
            print(result.stdout, end="")
            print_write_diff(before, after)
            run_auto_sync(root, "after improvement review")
        return
    result = run_script(root, "improvement-review.py", *script_args)
    print(result.stdout, end="")


def command_tasks(args: argparse.Namespace) -> None:
    root = Path(args.root)
    script_args = ["--root", str(root), args.action]
    if args.action == "generate" and args.write:
        script_args.append("--write")
        with acquire_lock(root):
            before = build_manifest(root)
            result = run_script(root, "maintenance-tasks.py", *script_args)
            after = build_manifest(root)
            print(result.stdout, end="")
            print_write_diff(before, after)
            run_auto_sync(root, "after maintenance tasks")
        return
    result = run_script(root, "maintenance-tasks.py", *script_args)
    print(result.stdout, end="")


def command_proposals(args: argparse.Namespace) -> None:
    root = Path(args.root)
    script_args = ["--root", str(root), args.action]
    if args.action == "generate" and args.write:
        script_args.append("--write")
        with acquire_lock(root):
            before = build_manifest(root)
            result = run_script(root, "maintenance-proposals.py", *script_args)
            after = build_manifest(root)
            print(result.stdout, end="")
            print_write_diff(before, after)
            run_auto_sync(root, "after maintenance proposals")
        return
    result = run_script(root, "maintenance-proposals.py", *script_args)
    print(result.stdout, end="")


def command_review_proposals(args: argparse.Namespace) -> None:
    root = Path(args.root)
    script_args = ["--root", str(root), "--limit", str(args.limit)]
    if args.decisions:
        script_args.extend(["--decisions", args.decisions])
    if args.note:
        script_args.extend(["--note", args.note])
    if args.decisions:
        with acquire_lock(root):
            before = build_manifest(root)
            result = run_script(root, "maintenance-proposal-review.py", *script_args)
            after = build_manifest(root)
            print(result.stdout, end="")
            print_write_diff(before, after)
            run_auto_sync(root, "after maintenance proposal review")
        return
    result = run_script(root, "maintenance-proposal-review.py", *script_args)
    print(result.stdout, end="")


def command_change_drafts(args: argparse.Namespace) -> None:
    root = Path(args.root)
    script_args = ["--root", str(root), args.action]
    if args.action == "generate" and args.write:
        script_args.append("--write")
        with acquire_lock(root):
            before = build_manifest(root)
            result = run_script(root, "maintenance-change-drafts.py", *script_args)
            after = build_manifest(root)
            print(result.stdout, end="")
            print_write_diff(before, after)
            run_auto_sync(root, "after maintenance change drafts")
        return
    result = run_script(root, "maintenance-change-drafts.py", *script_args)
    print(result.stdout, end="")


def command_review_change_drafts(args: argparse.Namespace) -> None:
    root = Path(args.root)
    script_args = ["--root", str(root), "--limit", str(args.limit)]
    if args.decisions:
        script_args.extend(["--decisions", args.decisions])
    if args.note:
        script_args.extend(["--note", args.note])
    if args.decisions:
        with acquire_lock(root):
            before = build_manifest(root)
            result = run_script(root, "maintenance-change-draft-review.py", *script_args)
            after = build_manifest(root)
            print(result.stdout, end="")
            print_write_diff(before, after)
            run_auto_sync(root, "after maintenance change draft review")
        return
    result = run_script(root, "maintenance-change-draft-review.py", *script_args)
    print(result.stdout, end="")


def command_apply_packages(args: argparse.Namespace) -> None:
    root = Path(args.root)
    script_args = ["--root", str(root), args.action]
    if args.action == "generate" and args.write:
        script_args.append("--write")
        with acquire_lock(root):
            before = build_manifest(root)
            result = run_script(root, "maintenance-apply-packages.py", *script_args)
            after = build_manifest(root)
            print(result.stdout, end="")
            print_write_diff(before, after)
            run_auto_sync(root, "after maintenance apply packages")
        return
    result = run_script(root, "maintenance-apply-packages.py", *script_args)
    print(result.stdout, end="")


def command_maintain(args: argparse.Namespace) -> None:
    root = Path(args.root)
    if args.action == "apply":
        print("apply_status: not_implemented")
        print(f"plan_id: {args.plan_id}")
        print("policy: P10 apply is a safe stub; no note is modified")
        return

    script_action = "generate" if args.action == "plan" else args.action
    script_args = ["--root", str(root), script_action]
    if args.action == "plan" and args.write:
        script_args.append("--write")
        with acquire_lock(root):
            before = build_manifest(root)
            result = run_script(root, "maintenance-apply-plans.py", *script_args)
            after = build_manifest(root)
            print(result.stdout, end="")
            print_write_diff(before, after)
            run_auto_sync(root, "after consolidated maintenance apply plans")
        return
    result = run_script(root, "maintenance-apply-plans.py", *script_args)
    print(result.stdout, end="")


def print_write_diff(before: dict, after: dict) -> None:
    diff = diff_manifests(before, after)
    changed_count = sum(len(items) for items in diff.values())
    print(f"write_changed_files: {changed_count}")
    if changed_count:
        print_diff(diff)


def command_snapshot(args: argparse.Namespace) -> None:
    root = Path(args.root)
    with acquire_lock(root):
        snapshot_path = save_snapshot(root)
        run_auto_sync(root, "after snapshot")
    manifest = load_json(snapshot_path)
    print(f"snapshot: {snapshot_path}")
    print(f"file_count: {manifest['file_count']}")


def command_diff(args: argparse.Namespace) -> None:
    root = Path(args.root)
    snapshot = latest_snapshot(root)
    if snapshot is None:
        raise SystemExit("no snapshot found; run `kb.py snapshot` first")
    old = load_json(snapshot)
    new = build_manifest(root)
    print(f"baseline: {snapshot}")
    print_diff(diff_manifests(old, new))


def scan_summary(text: str) -> tuple[int | None, int]:
    total_findings: int | None = None
    overlay_count = 0
    in_overlay = False
    for line in text.splitlines():
        if line.startswith("- total_findings:"):
            total_findings = int(line.split(":", 1)[1].strip())
        elif line == "## Registry Overlay Applied":
            in_overlay = True
        elif line.startswith("## ") and line != "## Registry Overlay Applied":
            in_overlay = False
        elif in_overlay and line.startswith("- `"):
            overlay_count += 1
    return total_findings, overlay_count


def command_status(args: argparse.Namespace) -> None:
    root = Path(args.root)
    result = run_script(root, "scan-vault-strict.py", "--root", str(root))
    total, overlays = scan_summary(result.stdout)
    print(f"vault_root: {root}")
    print(f"total_findings: {total if total is not None else 'unknown'}")
    print(f"registry_overlay_applied: {overlays}")
    snapshot = latest_snapshot(root)
    if snapshot is None:
        print("manifest_drift: no snapshot")
        return
    diff = diff_manifests(load_json(snapshot), build_manifest(root))
    drift_count = sum(len(items) for items in diff.values())
    print(f"manifest_baseline: {snapshot}")
    print(f"manifest_drift: {drift_count}")


def command_sync(args: argparse.Namespace) -> None:
    root = Path(args.root)
    scan = run_script(root, "scan-vault-strict.py", "--root", str(root))
    total, overlays = scan_summary(scan.stdout)
    print(f"pre_sync_total_findings: {total if total is not None else 'unknown'}")
    print(f"pre_sync_registry_overlay_applied: {overlays}")

    script_args = ["--source", str(root), "--target", args.target]
    if args.write:
        script_args.append("--write")
        with acquire_lock(root):
            result = run_script(root, "sync-vault.py", *script_args)
    else:
        result = run_script(root, "sync-vault.py", *script_args)
    print(result.stdout, end="")


def command_autosync(args: argparse.Namespace) -> None:
    root = Path(args.root)
    if args.action == "enable":
        target = Path(args.target)
        if not target.exists():
            raise SystemExit(f"target does not exist: {target}")
        path = save_auto_sync_config(root, target, enabled=True)
        save_vault_config(root, {"sync_target": str(target), "sync_enabled": True})
        print(f"auto_sync_enabled: {target}")
        print(f"config: {path}")
    elif args.action == "disable":
        config = load_auto_sync_config(root)
        target = Path(config.get("target") or "")
        path = save_auto_sync_config(root, target, enabled=False)
        save_vault_config(root, {"sync_enabled": False, "sync_target": config.get("target") or ""})
        print("auto_sync_enabled: false")
        print(f"config: {path}")
    elif args.action == "status":
        config = load_auto_sync_config(root)
        print(f"auto_sync_enabled: {bool(config.get('enabled'))}")
        print(f"target: {config.get('target') or ''}")
    elif args.action == "run":
        with acquire_lock(root):
            run_auto_sync(root, "manual run")


def command_doctor(args: argparse.Namespace) -> None:
    root = Path(args.root)
    status_args = argparse.Namespace(root=str(root))
    command_status(status_args)
    print("")
    print("diff:")
    try:
        command_diff(status_args)
    except SystemExit as exc:
        print(exc)
    print("")
    print("repair_dry_run:")
    command_repair(argparse.Namespace(root=str(root), write=False))


def print_protected_drift(drift: dict[str, list[str]]) -> None:
    for key in ("missing_baseline", "modified", "deleted"):
        items = drift.get(key, [])
        print(f"{key}: {len(items)}")
        for item in items:
            print(f"- {item}")


def command_protect(args: argparse.Namespace) -> None:
    root = Path(args.root)
    if args.action == "capture":
        with acquire_lock(root):
            manifest = capture_protected_files(root)
        print(f"protected_files_captured: {len(manifest.get('files', {}))}")
        print(f"manifest: {protected_manifest_path(root)}")
    elif args.action == "status":
        print_protected_drift(protected_file_drift(root))
    elif args.action == "restore":
        with acquire_lock(root):
            result = restore_protected_files(root)
        print(f"restored: {len(result.get('restored', []))}")
        for item in result.get("restored", []):
            print(f"- {item}")
        if result.get("missing_baseline"):
            print(f"missing_baseline: {len(result['missing_baseline'])}")
            for item in result["missing_baseline"]:
                print(f"- {item}")


def command_safety(args: argparse.Namespace) -> None:
    root = Path(args.root)
    status = sync_safety_status(root)
    for key in (
        "source_of_truth",
        "sync_direction",
        "auto_sync_enabled",
        "auto_sync_target",
        "auto_sync_target_status",
        "protected_file_drift",
        "legacy_reverse_sync_script",
    ):
        print(f"{key}: {status[key]}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Knowledge vault maintenance CLI")
    parser.add_argument("--root", default=str(default_vault_root()), help="Knowledge vault root")
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_root(subparser: argparse.ArgumentParser) -> None:
        subparser.add_argument("--root", default=argparse.SUPPRESS, help="Knowledge vault root")

    init = subparsers.add_parser("init", help="Initialize a local-first knowledge vault")
    add_root(init)
    init.add_argument("--sync-target", default="", help="Optional export/sync target")
    init.add_argument("--enable-sync", action="store_true", help="Enable local-to-target sync after init")
    init.set_defaults(func=command_init)

    configure = subparsers.add_parser("configure", help="Configure vault root and optional sync target")
    add_root(configure)
    configure.add_argument("--sync-target", default="", help="Optional export/sync target")
    sync_group = configure.add_mutually_exclusive_group()
    sync_group.add_argument("--enable-sync", action="store_true", help="Enable local-to-target sync")
    sync_group.add_argument("--disable-sync", action="store_true", help="Disable local-to-target sync")
    configure.set_defaults(func=command_configure)

    scan = subparsers.add_parser("scan", help="Run strict diagnostic scan")
    add_root(scan)
    scan.add_argument("--write", action="store_true", help="Write audit report and review queue")
    scan.set_defaults(func=command_scan)

    repair = subparsers.add_parser("repair", help="Apply human-review registry overlay")
    add_root(repair)
    repair.add_argument("--write", action="store_true", help="Actually repair frontmatter")
    repair.set_defaults(func=command_repair)

    improve = subparsers.add_parser("improve", help="Generate improvement candidates without changing notes")
    add_root(improve)
    improve.add_argument("--write", action="store_true", help="Write improvement candidate reports")
    improve.set_defaults(func=command_improve)

    review_improvements = subparsers.add_parser("review-improvements", help="Review improvement candidates and record decisions")
    add_root(review_improvements)
    review_improvements.add_argument("--limit", type=int, default=5, help="Number of candidates to show")
    review_improvements.add_argument("--decisions", default="", help='Compact decisions such as "1A 2C"')
    review_improvements.add_argument("--note", default="", help="Optional note stored with decisions")
    review_improvements.set_defaults(func=command_review_improvements)

    tasks = subparsers.add_parser("tasks", help="Generate or list maintenance tasks")
    add_root(tasks)
    tasks_sub = tasks.add_subparsers(dest="action", required=True)
    tasks_generate = tasks_sub.add_parser("generate", help="Generate tasks from improvement review decisions")
    add_root(tasks_generate)
    tasks_generate.add_argument("--write", action="store_true", help="Write maintenance task reports")
    tasks_generate.set_defaults(func=command_tasks)
    tasks_list = tasks_sub.add_parser("list", help="List existing maintenance tasks")
    add_root(tasks_list)
    tasks_list.set_defaults(func=command_tasks)

    proposals = subparsers.add_parser("proposals", help="Generate or list maintenance proposals")
    add_root(proposals)
    proposals_sub = proposals.add_subparsers(dest="action", required=True)
    proposals_generate = proposals_sub.add_parser("generate", help="Generate proposals from open maintenance tasks")
    add_root(proposals_generate)
    proposals_generate.add_argument("--write", action="store_true", help="Write maintenance proposal reports")
    proposals_generate.set_defaults(func=command_proposals)
    proposals_list = proposals_sub.add_parser("list", help="List existing maintenance proposals")
    add_root(proposals_list)
    proposals_list.set_defaults(func=command_proposals)

    review_proposals = subparsers.add_parser("review-proposals", help="Review maintenance proposals and record approval decisions")
    add_root(review_proposals)
    review_proposals.add_argument("--limit", type=int, default=5, help="Number of proposals to show")
    review_proposals.add_argument("--decisions", default="", help='Compact decisions such as "1A 2D"')
    review_proposals.add_argument("--note", default="", help="Optional reason stored with decisions")
    review_proposals.set_defaults(func=command_review_proposals)

    change_drafts = subparsers.add_parser("change-drafts", help="Generate or list approved maintenance change drafts")
    add_root(change_drafts)
    change_drafts_sub = change_drafts.add_subparsers(dest="action", required=True)
    change_drafts_generate = change_drafts_sub.add_parser("generate", help="Generate drafts from approved proposals")
    add_root(change_drafts_generate)
    change_drafts_generate.add_argument("--write", action="store_true", help="Write maintenance change draft reports")
    change_drafts_generate.set_defaults(func=command_change_drafts)
    change_drafts_list = change_drafts_sub.add_parser("list", help="List existing maintenance change drafts")
    add_root(change_drafts_list)
    change_drafts_list.set_defaults(func=command_change_drafts)

    review_change_drafts = subparsers.add_parser("review-change-drafts", help="Review maintenance change drafts and record final approval decisions")
    add_root(review_change_drafts)
    review_change_drafts.add_argument("--limit", type=int, default=5, help="Number of change drafts to show")
    review_change_drafts.add_argument("--decisions", default="", help='Compact decisions such as "1A 2D"')
    review_change_drafts.add_argument("--note", default="", help="Optional reason stored with decisions")
    review_change_drafts.set_defaults(func=command_review_change_drafts)

    apply_packages = subparsers.add_parser("apply-packages", help="Generate or list ready-to-apply package previews")
    add_root(apply_packages)
    apply_packages_sub = apply_packages.add_subparsers(dest="action", required=True)
    apply_packages_generate = apply_packages_sub.add_parser("generate", help="Generate apply package previews from ready change drafts")
    add_root(apply_packages_generate)
    apply_packages_generate.add_argument("--write", action="store_true", help="Write maintenance apply package reports")
    apply_packages_generate.set_defaults(func=command_apply_packages)
    apply_packages_list = apply_packages_sub.add_parser("list", help="List existing maintenance apply packages")
    add_root(apply_packages_list)
    apply_packages_list.set_defaults(func=command_apply_packages)

    maintain = subparsers.add_parser("maintain", help="Consolidated daily maintenance workflow")
    add_root(maintain)
    maintain_sub = maintain.add_subparsers(dest="action", required=True)
    maintain_status = maintain_sub.add_parser("status", help="Summarize maintenance candidates, reviews, and plans")
    add_root(maintain_status)
    maintain_status.set_defaults(func=command_maintain)
    maintain_plan = maintain_sub.add_parser("plan", help="Generate consolidated apply plan previews")
    add_root(maintain_plan)
    maintain_plan.add_argument("--write", action="store_true", help="Write consolidated apply plan reports")
    maintain_plan.set_defaults(func=command_maintain)
    maintain_apply = maintain_sub.add_parser("apply", help="Reserved apply workflow stub; does not modify notes in P10")
    add_root(maintain_apply)
    maintain_apply.add_argument("--plan-id", required=True, help="Apply plan ID to apply in a future workflow")
    maintain_apply.add_argument("--write", action="store_true", help="Reserved for future explicit apply workflow")
    maintain_apply.set_defaults(func=command_maintain)

    snapshot = subparsers.add_parser("snapshot", help="Save a SHA256 manifest snapshot")
    add_root(snapshot)
    snapshot.set_defaults(func=command_snapshot)

    diff = subparsers.add_parser("diff", help="Compare current files to latest snapshot")
    add_root(diff)
    diff.set_defaults(func=command_diff)

    status = subparsers.add_parser("status", help="Show scan and manifest summary")
    add_root(status)
    status.set_defaults(func=command_status)

    sync = subparsers.add_parser("sync", help="Sync primary vault to a target")
    add_root(sync)
    sync.add_argument("--target", required=True)
    sync.add_argument("--write", action="store_true", help="Actually copy changed files")
    sync.set_defaults(func=command_sync)

    autosync = subparsers.add_parser("autosync", help="Configure or run automatic sync")
    add_root(autosync)
    autosync_sub = autosync.add_subparsers(dest="action", required=True)
    autosync_enable = autosync_sub.add_parser("enable", help="Enable automatic sync")
    add_root(autosync_enable)
    autosync_enable.add_argument("--target", required=True)
    autosync_enable.set_defaults(func=command_autosync)
    autosync_disable = autosync_sub.add_parser("disable", help="Disable automatic sync")
    add_root(autosync_disable)
    autosync_disable.set_defaults(func=command_autosync)
    autosync_status = autosync_sub.add_parser("status", help="Show automatic sync config")
    add_root(autosync_status)
    autosync_status.set_defaults(func=command_autosync)
    autosync_run = autosync_sub.add_parser("run", help="Run configured sync now")
    add_root(autosync_run)
    autosync_run.set_defaults(func=command_autosync)

    doctor = subparsers.add_parser("doctor", help="Run status, diff, and repair dry-run")
    add_root(doctor)
    doctor.set_defaults(func=command_doctor)

    safety = subparsers.add_parser("safety", help="Show sync safety status")
    add_root(safety)
    safety.set_defaults(func=command_safety)

    protect = subparsers.add_parser("protect", help="Capture, inspect, or restore critical files")
    add_root(protect)
    protect_sub = protect.add_subparsers(dest="action", required=True)
    protect_capture = protect_sub.add_parser("capture", help="Capture protected file baselines")
    add_root(protect_capture)
    protect_capture.set_defaults(func=command_protect)
    protect_status = protect_sub.add_parser("status", help="Show protected file drift")
    add_root(protect_status)
    protect_status.set_defaults(func=command_protect)
    protect_restore = protect_sub.add_parser("restore", help="Restore protected files from baseline")
    add_root(protect_restore)
    protect_restore.set_defaults(func=command_protect)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
