#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import date
from pathlib import Path


STRONG_EVIDENCE_LEVEL = {"official_doc", "source_code", "experiment", "backtest", "production_result"}
EVIDENCE_CHECKLIST_FIELDS = {"evidence_checklist", "validation_evidence", "verified_evidence"}


def report_markdown_path(root: Path) -> Path:
    return root / "00-global" / "trust-drift-report.md"


def report_jsonl_path(root: Path) -> Path:
    return root / "00-global" / "state" / "trust-drift-report.jsonl"


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end == -1:
        return {}
    meta: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if not line.strip() or line.startswith((" ", "-")):
            continue
        if ":" in line:
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip().strip('"').strip("'")
    return meta


def read_notes(root: Path) -> list[dict]:
    notes: list[dict] = []
    for path in sorted(root.rglob("*.md")):
        rel = path.relative_to(root)
        if ".git" in rel.parts or "state" in rel.parts or "audit-reports" in rel.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        notes.append({"path": path, "rel": rel.as_posix(), "meta": parse_frontmatter(text), "text": text})
    return notes


def parse_review_registry(root: Path) -> dict[str, dict]:
    registry = root / "00-global" / "human-review-registry.md"
    if not registry.exists():
        return {}
    entries: dict[str, dict] = {}
    for line in registry.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith("| `"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 8:
            continue
        path = cells[0].strip("`")
        entries[path] = {
            "path": path,
            "registry_status": cells[1],
            "decision": cells[2].strip("`"),
            "reviewed_at": cells[3],
            "use": cells[4],
            "risk": cells[5],
            "evidence_need": cells[6],
            "boundary": cells[7],
        }
    return entries


def finding(path: str, finding_type: str, severity: str, message: str) -> dict:
    return {
        "schema": "knowledge-trust-drift-finding-v1",
        "path": path,
        "finding_type": finding_type,
        "severity": severity,
        "message": message,
        "created_at": date.today().isoformat(),
    }


def generate_findings(root: Path) -> list[dict]:
    registry = parse_review_registry(root)
    notes = read_notes(root)
    notes_by_rel = {note["rel"]: note for note in notes}
    findings: list[dict] = []

    for path, entry in registry.items():
        note = notes_by_rel.get(path)
        if note is None:
            findings.append(finding(path, "registry_target_missing", "high", "Registry entry points to a missing note."))
            continue
        frontmatter_status = note["meta"].get("status", "")
        if frontmatter_status != entry["registry_status"]:
            findings.append(
                finding(
                    path,
                    "frontmatter_registry_mismatch",
                    "medium",
                    f"Frontmatter status `{frontmatter_status or 'missing'}` differs from registry `{entry['registry_status']}`.",
                )
            )

    for note in notes:
        rel = note["rel"]
        meta = note["meta"]
        status = meta.get("status", "")
        if status == "reviewed" and "human_review" not in meta and rel not in registry:
            findings.append(finding(rel, "reviewed_without_human_review", "medium", "Reviewed note lacks human_review and registry entry."))
        if status == "verified":
            evidence_level = meta.get("evidence_level", "")
            if evidence_level not in STRONG_EVIDENCE_LEVEL:
                findings.append(
                    finding(
                        rel,
                        "verified_without_strong_evidence",
                        "high",
                        f"Verified note has evidence_level `{evidence_level or 'missing'}`.",
                    )
                )
            if not (EVIDENCE_CHECKLIST_FIELDS & set(meta)):
                findings.append(finding(rel, "verified_missing_evidence_checklist", "high", "Verified note lacks an evidence checklist field."))
            if not meta.get("source") or meta.get("source") in {"unclear", "unknown", "ai"}:
                findings.append(finding(rel, "verified_unclear_source", "high", "Verified note has unclear source metadata."))

    return sorted(findings, key=lambda item: (item["severity"], item["path"], item["finding_type"]))


def render_markdown(root: Path, findings: list[dict]) -> str:
    counts = Counter(item["finding_type"] for item in findings)
    lines = [
        "---",
        "type: audit-report",
        "domain: global",
        "status: draft",
        "confidence: high",
        "source: trust-drift-report.py",
        f"updated: {date.today().isoformat()}",
        "---",
        "",
        f"# Trust Drift Report {date.today().isoformat()}",
        "",
        f"- vault_root: `{root}`",
        f"- trust_drift_count: {len(findings)}",
        "",
        "## Summary",
        "",
    ]
    if counts:
        for key, count in sorted(counts.items()):
            lines.append(f"- {key}: {count}")
    else:
        lines.append("- None")
    lines.extend(["", "## Findings", ""])
    if not findings:
        lines.append("- None")
    for item in findings:
        lines.append(f"- [{item['severity']}] `{item['path']}` {item['finding_type']}: {item['message']}")
    return "\n".join(lines).rstrip() + "\n"


def write_outputs(root: Path, findings: list[dict]) -> dict[str, Path]:
    markdown = report_markdown_path(root)
    jsonl = report_jsonl_path(root)
    markdown.parent.mkdir(parents=True, exist_ok=True)
    jsonl.parent.mkdir(parents=True, exist_ok=True)
    markdown.write_text(render_markdown(root, findings), encoding="utf-8")
    jsonl.write_text("".join(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n" for item in findings), encoding="utf-8")
    return {"markdown": markdown, "jsonl": jsonl}


def print_summary(findings: list[dict]) -> None:
    print(f"trust_drift_count: {len(findings)}")
    counts = Counter(item["finding_type"] for item in findings)
    for key, count in sorted(counts.items()):
        print(f"{key}: {count}")
    for item in findings[:20]:
        print(f"- [{item['severity']}] `{item['path']}` {item['finding_type']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate trust drift reports without modifying notes.")
    parser.add_argument("--root", required=True)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    root = Path(args.root)
    findings = generate_findings(root)
    print_summary(findings)
    if args.write:
        outputs = write_outputs(root, findings)
        print(f"wrote_markdown: {outputs['markdown']}")
        print(f"wrote_jsonl: {outputs['jsonl']}")


if __name__ == "__main__":
    main()
