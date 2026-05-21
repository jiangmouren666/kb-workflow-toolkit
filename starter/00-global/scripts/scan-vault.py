#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

ALLOWED_STATUS = {"raw", "draft", "verified", "stale", "deprecated", "rejected", "needs-review"}
ALLOWED_CONFIDENCE = {"low", "medium", "high"}
REVIEW_CYCLES = {"none": None, "30d": 30, "90d": 90, "180d": 180, "365d": 365}
REQUIRED_META = {"type", "status", "confidence", "source"}
REQUIRED_ANY_DATE = {"updated", "ingested", "last_checked"}
DOMAIN_FOLDERS = {"quant", "machine-learning", "ai-agent"}
WIKILINK_RE = re.compile(r"(?<!!)\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")
SAFE_RANDOM_SPLIT_CONTEXT = (
    "do not",
    "don't",
    "not treat",
    "without checking",
    "leakage",
    "防止",
    "不要",
    "不能",
    "不应",
    "不建议",
)


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end == -1:
        return {}
    meta: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if not line.strip() or line.startswith(" ") or line.startswith("-"):
            continue
        if ":" in line:
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip().strip('"').strip("'")
    return meta


def title_for(path: Path, text: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return path.stem


def read_notes(root: Path) -> list[dict]:
    notes: list[dict] = []
    for path in sorted(root.rglob("*.md")):
        rel = path.relative_to(root)
        if ".git" in rel.parts or "audit-reports" in rel.parts:
            continue
        text = path.read_text(encoding="utf-8")
        notes.append({"path": path, "rel": rel, "text": text, "meta": parse_frontmatter(text), "title": title_for(path, text)})
    return notes


def parse_date(value: str | None) -> date | None:
    if not value or value == "Not reported":
        return None
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def path_domain(rel: Path) -> str | None:
    for part in rel.parts:
        if part in DOMAIN_FOLDERS:
            return part
    if rel.parts and rel.parts[0] == "00-global":
        return "global"
    return None


def link_index(notes: list[dict]) -> set[str]:
    index: set[str] = set()
    for note in notes:
        index.add(note["path"].stem)
        index.add(str(note["rel"].with_suffix("")))
        index.add(note["title"])
    return index


def scan(root: Path) -> tuple[list[dict], dict[str, list[str]]]:
    notes = read_notes(root)
    links = link_index(notes)
    findings: dict[str, list[str]] = defaultdict(list)
    title_map: dict[str, list[dict]] = defaultdict(list)

    for note in notes:
        rel = note["rel"]
        text = note["text"]
        meta = note["meta"]

        missing = sorted((REQUIRED_META - set(meta)) | (set() if REQUIRED_ANY_DATE & set(meta) else {"updated_or_ingested"}))
        if missing:
            findings["missing_metadata"].append(f"- `{rel}` missing: {', '.join(missing)}")

        status = meta.get("status")
        if status and status not in ALLOWED_STATUS:
            findings["invalid_status"].append(f"- `{rel}` status `{status}` is not allowed")

        confidence = meta.get("confidence")
        if confidence and confidence not in ALLOWED_CONFIDENCE:
            findings["invalid_confidence"].append(f"- `{rel}` confidence `{confidence}` is not allowed")

        folder_domain = path_domain(rel)
        meta_domain = meta.get("primary_domain") or meta.get("domain")
        if folder_domain and meta_domain and folder_domain != "global" and meta_domain not in {folder_domain, "quant-factor"}:
            findings["category_mismatch"].append(f"- `{rel}` path domain `{folder_domain}` differs from metadata `{meta_domain}`")

        cycle = meta.get("review_cycle")
        if cycle in REVIEW_CYCLES and REVIEW_CYCLES[cycle] is not None:
            base = parse_date(meta.get("last_checked")) or parse_date(meta.get("updated")) or parse_date(meta.get("ingested"))
            if base and date.today() > base + timedelta(days=REVIEW_CYCLES[cycle] or 0):
                findings["stale_candidates"].append(f"- `{rel}` review_cycle `{cycle}` last checked `{base}`")

        for raw in WIKILINK_RE.findall(text):
            target = raw.strip()
            target_name = Path(target).name
            if target not in links and target_name not in links:
                findings["broken_links"].append(f"- `{rel}` unresolved wikilink `[[{raw}]]`")

        for line in text.splitlines():
            lower = line.lower()
            mentions_random = "random split" in lower or "随机切分" in line or "随机打乱" in line
            mentions_temporal = "time series" in lower or "temporal" in lower or "时间序列" in line or "股票收益" in line
            warning_context = any(marker in lower or marker in line for marker in SAFE_RANDOM_SPLIT_CONTEXT)
            if mentions_random and mentions_temporal and not warning_context:
                findings["conflict_candidates"].append(f"- `{rel}` mentions random splitting for temporal/financial prediction; review against leakage standards")
                break

        title_key = re.sub(r"\s+", " ", note["title"].lower()).strip()
        title_map[title_key].append(note)

    for title, group in title_map.items():
        if title and len(group) > 1:
            paths = ", ".join(f"`{item['rel']}`" for item in group)
            findings["duplicate_candidates"].append(f"- title `{title}` appears in {paths}")

    return notes, findings


def render_report(root: Path, notes: list[dict], findings: dict[str, list[str]]) -> str:
    total = sum(len(items) for items in findings.values())
    lines = [
        "---",
        "type: audit-report",
        "domain: global",
        "status: draft",
        "confidence: high",
        "source: scan-vault.py",
        f"updated: {date.today().isoformat()}",
        "---",
        "",
        f"# Vault Audit {date.today().isoformat()}",
        "",
        "## Summary",
        "",
        f"- vault_root: `{root}`",
        f"- scanned_notes: {len(notes)}",
        f"- total_findings: {total}",
        "",
    ]
    for key in [
        "missing_metadata",
        "invalid_status",
        "invalid_confidence",
        "stale_candidates",
        "category_mismatch",
        "broken_links",
        "duplicate_candidates",
        "conflict_candidates",
    ]:
        lines += [f"## {key.replace('_', ' ').title()}", ""]
        lines += findings.get(key) or ["- None"]
        lines.append("")
    lines += [
        "## Policy",
        "",
        "- This report is diagnostic only.",
        "- Do not delete, merge, move, or change note status without approval.",
        "- Use `review-queue.md` for human decisions.",
        "",
    ]
    return "\n".join(lines)


def render_queue(findings: dict[str, list[str]]) -> str:
    high_keys = ["conflict_candidates", "category_mismatch", "stale_candidates", "broken_links"]
    lines = [
        "---",
        "type: maintenance",
        "domain: global",
        "status: draft",
        "confidence: high",
        "source: scan-vault.py",
        f"updated: {date.today().isoformat()}",
        "---",
        "",
        "# Review Queue",
        "",
        "Items below require human review before mutation.",
        "",
        "## Open Items",
        "",
    ]
    count = 0
    for key in high_keys:
        for item in findings.get(key, []):
            count += 1
            lines += [
                f"### {count}. {key.replace('_', ' ').title()}",
                "",
                item,
                "",
                "- suggested_action: needs-human-review",
                "- approval_needed: yes",
                "",
            ]
    if count == 0:
        lines.append("No open items.")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="knowledge-vaults")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    root = Path(args.root)
    notes, findings = scan(root)
    report = render_report(root, notes, findings)
    print(report)

    if args.write:
        report_dir = root / "00-global" / "audit-reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir / f"{date.today().isoformat()}-vault-audit.md"
        queue_path = root / "00-global" / "review-queue.md"
        report_path.write_text(report, encoding="utf-8")
        queue_path.write_text(render_queue(findings), encoding="utf-8")
        print(f"\nWROTE {report_path}")
        print(f"WROTE {queue_path}")


if __name__ == "__main__":
    main()
