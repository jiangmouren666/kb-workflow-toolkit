#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path


SCHEMA = "knowledge-improvement-candidate-v1"
STRONG_EVIDENCE_LEVELS = {"official_doc", "source_code", "experiment", "backtest", "production_result"}
NEGATIVE_FEEDBACK = {"wrong", "incomplete", "too_generic", "stale"}
REVIEW_CYCLES = {"none": None, "30d": 30, "90d": 90, "180d": 180, "365d": 365}
HIGH_RISK_SENSITIVITY = {"high"}
HIGH_RISK_DOMAINS = {"quant", "machine-learning", "programming"}
EXCLUDED_PARTS = {".git", "__pycache__", "audit-reports", "state", "review-batches"}
RECENT_IMPORT_WINDOW_DAYS = 7
CONFLICT_PATTERNS = (
    ("random_split_temporal", re.compile(r"\b(random split|randomly split|随机切分|随机划分)\b", re.I), ("time series", "时间序列", "回测", "temporal", "financial", "金融")),
)
RESOLVED_REVIEW_DECISIONS = {"rejected", "accepted_for_review", "converted_to_task"}
RECURRING_REVIEW_DECISIONS = {"deferred", "needs_more_evidence"}


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
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip().strip('"').strip("'")
    return meta


def parse_date(value: str | None) -> date | None:
    if not value or value == "Not reported":
        return None
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def parse_int(value: str | None) -> int:
    if not value:
        return 0
    try:
        return int(value)
    except ValueError:
        return 0


def read_notes(root: Path) -> list[dict]:
    notes: list[dict] = []
    for path in sorted(root.rglob("*.md")):
        rel = path.relative_to(root)
        if any(part in EXCLUDED_PARTS for part in rel.parts):
            continue
        if rel.parts[:1] == ("00-global",) and path.name in {"review-queue.md", "review-queue-v2.md", "improvement-candidates.md"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        notes.append({"path": path, "rel": rel.as_posix(), "text": text, "meta": parse_frontmatter(text)})
    return notes


def candidate(path: str, candidate_type: str, severity: str, reason: str, suggested_action: str, metadata: dict | None = None) -> dict:
    return {
        "schema": SCHEMA,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "path": path,
        "candidate_type": candidate_type,
        "severity": severity,
        "reason": reason,
        "suggested_action": suggested_action,
        "requires_human_review": True,
        "metadata_snapshot": metadata or {},
    }


def candidate_id(item: dict) -> str:
    raw = "\n".join([str(item.get("path", "")), str(item.get("candidate_type", "")), str(item.get("reason", ""))])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def review_registry_path(root: Path) -> Path:
    return root / "00-global" / "improvement-review-registry.md"


def parse_review_registry(root: Path) -> dict[str, dict]:
    path = review_registry_path(root)
    if not path.exists():
        return {}
    entries: dict[str, dict] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith("| `"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 7:
            continue
        cid = cells[0].strip("`")
        entries[cid] = {
            "decision": cells[3],
            "reviewed_at": cells[4],
            "reason": cells[5],
            "next_action": cells[6],
        }
    return entries


def apply_review_registry(items: list[dict], root: Path) -> list[dict]:
    registry = parse_review_registry(root)
    filtered: list[dict] = []
    for item in items:
        cid = candidate_id(item)
        entry = registry.get(cid)
        if not entry:
            filtered.append(item)
            continue
        decision = entry.get("decision", "")
        if decision in RESOLVED_REVIEW_DECISIONS:
            continue
        if decision in RECURRING_REVIEW_DECISIONS:
            enriched = dict(item)
            enriched["prior_review_decision"] = decision
            enriched["prior_reviewed_at"] = entry.get("reviewed_at", "")
            filtered.append(enriched)
    return filtered


def is_user_content_note(rel: str, meta: dict[str, str]) -> bool:
    path = Path(rel)
    if not path.parts:
        return False
    if path.parts[0] == "00-global" or path.name in {"README.md", "00-index.md"}:
        return False
    if "templates" in path.parts:
        return False
    if meta.get("type") in {"index", "guide", "standard", "maintenance", "audit-report"}:
        return False
    return True


def note_candidates(note: dict) -> list[dict]:
    rel = note["rel"]
    meta = note["meta"]
    text = note["text"]
    status = meta.get("status", "")
    evidence = meta.get("evidence_level", "")
    usage_count = parse_int(meta.get("usage_count"))
    time_sensitivity = meta.get("time_sensitivity", "")
    domain = meta.get("primary_domain") or meta.get("domain", "")
    imported_date = parse_date(meta.get("ingested")) or parse_date(meta.get("updated"))
    user_content_note = is_user_content_note(rel, meta)
    recent_import = bool(user_content_note and imported_date and date.today() <= imported_date + timedelta(days=RECENT_IMPORT_WINDOW_DAYS))
    items: list[dict] = []

    if status == "draft" and recent_import:
        items.append(
            candidate(
                rel,
                "recent_imported_draft",
                "low",
                f"draft note was imported or updated within {RECENT_IMPORT_WINDOW_DAYS} days",
                "Review scope, evidence boundary, feedback fields, and whether the note should be split after initial ingestion.",
                meta,
            )
        )

    if status == "draft" and usage_count >= 3:
        items.append(
            candidate(
                rel,
                "frequently_used_but_draft",
                "medium",
                f"usage_count is {usage_count} while status remains draft",
                "Review scope and evidence; decide whether to keep as draft, split, or submit for human review.",
                meta,
            )
        )

    if meta.get("last_feedback") in NEGATIVE_FEEDBACK:
        items.append(
            candidate(
                rel,
                "negative_feedback",
                "high",
                f"last_feedback is {meta.get('last_feedback')}",
                "Inspect the answer failure, add boundary conditions, downgrade use, or request human review.",
                meta,
            )
        )

    if status == "verified" and evidence not in STRONG_EVIDENCE_LEVELS:
        items.append(
            candidate(
                rel,
                "missing_evidence_for_verified",
                "high",
                f"verified note has evidence_level {evidence or 'missing'}",
                "Do not keep verified status without strong evidence; collect proof or queue for status review.",
                meta,
            )
        )

    if status in {"reviewed", "verified"} or recent_import:
        missing_feedback = [field for field in ("usage_count", "last_used", "last_feedback", "failure_modes", "improvement_notes") if field not in meta]
        if missing_feedback:
            items.append(
                candidate(
                    rel,
                    "missing_feedback_fields",
                    "low",
                    f"reusable note missing feedback fields: {', '.join(missing_feedback)}",
                    "Add feedback fields during the next maintenance pass without changing trust status.",
                    meta,
                )
            )

    cycle_days = REVIEW_CYCLES.get(meta.get("review_cycle", ""))
    base_date = parse_date(meta.get("last_checked")) or parse_date(meta.get("updated")) or parse_date(meta.get("ingested"))
    high_risk = time_sensitivity in HIGH_RISK_SENSITIVITY or domain in HIGH_RISK_DOMAINS
    if high_risk and cycle_days and base_date and date.today() > base_date + timedelta(days=cycle_days):
        items.append(
            candidate(
                rel,
                "stale_high_risk",
                "high",
                f"high-risk note review_cycle {meta.get('review_cycle')} last checked {base_date}",
                "Re-check against current evidence before using for decisions; consider marking stale after human approval.",
                meta,
            )
        )

    lowered = text.lower()
    for name, pattern, context_terms in CONFLICT_PATTERNS:
        if pattern.search(lowered) and any(term.lower() in lowered for term in context_terms):
            items.append(
                candidate(
                    rel,
                    "conflict_candidate",
                    "medium",
                    f"content matches conflict pattern {name}",
                    "Compare against domain standards and decide whether to add a warning, split, or reject the claim.",
                    meta,
                )
            )
            break

    return items


def read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return rows
    for line in lines:
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def load_context_pack(row: dict) -> dict | None:
    pack_path = row.get("context_pack_path")
    if not pack_path:
        return None
    path = Path(pack_path)
    if not path.exists():
        return None
    rows = read_jsonl(path)
    return rows[-1] if rows else None


def context_candidates(root: Path) -> list[dict]:
    runs_dir = root / "00-global" / "evaluation" / "runs"
    if not runs_dir.exists():
        return []
    items: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for run_path in sorted(runs_dir.glob("*.jsonl")):
        for row in read_jsonl(run_path):
            pack = load_context_pack(row)
            if not pack:
                continue
            quality = pack.get("context_quality", {})
            top_score = float(quality.get("top_score") or 0)
            missing_count = int(quality.get("missing_evidence_count") or 0)
            selected_count = int(quality.get("selected_count") or 0)
            if top_score >= 2 and missing_count == 0 and selected_count > 0:
                continue
            key = (run_path.as_posix(), row.get("question_id") or row.get("question") or "")
            if key in seen:
                continue
            seen.add(key)
            rel = run_path.relative_to(root).as_posix()
            items.append(
                candidate(
                    rel,
                    "low_quality_context_signal",
                    "medium",
                    f"context quality is weak: top_score={top_score}, selected_count={selected_count}, missing_evidence_count={missing_count}",
                    "Add or improve source notes for this question before relying on knowledge-base answers.",
                    {
                        "question_id": row.get("question_id", ""),
                        "question": row.get("question", pack.get("question", "")),
                        "top_path": quality.get("top_path", ""),
                    },
                )
            )
    return items


def sort_candidates(items: list[dict]) -> list[dict]:
    severity_rank = {"high": 0, "medium": 1, "low": 2}
    return sorted(items, key=lambda item: (severity_rank.get(item["severity"], 9), item["path"], item["candidate_type"]))


def build_candidates(root: Path) -> list[dict]:
    items: list[dict] = []
    for note in read_notes(root):
        items.extend(note_candidates(note))
    items.extend(context_candidates(root))
    return sort_candidates(apply_review_registry(items, root))


def render_markdown(root: Path, items: list[dict]) -> str:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for item in items:
        grouped[item["severity"]].append(item)
    lines = [
        "---",
        "type: maintenance",
        "domain: global",
        "status: draft",
        "confidence: high",
        "source: improvement-loop.py",
        f"updated: {date.today().isoformat()}",
        "---",
        "",
        "# Improvement Candidates",
        "",
        f"- vault_root: `{root}`",
        f"- candidate_count: {len(items)}",
        "- policy: suggestions only; do not auto-modify note status, registry, or standards",
        "",
    ]
    for severity in ("high", "medium", "low"):
        lines.extend([f"## {severity.title()} Severity", ""])
        if not grouped.get(severity):
            lines.extend(["- None", ""])
            continue
        for item in grouped[severity]:
            lines.extend(
                [
                    f"### `{item['path']}`",
                    "",
                    f"- type: `{item['candidate_type']}`",
                    f"- reason: {item['reason']}",
                    f"- suggested_action: {item['suggested_action']}",
                    f"- requires_human_review: {str(item['requires_human_review']).lower()}",
                    "",
                ]
            )
    return "\n".join(lines).rstrip() + "\n"


def write_outputs(root: Path, items: list[dict]) -> dict[str, Path]:
    markdown_path = root / "00-global" / "improvement-candidates.md"
    jsonl_path = root / "00-global" / "state" / "improvement-candidates.jsonl"
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(render_markdown(root, items), encoding="utf-8")
    jsonl_path.write_text("".join(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n" for item in items), encoding="utf-8")
    return {"markdown": markdown_path, "jsonl": jsonl_path}


def print_summary(items: list[dict]) -> None:
    counts: dict[str, int] = defaultdict(int)
    for item in items:
        counts[item["candidate_type"]] += 1
    print(f"candidate_count: {len(items)}")
    for key in sorted(counts):
        print(f"{key}: {counts[key]}")
    for item in items[:20]:
        print(f"- [{item['severity']}] {item['candidate_type']} `{item['path']}`: {item['reason']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate knowledge improvement candidates without mutating notes.")
    parser.add_argument("--root", required=True)
    parser.add_argument("--write", action="store_true", help="Write improvement-candidates.md and JSONL report.")
    args = parser.parse_args()
    root = Path(args.root)
    items = build_candidates(root)
    print_summary(items)
    if args.write:
        outputs = write_outputs(root, items)
        print(f"wrote_markdown: {outputs['markdown']}")
        print(f"wrote_jsonl: {outputs['jsonl']}")


if __name__ == "__main__":
    main()
