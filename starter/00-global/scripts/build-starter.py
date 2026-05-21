#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


DEFAULT_TARGET = Path("/data/knowledge-vault-starter")
DOMAINS = (
    "quant",
    "ai-agent",
    "machine-learning",
    "programming",
    "framework-optimization",
    "fiction-reasoning",
    "education",
)
SCRIPT_FILES = (
    "kb.py",
    "scan-vault-strict.py",
    "apply-registry-overlay.py",
    "improvement-loop.py",
    "improvement-review.py",
    "maintenance-tasks.py",
    "maintenance-proposals.py",
    "maintenance-proposal-review.py",
    "maintenance-change-drafts.py",
    "maintenance-change-draft-review.py",
    "maintenance-apply-packages.py",
    "maintenance-apply-plans.py",
    "sync-vault.py",
    "build-starter.py",
    "test_kb.py",
    "test_sync_vault.py",
    "test_build_starter.py",
    "test_improvement_loop.py",
    "test_improvement_review.py",
    "test_maintenance_tasks.py",
    "test_maintenance_proposals.py",
    "test_maintenance_proposal_review.py",
    "test_maintenance_change_drafts.py",
    "test_maintenance_change_draft_review.py",
    "test_maintenance_apply_packages.py",
    "test_maintenance_apply_plans.py",
)
EVALUATION_FILES = (
    "context_pack_builder_v2.py",
    "run_context_format_eval_v2.py",
    "test_context_pack_builder_v2.py",
    "test_run_context_format_eval_v2.py",
)
GLOBAL_DOCS = (
    "current-governance-v2.md",
    "domain-standard-template.md",
    "usage-guide.md",
    "write-protection-policy.md",
    "import-interaction-workflow.md",
    "human-machine-governance.md",
    "maintenance-rules.md",
    "review-decision-questions.md",
    "answer-risk-reminders.md",
    "routing-rules.md",
    "evaluation-scorecard.md",
)
EXCLUDED_PREFIXES = (
    "00-global/state/",
    "00-global/audit-reports/",
    "00-global/evaluation/runs/",
    "00-global/review-batches/",
)
EXCLUDED_NAMES = {
    "webdav-sync-reliability-report-v1.md",
}


BOOTSTRAP_SCRIPT = r'''#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


EXCLUDED_PREFIXES = (
    "00-global/state/",
    "00-global/audit-reports/",
    "00-global/evaluation/runs/",
)
EXCLUDED_ROOT_FILES = {"bootstrap-local-vault.py", "starter-manifest.json"}


def should_copy(rel: Path) -> bool:
    rel_text = rel.as_posix()
    if rel_text in EXCLUDED_ROOT_FILES:
        return False
    return not any(rel_text.startswith(prefix) for prefix in EXCLUDED_PREFIXES)


def copy_template(template: Path, root: Path) -> list[str]:
    copied: list[str] = []
    for source in sorted(template.rglob("*")):
        rel = source.relative_to(template)
        if not should_copy(rel):
            continue
        target = root / rel
        if source.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied.append(rel.as_posix())
    return copied


def bootstrap(template: Path, root: Path, sync_target: str = "", enable_sync: bool = False) -> None:
    template = template.expanduser().resolve()
    root = root.expanduser().resolve()
    copy_template(template, root)
    command = [sys.executable, str(root / "00-global" / "scripts" / "kb.py"), "init", "--root", str(root)]
    if sync_target:
        command.extend(["--sync-target", sync_target])
    if enable_sync:
        command.append("--enable-sync")
    subprocess.run(command, text=True, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap a local-first knowledge vault from this starter template.")
    parser.add_argument("--root", required=True, help="Target local vault root.")
    parser.add_argument("--template", default=str(Path(__file__).resolve().parent), help="Starter template root.")
    parser.add_argument("--sync-target", default="", help="Optional export/sync target.")
    parser.add_argument("--enable-sync", action="store_true", help="Enable local-to-target sync after bootstrap.")
    args = parser.parse_args()
    bootstrap(Path(args.template), Path(args.root), sync_target=args.sync_target, enable_sync=args.enable_sync)
    print(f"vault_bootstrapped: {Path(args.root).expanduser().resolve()}")


if __name__ == "__main__":
    main()
'''


def default_source_root() -> Path:
    return Path(__file__).resolve().parents[2]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def reset_target(target_root: Path) -> None:
    if target_root.exists():
        shutil.rmtree(target_root)
    target_root.mkdir(parents=True)


def copy_file(source_root: Path, target_root: Path, rel: str, copied: list[str]) -> None:
    source = source_root / rel
    if not source.exists() or source.name in EXCLUDED_NAMES:
        return
    target = target_root / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    copied.append(rel)


def create_base_directories(target_root: Path) -> None:
    for domain in DOMAINS:
        (target_root / domain / "10-standards").mkdir(parents=True, exist_ok=True)
        (target_root / domain / "20-notes").mkdir(parents=True, exist_ok=True)
    for rel in ("00-global/scripts", "00-global/evaluation"):
        (target_root / rel).mkdir(parents=True, exist_ok=True)


def collect_template_files(source_root: Path) -> list[str]:
    relpaths: list[str] = []
    relpaths.extend(f"00-global/scripts/{name}" for name in SCRIPT_FILES)
    relpaths.extend(f"00-global/evaluation/{name}" for name in EVALUATION_FILES)
    relpaths.extend(f"00-global/{name}" for name in GLOBAL_DOCS)
    for domain in DOMAINS:
        standards = sorted((source_root / domain / "10-standards").glob("*.md"))
        relpaths.extend(path.relative_to(source_root).as_posix() for path in standards)
        inbox_readme = source_root / domain / "00-inbox" / "README.md"
        if inbox_readme.exists():
            relpaths.append(inbox_readme.relative_to(source_root).as_posix())
    return sorted(dict.fromkeys(relpaths))


def write_bootstrap(target_root: Path, copied: list[str]) -> None:
    path = target_root / "bootstrap-local-vault.py"
    path.write_text(BOOTSTRAP_SCRIPT, encoding="utf-8")
    path.chmod(0o755)
    copied.append("bootstrap-local-vault.py")


def write_readme(target_root: Path, copied: list[str]) -> None:
    path = target_root / "README.md"
    path.write_text(
        "# Knowledge Vault Starter\n\n"
        "This starter initializes a local-first knowledge vault. The local folder is the source of truth; sync targets are optional.\n\n"
        "```bash\n"
        "python bootstrap-local-vault.py --root /path/to/my-knowledge-vaults\n"
        "```\n",
        encoding="utf-8",
    )
    copied.append("README.md")


def write_manifest(source_root: Path, target_root: Path, copied: list[str]) -> dict:
    files = sorted(dict.fromkeys(copied + ["starter-manifest.json"]))
    manifest = {
        "schema": "knowledge-vault-starter-manifest-v1",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "source_root_name": source_root.name,
        "file_count": len(files),
        "files": files,
        "excluded_prefixes": list(EXCLUDED_PREFIXES),
        "excluded_names": sorted(EXCLUDED_NAMES),
    }
    manifest_path = target_root / "starter-manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest["checksums"] = {rel: sha256(target_root / rel) for rel in files if (target_root / rel).is_file()}
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def build_starter(source_root: Path, target_root: Path = DEFAULT_TARGET) -> dict:
    source_root = source_root.expanduser().resolve()
    target_root = target_root.expanduser().resolve()
    reset_target(target_root)
    create_base_directories(target_root)
    copied: list[str] = []
    for rel in collect_template_files(source_root):
        if any(rel.startswith(prefix) for prefix in EXCLUDED_PREFIXES):
            continue
        copy_file(source_root, target_root, rel, copied)
    write_bootstrap(target_root, copied)
    write_readme(target_root, copied)
    return write_manifest(source_root, target_root, copied)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a portable local-first knowledge vault starter.")
    parser.add_argument("--source-root", default=str(default_source_root()), help="Source knowledge vault root.")
    parser.add_argument("--target", default=str(DEFAULT_TARGET), help="Starter output directory.")
    args = parser.parse_args()
    manifest = build_starter(Path(args.source_root), Path(args.target))
    print(f"starter_built: {Path(args.target).expanduser().resolve()}")
    print(f"file_count: {manifest['file_count']}")
    print(f"manifest: {Path(args.target).expanduser().resolve() / 'starter-manifest.json'}")


if __name__ == "__main__":
    main()
