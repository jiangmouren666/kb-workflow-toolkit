#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path


def append_context_pack(path: Path, pack: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(pack, ensure_ascii=False, sort_keys=True) + "\n")


def terms_for(question: str, scoring_focus: str = "") -> list[str]:
    text = f"{question} {scoring_focus}".lower()
    terms: list[str] = []
    if "自动同步" in text or "autosync" in text or "auto sync" in text:
        terms.extend(["run_auto_sync", "auto_sync"])
    if "不可写" in text or "not writable" in text or "webdav" in text:
        terms.extend(["target_writable", "not writable", "auto_sync: skipped"])
    if "快速导入" in text or "quick import" in text:
        terms.extend(["Quick Import", "快速导入", "draft", "reviewed", "verified"])
    if "registry" in text or "frontmatter" in text:
        terms.extend(["human-review-registry", "Registry Overlay", "reviewed", "verified"])
    terms.extend(term for term in re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", text) if "_" in term or len(term) >= 10)
    seen: set[str] = set()
    return [term for term in terms if not (term.lower() in seen or seen.add(term.lower()))]


def extract_frontmatter(text: str) -> tuple[str, dict]:
    if not text.startswith("---\n"):
        return "", {}
    end = text.find("\n---\n", 4)
    if end == -1:
        return "", {}
    frontmatter = text[: end + len("\n---\n")]
    metadata: dict[str, str] = {}
    for line in frontmatter.splitlines()[1:-1]:
        if ":" not in line or line.startswith(" "):
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip()
    return frontmatter, metadata


def markdown_sections(text: str) -> list[tuple[str, str]]:
    lines = text.splitlines()
    sections: list[tuple[str, str]] = []
    start = 0
    title = "document-start"
    for idx, line in enumerate(lines):
        if line.startswith("#"):
            if idx > start:
                sections.append((title, "\n".join(lines[start:idx])))
            title = line.strip()
            start = idx
    if start < len(lines):
        sections.append((title, "\n".join(lines[start:])))
    return sections


def extract_markdown_context(path: Path, terms: list[str], max_chars: int) -> tuple[str, str, dict]:
    text = path.read_text(encoding="utf-8", errors="replace")
    frontmatter, metadata = extract_frontmatter(text)
    lowered = [term.lower() for term in terms]
    matched: list[str] = []
    for _title, section in markdown_sections(text):
        body = section.lower()
        if any(term.lower() in body for term in lowered):
            matched.append(section)
    if not matched:
        matched = [text[:max_chars]]
    selected = (frontmatter + "\n" + "\n\n".join(matched[:2])).strip()
    return selected[:max_chars], "frontmatter plus matching markdown section", metadata


def extract_windows(text: str, terms: list[str], window_lines: int = 16, max_chunks: int = 4) -> str:
    lines = text.splitlines()
    chunks: list[str] = []
    seen: set[tuple[int, int]] = set()
    for term in terms:
        lower_term = term.lower()
        for idx, line in enumerate(lines):
            if lower_term not in line.lower():
                continue
            start = max(0, idx - window_lines)
            end = min(len(lines), idx + window_lines + 1)
            key = (start, end)
            if key in seen:
                continue
            seen.add(key)
            chunks.append("\n".join(lines[start:end]))
            if len(chunks) >= max_chunks:
                return "\n\n...\n\n".join(chunks)
    return "\n\n...\n\n".join(chunks)


def extract_python_context(path: Path, terms: list[str], max_chars: int) -> tuple[str, str, dict]:
    text = path.read_text(encoding="utf-8", errors="replace")
    selected = extract_windows(text, terms, window_lines=18)
    if not selected:
        selected = text[:max_chars]
    return selected[:max_chars], "python keyword/function window", {}


def select_context(path: Path, terms: list[str], max_chars: int) -> tuple[str, str, dict]:
    if path.suffix == ".py":
        return extract_python_context(path, terms, max_chars)
    return extract_markdown_context(path, terms, max_chars)


def build_context_pack(
    vault_root: Path,
    question: str,
    candidate_paths: list[str],
    scoring_focus: str = "",
    max_chars_per_file: int = 2800,
) -> dict:
    terms = terms_for(question, scoring_focus)
    selected_chunks: list[dict] = []
    metadata_used: list[dict] = []
    missing_evidence: list[str] = []
    for rel in candidate_paths:
        path = vault_root / rel
        if not path.exists():
            missing_evidence.append(rel)
            continue
        text, reason, metadata = select_context(path, terms, max_chars_per_file)
        selected_chunks.append(
            {
                "path": rel,
                "text": text,
                "why_selected": reason,
            }
        )
        if metadata:
            metadata_used.append({"path": rel, **metadata})
    return {
        "question": question,
        "scoring_focus": scoring_focus,
        "retrieved_files": candidate_paths,
        "selected_chunks": selected_chunks,
        "metadata_used": metadata_used,
        "missing_evidence": missing_evidence,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
