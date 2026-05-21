#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

ALLOWED_STATUS = {"raw", "draft", "reviewed", "verified", "stale", "deprecated", "rejected", "needs-review"}
ALLOWED_CONFIDENCE = {"low", "medium", "high"}
ALLOWED_EVIDENCE_LEVEL = {"none", "source_claim", "user_experience", "official_doc", "source_code", "experiment", "backtest", "production_result"}
STRONG_EVIDENCE_LEVEL = {"official_doc", "source_code", "experiment", "backtest", "production_result"}
REVIEW_CYCLES = {"none": None, "30d": 30, "90d": 90, "180d": 180, "365d": 365}
REQUIRED_META = {"type", "status", "confidence", "source"}
REQUIRED_ANY_DATE = {"updated", "ingested", "last_checked"}
RECOMMENDED_GOVERNANCE_META = {"evidence_level", "use_for", "scope", "should_not_use_for", "time_sensitivity", "review_cycle"}
FEEDBACK_META = {"usage_count", "last_used", "last_feedback", "failure_modes", "improvement_notes"}
DOMAIN_FOLDERS = {"quant", "machine-learning", "ai-agent", "programming", "framework-optimization", "fiction-reasoning", "education"}
LEGACY_GLOBAL_FILES = {
    "answer-risk-reminders.md",
    "evaluation-scorecard.md",
    "human-machine-governance.md",
    "maintenance-rules.md",
    "review-decision-questions.md",
    "routing-rules.md",
}
WIKILINK_RE = re.compile(r"(?<!!)\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")
SAFE_RANDOM_SPLIT_CONTEXT = ("do not", "don't", "not treat", "without checking", "leakage", "防止", "不要", "不能", "不应", "不建议")
FINDING_ORDER = [
    "missing_metadata",
    "missing_governance_metadata",
    "missing_human_review",
    "missing_feedback_metadata",
    "invalid_status",
    "invalid_confidence",
    "invalid_evidence_level",
    "trust_upgrade_risks",
    "feedback_review",
    "stale_candidates",
    "category_mismatch",
    "broken_links",
    "duplicate_candidates",
    "conflict_candidates",
]


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
        if ".git" in rel.parts or "audit-reports" in rel.parts or "review-batches" in rel.parts:
            continue
        if rel.parts[:1] == ("00-global",) and path.name in {"review-queue.md", "review-queue-explicit.md", "review-queue-v2.md"}:
            continue
        text = path.read_text(encoding="utf-8")
        notes.append({"path": path, "rel": rel, "text": text, "meta": parse_frontmatter(text), "title": title_for(path, text)})
    return notes


def parse_review_registry(root: Path) -> dict[str, str]:
    registry = root / "00-global" / "human-review-registry.md"
    if not registry.exists():
        return {}
    statuses: dict[str, str] = {}
    text = registry.read_text(encoding="utf-8")
    for line in text.splitlines():
        if not line.startswith("| `"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) >= 2:
            statuses[cells[0].strip("`")] = cells[1]
    return statuses


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


def add_all_markdown_link_targets(root: Path, index: set[str]) -> None:
    for path in root.rglob("*.md"):
        rel = path.relative_to(root)
        if ".git" in rel.parts:
            continue
        index.add(path.stem)
        index.add(str(rel.with_suffix("")))


def requires_governance_metadata(rel: Path, meta: dict[str, str]) -> bool:
    if rel.parts[:1] == ("00-global",) and rel.name in LEGACY_GLOBAL_FILES:
        return False
    if rel.name in {"README.md", "00-index.md", "review-queue.md", "review-queue-explicit.md", "review-queue-v2.md"}:
        return False
    if "templates" in rel.parts:
        return False
    if meta.get("type") in {"index", "maintenance", "audit-report"}:
        return False
    return True


def scan(root: Path) -> tuple[list[dict], dict[str, list[str]], dict[str, list[str]]]:
    notes = read_notes(root)
    registry_status = parse_review_registry(root)
    links = link_index(notes)
    add_all_markdown_link_targets(root, links)
    findings: dict[str, list[str]] = defaultdict(list)
    notices: dict[str, list[str]] = defaultdict(list)
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

        rel_str = str(rel)
        if rel_str in registry_status and status != registry_status[rel_str]:
            notices["registry_overlay_applied"].append(
                f"- `{rel}` frontmatter status `{status or 'missing'}` differs from registry `{registry_status[rel_str]}`"
            )

        confidence = meta.get("confidence")
        if confidence and confidence not in ALLOWED_CONFIDENCE:
            findings["invalid_confidence"].append(f"- `{rel}` confidence `{confidence}` is not allowed")

        evidence_level = meta.get("evidence_level")
        if evidence_level and evidence_level not in ALLOWED_EVIDENCE_LEVEL:
            findings["invalid_evidence_level"].append(f"- `{rel}` evidence_level `{evidence_level}` is not allowed")

        if requires_governance_metadata(rel, meta):
            if rel_str not in registry_status:
                missing_governance = sorted(RECOMMENDED_GOVERNANCE_META - set(meta))
                if missing_governance:
                    message = f"- `{rel}` missing recommended governance fields: {', '.join(missing_governance)}"
                    if "use_when" in meta and status == "draft":
                        notices["legacy_metadata_overlay"].append(message)
                    else:
                        findings["missing_governance_metadata"].append(message)

            if status in {"reviewed", "verified"} and "human_review" not in meta:
                findings["missing_human_review"].append(f"- `{rel}` is `{status}` but has no `human_review` record")

            if status in {"reviewed", "verified"} and rel_str not in registry_status:
                missing_feedback = sorted(FEEDBACK_META - set(meta))
                if missing_feedback:
                    findings["missing_feedback_metadata"].append(f"- `{rel}` is reusable but missing feedback fields: {', '.join(missing_feedback)}")

        if status == "verified" and evidence_level not in STRONG_EVIDENCE_LEVEL:
            findings["trust_upgrade_risks"].append(f"- `{rel}` is `verified` but evidence_level `{evidence_level or 'missing'}` is not strong enough")

        if meta.get("last_feedback") in {"wrong", "incomplete", "too_generic", "stale"}:
            findings["feedback_review"].append(f"- `{rel}` has last_feedback `{meta.get('last_feedback')}`; review scope, status, or evidence needs")

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

    return notes, findings, notices


def render_report(root: Path, notes: list[dict], findings: dict[str, list[str]], notices: dict[str, list[str]]) -> str:
    total = sum(len(items) for items in findings.values())
    lines = [
        "---",
        "type: audit-report",
        "domain: global",
        "status: draft",
        "confidence: high",
        "source: scan-vault-strict.py",
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
    for key in FINDING_ORDER:
        lines += [f"## {key.replace('_', ' ').title()}", ""]
        lines += findings.get(key) or ["- None"]
        lines.append("")
    lines += ["## Registry Overlay Applied", ""]
    lines += notices.get("registry_overlay_applied") or ["- None"]
    lines.append("")
    lines += ["## Legacy Metadata Overlay", ""]
    lines += notices.get("legacy_metadata_overlay") or ["- None"]
    lines.append("")
    lines += [
        "## Policy",
        "",
        "- This report is diagnostic only.",
        "- Do not delete, merge, move, or change note status without approval.",
        "- Use `review-queue-v2.md` for human decisions.",
        "",
    ]
    return "\n".join(lines)


def render_queue(findings: dict[str, list[str]]) -> str:
    high_keys = ["trust_upgrade_risks", "feedback_review", "missing_human_review", "conflict_candidates", "category_mismatch", "stale_candidates", "broken_links"]
    lines = [
        "---",
        "type: maintenance",
        "domain: global",
        "status: draft",
        "confidence: high",
        "source: scan-vault-strict.py",
        f"updated: {date.today().isoformat()}",
        "---",
        "",
        "# Review Queue",
        "",
        "Items below require human review before mutation. Each item must include enough context for a user to decide without opening the note.",
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
                "- review_location: metadata or affected section listed above",
                "- content_excerpt: see note before changing status if the item affects trust",
                "- key_claims: not automatically inferred by scanner",
                "- risks_or_unknowns: this finding may affect retrieval, trust, or answer safety",
                "- suggested_action: needs-human-review",
                "- my_recommendation: B unless the item is clearly false or high-risk",
                "",
                "Options:",
                "- A. Keep as is: make no metadata change now.",
                "- B. Add to needs-review: keep or downgrade citation strength until resolved.",
                "- C. Request evidence: add an improvement note describing what proof is needed.",
                "- D. Mark as deprecated/rejected candidate: only if confirmed harmful.",
                "",
                "- approval_needed: yes",
                "",
            ]
    if count == 0:
        lines.append("No open items.")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=os.environ.get("KNOWLEDGE_VAULT_ROOT", "knowledge-vaults"), help="Knowledge vault root. Defaults to KNOWLEDGE_VAULT_ROOT or ./knowledge-vaults.")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    root = Path(args.root)
    notes, findings, notices = scan(root)
    report = render_report(root, notes, findings, notices)
    print(report)

    if args.write:
        report_dir = root / "00-global" / "audit-reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir / f"{date.today().isoformat()}-vault-audit.md"
        queue_path = root / "00-global" / "review-queue-v2.md"
        report_path.write_text(report, encoding="utf-8")
        queue_path.write_text(render_queue(findings), encoding="utf-8")
        print(f"\nWROTE {report_path}")
        print(f"WROTE {queue_path}")


if __name__ == "__main__":
    main()
