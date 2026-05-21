#!/usr/bin/env python3
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
