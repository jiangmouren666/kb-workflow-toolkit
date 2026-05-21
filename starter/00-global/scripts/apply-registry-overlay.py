#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path


def default_vault_root() -> Path:
    return Path(__file__).resolve().parents[2]


@dataclass
class RegistryEntry:
    path: str
    status: str
    decision: str
    reviewed_at: str
    use: str
    risk: str
    evidence_need: str
    boundary: str


def parse_registry(root: Path) -> list[RegistryEntry]:
    registry = root / "00-global" / "human-review-registry.md"
    text = registry.read_text(encoding="utf-8")
    entries: list[RegistryEntry] = []
    for line in text.splitlines():
        if not line.startswith("| `"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 8:
            continue
        path = cells[0].strip("`")
        entries.append(
            RegistryEntry(
                path=path,
                status=cells[1],
                decision=cells[2].strip("`"),
                reviewed_at=cells[3],
                use=cells[4],
                risk=cells[5],
                evidence_need=cells[6],
                boundary=cells[7],
            )
        )
    return entries


def frontmatter_bounds(text: str) -> tuple[int, int] | None:
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end == -1:
        return None
    return 4, end


def top_level_keys(frontmatter: str) -> set[str]:
    keys: set[str] = set()
    for line in frontmatter.splitlines():
        if line and not line.startswith((" ", "-")) and ":" in line:
            keys.add(line.split(":", 1)[0].strip())
    return keys


def replace_or_insert_status(lines: list[str], status: str) -> list[str]:
    for idx, line in enumerate(lines):
        if line.startswith("status:"):
            lines[idx] = f"status: {status}"
            return lines
    insert_at = 0
    for idx, line in enumerate(lines):
        if line.startswith("domain:") or line.startswith("primary_domain:"):
            insert_at = idx + 1
    lines.insert(insert_at, f"status: {status}")
    return lines


def append_missing_scalar(lines: list[str], keys: set[str], key: str, value: str) -> bool:
    if key in keys:
        return False
    lines.append(f"{key}: {value}")
    keys.add(key)
    return True


def append_missing_list(lines: list[str], keys: set[str], key: str, values: list[str]) -> bool:
    if key in keys:
        return False
    lines.append(f"{key}:")
    for value in values:
        lines.append(f"  - {value}")
    keys.add(key)
    return True


def apply_entry(root: Path, entry: RegistryEntry, write: bool) -> str:
    path = root / entry.path
    if not path.exists():
        return f"missing: {entry.path}"
    text = path.read_text(encoding="utf-8")
    bounds = frontmatter_bounds(text)
    if bounds is None:
        return f"no_frontmatter: {entry.path}"
    start, end = bounds
    fm = text[start:end]
    keys = top_level_keys(fm)
    lines = replace_or_insert_status(fm.splitlines(), entry.status)
    changed = lines != fm.splitlines()

    changed |= append_missing_scalar(lines, keys, "evidence_level", "user_experience")
    changed |= append_missing_list(lines, keys, "use_for", [entry.use.replace(" ", "_").replace("/", "_")])
    changed |= append_missing_scalar(lines, keys, "scope", entry.boundary)
    changed |= append_missing_scalar(lines, keys, "should_not_use_for", "treating this reviewed note as externally verified fact")
    changed |= append_missing_scalar(lines, keys, "time_sensitivity", "medium")
    changed |= append_missing_scalar(lines, keys, "review_cycle", "180d")
    changed |= append_missing_scalar(lines, keys, "usage_count", "0")
    changed |= append_missing_scalar(lines, keys, "last_used", "")
    changed |= append_missing_scalar(lines, keys, "last_feedback", "")
    changed |= append_missing_list(lines, keys, "failure_modes", [])
    changed |= append_missing_list(lines, keys, "improvement_notes", [])

    if "human_review" not in keys:
        lines.extend(
            [
                "human_review:",
                "  reviewer: user",
                f"  decision: {entry.decision}",
                f"  reviewed_at: {entry.reviewed_at}",
                f"  result: registry overlay restored; {entry.boundary}",
            ]
        )
        changed = True

    if not changed:
        return f"ok: {entry.path}"

    if write:
        new_text = "---\n" + "\n".join(lines) + text[end:]
        path.write_text(new_text, encoding="utf-8")
        return f"repaired: {entry.path}"
    return f"would_repair: {entry.path}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(default_vault_root()))
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    root = Path(args.root)
    entries = parse_registry(root)
    print(f"registry_entries: {len(entries)}")
    print(f"mode: {'write' if args.write else 'dry-run'}")
    for entry in entries:
        print(apply_entry(root, entry, args.write))


if __name__ == "__main__":
    main()
