#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import shutil
from datetime import datetime
from pathlib import Path

EXCLUDED_PARTS = {".git", "__pycache__", "state"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}


def default_source_root() -> Path:
    return Path(__file__).resolve().parents[2]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def maybe_sha256(path: Path) -> str | None:
    try:
        return sha256(path)
    except OSError:
        return None


def iter_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if any(part in EXCLUDED_PARTS for part in rel.parts):
            continue
        if path.suffix in EXCLUDED_SUFFIXES:
            continue
        files.append(path)
    return files


def plan_sync(source: Path, target: Path) -> tuple[list[tuple[Path, Path]], list[tuple[Path, Path]]]:
    to_copy: list[tuple[Path, Path]] = []
    same: list[tuple[Path, Path]] = []
    for src in iter_files(source):
        rel = src.relative_to(source)
        dst = target / rel
        src_hash = maybe_sha256(src)
        dst_hash = maybe_sha256(dst) if dst.exists() else None
        if src_hash is None or dst_hash is None or src_hash != dst_hash:
            to_copy.append((src, dst))
        else:
            same.append((src, dst))
    return to_copy, same


def copy_with_rebuild(src: Path, dst: Path) -> str | None:
    try:
        shutil.copy2(src, dst)
        if maybe_sha256(src) == maybe_sha256(dst):
            return None
        first_error: Exception = OSError("copy completed but target hash stayed stale")
    except OSError as exc:
        first_error = exc
    try:
        if dst.exists():
            dst.unlink()
    except OSError as exc:
        return f"{dst}: copy failed ({first_error}); unlink failed ({exc})"
    try:
        shutil.copy2(src, dst)
        if maybe_sha256(src) == maybe_sha256(dst):
            return None
        return f"{dst}: copy failed after rebuild (target hash stayed stale)"
    except OSError as exc:
        return f"{dst}: copy failed after rebuild ({exc})"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=str(default_source_root()), help="Primary local vault root")
    parser.add_argument("--target", required=True, help="Optional sync target")
    parser.add_argument("--write", action="store_true", help="Actually copy changed files")
    args = parser.parse_args()

    source = Path(args.source)
    target = Path(args.target)
    if not source.exists():
        raise SystemExit(f"source does not exist: {source}")
    if not target.exists():
        raise SystemExit(f"target does not exist: {target}")

    to_copy, same = plan_sync(source, target)
    failed_files: list[str] = []
    lines = [
        f"sync_time: {datetime.now().isoformat(timespec='seconds')}",
        f"source: {source}",
        f"target: {target}",
        f"same_files: {len(same)}",
        f"changed_files: {len(to_copy)}",
        f"mode: {'write' if args.write else 'dry-run'}",
        "",
    ]
    for src, dst in to_copy:
        rel = src.relative_to(source)
        lines.append(f"- {rel}")
        if args.write:
            dst.parent.mkdir(parents=True, exist_ok=True)
            error = copy_with_rebuild(src, dst)
            if error:
                lines.append(f"  error: {error}")
                failed_files.append(rel.as_posix())

    print("\n".join(lines))
    if failed_files:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
