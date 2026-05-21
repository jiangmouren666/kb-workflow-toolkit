#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path


def append_jsonl(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def terms_for(question: str, focus: str = "") -> list[str]:
    text = f"{question} {focus}".lower()
    terms: list[str] = []
    if "自动同步" in text or "autosync" in text or "auto sync" in text:
        terms.extend(["run_auto_sync", "auto_sync"])
    if "不可写" in text or "not writable" in text or "webdav" in text:
        terms.extend(["target_writable", "not writable", "auto_sync: skipped"])
    if "未来函数" in text or "lookahead" in text:
        terms.extend(["未来函数", "lookahead", "anti-lookahead", "point-in-time"])
    if "数据泄漏" in text or "leakage" in text:
        terms.extend(["数据泄漏", "leakage", "leakage-prevention"])
    if "快速导入" in text or "quick import" in text:
        terms.extend(["Quick Import", "快速导入", "draft", "reviewed", "verified"])
    if "registry" in text or "frontmatter" in text or "reviewed" in text:
        terms.extend(["human-review-registry", "Registry Overlay", "reviewed", "verified"])
    terms.extend(term for term in re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", text) if "_" in term or len(term) >= 10)
    seen: set[str] = set()
    return [term for term in terms if not (term.lower() in seen or seen.add(term.lower()))]


def frontmatter(text: str) -> tuple[str, dict]:
    if not text.startswith("---\n"):
        return "", {}
    end = text.find("\n---\n", 4)
    if end == -1:
        return "", {}
    block = text[: end + len("\n---\n")]
    meta: dict[str, str] = {}
    for line in block.splitlines()[1:-1]:
        if ":" not in line or line.startswith((" ", "-")):
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip()
    return block, meta


def registry_entries(root: Path) -> dict[str, dict]:
    path = root / "00-global" / "human-review-registry.md"
    if not path.exists():
        return {}
    entries: dict[str, dict] = {}
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line.startswith("| `"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 2:
            continue
        rel = cells[0].strip("`")
        entries[rel] = {
            "registry_status": cells[1],
            "registry_decision": cells[2] if len(cells) > 2 else "",
            "registry_reviewed_at": cells[3] if len(cells) > 3 else "",
        }
    return entries


def overlay_metadata(meta: dict, registry_entry: dict | None) -> dict:
    if not registry_entry:
        return meta
    original = meta.get("status", "")
    merged = dict(meta)
    merged["frontmatter_status"] = original
    merged["status"] = registry_entry["registry_status"]
    merged["registry_overlay_applied"] = original != registry_entry["registry_status"]
    merged.update(registry_entry)
    return merged


GOVERNANCE_CANDIDATES = [
    "00-global/current-governance-v2.md",
    "00-global/human-review-registry.md",
    "00-global/write-protection-policy.md",
    "00-global/routing-rules.md",
]

DOMAIN_SIGNALS = {
    "quant": ["量化", "因子", "回测", "实盘", "股票", "rankic", "icir", "lookahead", "future function", "未来函数"],
    "machine-learning": ["机器学习", "模型", "训练", "特征", "leakage", "数据泄漏", "cross validation"],
    "ai-agent": ["agent", "智能体", "prompt", "工具调用", "workflow", "工作流"],
    "programming": ["代码", "debug", "部署", "api", "源码", "测试"],
    "framework-optimization": ["框架", "next.js", "react", "性能", "benchmark", "版本", "回归", "缓存"],
    "fiction-reasoning": ["小说", "剧情", "人物", "伏笔", "动机", "文本证据", "世界观"],
    "education": ["学习", "课程", "教学", "备考", "教育", "计划"],
}


def domain_candidates(question: str, focus: str = "") -> set[str]:
    text = f"{question} {focus}".lower()
    domains: set[str] = set()
    for domain, signals in DOMAIN_SIGNALS.items():
        if any(signal in text for signal in signals):
            domains.add(domain)
    return domains


def iter_candidate_files(root: Path, domains: set[str]) -> list[Path]:
    files: list[Path] = []
    for path in sorted(root.rglob("*.md")) + sorted(root.rglob("*.py")):
        rel = path.relative_to(root)
        if any(part in {".git", "__pycache__", "state", "audit-reports"} for part in rel.parts):
            continue
        if rel.parts[:2] == ("00-global", "evaluation") and path.name.startswith("manual-"):
            continue
        if rel.parts and rel.parts[0] == "00-global":
            files.append(path)
            continue
        if not domains or rel.parts[0] in domains:
            files.append(path)
    return files


def candidate_score(path: Path, root: Path, terms: list[str], domains: set[str]) -> float:
    rel = path.relative_to(root).as_posix()
    score = 0.0
    if rel in GOVERNANCE_CANDIDATES:
        score += 20
    if "10-standards" in rel:
        score += 8
    if path.name == "00-index.md":
        score += 4
    if path.name == "README.md":
        score -= 2
    parts = rel.split("/")
    if parts and parts[0] in domains:
        score += 6
    name = rel.lower()
    score += sum(2 for term in terms if term.lower() in name)
    try:
        text = path.read_text(encoding="utf-8", errors="replace").lower()
    except OSError:
        return score
    score += sum(1 for term in terms if term.lower() in text)
    return score


def discover_candidate_paths(root: Path, question: str, focus: str = "", limit: int = 12) -> list[str]:
    terms = terms_for(question, focus)
    domains = domain_candidates(question, focus)
    ranked: list[tuple[float, str]] = []
    for path in iter_candidate_files(root, domains):
        rel = path.relative_to(root).as_posix()
        score = candidate_score(path, root, terms, domains)
        if score > 0:
            ranked.append((score, rel))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    selected: list[str] = []
    for rel in GOVERNANCE_CANDIDATES:
        if (root / rel).exists() and rel not in selected:
            selected.append(rel)
    for _score, rel in ranked:
        if rel not in selected:
            selected.append(rel)
        if len(selected) >= limit:
            break
    return selected[:limit]


def markdown_sections(text: str) -> list[str]:
    lines = text.splitlines()
    sections: list[str] = []
    start = 0
    for idx, line in enumerate(lines):
        if line.startswith("#") and idx > start:
            sections.append("\n".join(lines[start:idx]))
            start = idx
    if start < len(lines):
        sections.append("\n".join(lines[start:]))
    return sections


def matching_markdown(text: str, terms: list[str], max_chars: int) -> str:
    fm, _meta = frontmatter(text)
    lowered = [term.lower() for term in terms]
    matched = [section for section in markdown_sections(text) if any(term in section.lower() for term in lowered)]
    if not matched:
        matched = [text[:max_chars]]
    return (fm + "\n" + "\n\n".join(matched[:2])).strip()[:max_chars]


def matching_windows(text: str, terms: list[str], max_chars: int, window_lines: int = 18) -> str:
    lines = text.splitlines()
    chunks: list[str] = []
    seen: set[tuple[int, int]] = set()
    for term in terms:
        term = term.lower()
        for idx, line in enumerate(lines):
            if term not in line.lower():
                continue
            start = max(0, idx - window_lines)
            end = min(len(lines), idx + window_lines + 1)
            key = (start, end)
            if key in seen:
                continue
            seen.add(key)
            chunks.append("\n".join(lines[start:end]))
            if len(chunks) >= 4:
                return "\n\n...\n\n".join(chunks)[:max_chars]
    return ("\n\n...\n\n".join(chunks) or text[:max_chars])[:max_chars]


def select_chunk(path: Path, terms: list[str], max_chars: int) -> tuple[str, str, dict]:
    text = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix == ".py":
        return matching_windows(text, terms, max_chars), "python keyword/function window", {}
    _fm, meta = frontmatter(text)
    return matching_markdown(text, terms, max_chars), "frontmatter plus matching markdown section", meta


def score_chunk(text: str, metadata: dict, terms: list[str], missing: bool = False) -> tuple[float, list[str]]:
    if missing:
        return 0.0, ["missing_evidence"]
    score = 0.0
    reasons: list[str] = []
    lowered = text.lower()
    term_hits = sum(1 for term in terms if term.lower() in lowered)
    if term_hits:
        score += term_hits * 3
        reasons.append("term_hits")
    status = metadata.get("status", "")
    if status == "verified":
        score += 4
        reasons.append("verified_status")
    elif status == "reviewed":
        score += 3
        reasons.append("reviewed_status")
    elif status == "draft":
        score -= 1
        reasons.append("draft_status")
    elif status in {"raw", "stale"}:
        score -= 2
        reasons.append(f"{status}_status")
    confidence = metadata.get("confidence", "")
    if confidence == "high":
        score += 1
        reasons.append("high_confidence")
    elif confidence == "low":
        score -= 1
        reasons.append("low_confidence")
    if metadata.get("registry_overlay_applied"):
        score += 1
        reasons.append("registry_overlay")
    return score, reasons or ["fallback_context"]


def build_context_pack(root: Path, question: str, paths: list[str] | None = None, focus: str = "", max_chars_per_file: int = 2800) -> dict:
    candidate_source = "provided"
    if paths is None:
        paths = discover_candidate_paths(root, question, focus)
        candidate_source = "auto_discovered"
    terms = terms_for(question, focus)
    registry = registry_entries(root)
    selected_chunks: list[dict] = []
    metadata_used: list[dict] = []
    missing_evidence: list[str] = []
    for rel in paths:
        path = root / rel
        if not path.exists():
            missing_evidence.append(rel)
            continue
        text, why, meta = select_chunk(path, terms, max_chars_per_file)
        effective_meta = overlay_metadata(meta, registry.get(rel))
        retrieval_score, score_reasons = score_chunk(text, effective_meta, terms)
        selected_chunks.append(
            {
                "path": rel,
                "why_selected": why,
                "retrieval_score": retrieval_score,
                "score_reasons": score_reasons,
                "text": text,
            }
        )
        if effective_meta:
            metadata_used.append({"path": rel, **effective_meta})
    selected_chunks.sort(key=lambda chunk: chunk["retrieval_score"], reverse=True)
    top_path = selected_chunks[0]["path"] if selected_chunks else ""
    return {
        "schema": "knowledge-context-pack-v2",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "question": question,
        "focus": focus,
        "retrieved_files": paths,
        "selected_chunks": selected_chunks,
        "metadata_used": metadata_used,
        "missing_evidence": missing_evidence,
        "context_quality": {
            "top_path": top_path,
            "candidate_count": len(paths),
            "selected_count": len(selected_chunks),
            "missing_evidence_count": len(missing_evidence),
            "top_score": selected_chunks[0]["retrieval_score"] if selected_chunks else 0,
            "candidate_source": candidate_source,
        },
    }


def bool_text(value: object) -> str:
    return "true" if value is True else "false" if value is False else ""


def render_markdown_context(pack: dict) -> str:
    quality = pack.get("context_quality", {})
    title_suffix = pack.get("artifact_id") or pack.get("question") or "Untitled"
    lines = [
        "---",
        "type: context-pack",
        "domain: global",
        "status: draft",
        "confidence: high",
        "evidence_level: experiment",
        "source: context_pack_builder_v2.py",
        f"updated: {datetime.now().date().isoformat()}",
        "use_for:",
        "  - answer_context",
        "  - retrieval_audit",
        "scope: generated context block for answer-router prompts",
        "should_not_use_for: treating generated snippets as canonical notes",
        "time_sensitivity: medium",
        "review_cycle: 30d",
        "---",
        "",
        f"# Context Pack V2 - {title_suffix}",
        "",
        "<context_pack>",
        "",
        "## Context Quality",
        "",
        f"- schema: `{pack.get('schema', '')}`",
        f"- candidate_source: `{quality.get('candidate_source', '')}`",
        f"- top_path: `{quality.get('top_path', '')}`",
        f"- top_score: {quality.get('top_score', 0)}",
        f"- candidate_count: {quality.get('candidate_count', 0)}",
        f"- selected_count: {quality.get('selected_count', 0)}",
        f"- missing_evidence_count: {quality.get('missing_evidence_count', 0)}",
        "",
        "## Metadata Used",
        "",
        "| Path | Status | Confidence | Evidence Level | Registry Overlay | Frontmatter Status |",
        "|---|---|---|---|---|---|",
    ]
    metadata = pack.get("metadata_used", [])
    if metadata:
        for meta in metadata:
            lines.append(
                "| "
                f"`{meta.get('path', '')}` | "
                f"{meta.get('status', '')} | "
                f"{meta.get('confidence', '')} | "
                f"{meta.get('evidence_level', '')} | "
                f"{bool_text(meta.get('registry_overlay_applied'))} | "
                f"{meta.get('frontmatter_status', '')} |"
            )
    else:
        lines.append("| None |  |  |  |  |  |")
    missing = pack.get("missing_evidence", [])
    lines.extend(["", "## Missing Evidence", ""])
    lines.extend([f"- `{path}`" for path in missing] or ["- None"])
    lines.extend(["", "## Selected Chunks", ""])
    for idx, chunk in enumerate(pack.get("selected_chunks", []), 1):
        reasons = ", ".join(chunk.get("score_reasons", []))
        lines.extend(
            [
                f"### {idx}. `{chunk.get('path', '')}`",
                "",
                f"- retrieval_score: {chunk.get('retrieval_score', 0)}",
                f"- score_reasons: {reasons}",
                f"- why_selected: {chunk.get('why_selected', '')}",
                "",
                "```text",
                chunk.get("text", "").strip(),
                "```",
                "",
            ]
        )
    lines.append("</context_pack>")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build an auditable v2 context pack.")
    parser.add_argument("--root", required=True)
    parser.add_argument("--question", required=True)
    parser.add_argument("--paths", nargs="+")
    parser.add_argument("--focus", default="")
    parser.add_argument("--max-chars-per-file", type=int, default=2800)
    parser.add_argument("--out", help="Optional JSONL output path.")
    parser.add_argument("--markdown-out", help="Optional Markdown context block output path.")
    args = parser.parse_args()

    pack = build_context_pack(Path(args.root), args.question, args.paths, focus=args.focus, max_chars_per_file=args.max_chars_per_file)
    if args.out:
        append_jsonl(Path(args.out), pack)
        print(f"context_pack_written: {args.out}")
    if args.markdown_out:
        path = Path(args.markdown_out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render_markdown_context(pack) + "\n", encoding="utf-8")
        print(f"context_markdown_written: {args.markdown_out}")
    if not args.out and not args.markdown_out:
        print(json.dumps(pack, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
