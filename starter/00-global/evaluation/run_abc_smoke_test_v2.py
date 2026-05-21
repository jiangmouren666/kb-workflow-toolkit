#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path


GROUPS = ("A", "B", "C")
DEFAULT_SYSTEM_PROMPT = "你是严谨的中文软件工程与知识库评估助手。回答要准确、简洁，不要编造不存在的依据。"


def default_vault_root() -> Path:
    return Path(__file__).resolve().parents[2]


def read_jsonl(path: Path) -> list[dict]:
    items: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            items.append(json.loads(line))
    return items


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )


def append_jsonl_row(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def completed_keys(path: Path) -> set[tuple[str, str]]:
    if not path.exists():
        return set()
    return {(row["question_id"], row["group"]) for row in read_jsonl(path) if "question_id" in row and "group" in row}


def parse_export_config(path: Path) -> dict[str, str]:
    config: dict[str, str] = {}
    if not path.exists():
        return config
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line.startswith("export ") or "=" not in line:
            continue
        key, value = line[len("export ") :].split("=", 1)
        config[key.strip()] = value.strip().strip('"').strip("'")
    return config


def load_llm_config(config_path: Path | None) -> dict[str, str]:
    config = parse_export_config(config_path) if config_path else {}
    return {
        "api_key": os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY") or config.get("LLM_API_KEY", ""),
        "base_url": os.environ.get("LLM_BASE_URL") or config.get("LLM_BASE_URL", "https://api.openai.com/v1"),
        "model": os.environ.get("LLM_MODEL") or config.get("LLM_MODEL", "gpt-4o-mini"),
    }


def read_context(vault_root: Path, paths: list[str], max_chars_per_file: int = 2800) -> str:
    chunks: list[str] = []
    for rel in paths:
        path = vault_root / rel
        if not path.exists():
            chunks.append(f"## {rel}\n[missing]")
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        chunks.append(f"## {rel}\n{text[:max_chars_per_file]}")
    return "\n\n".join(chunks)


def group_prompt(group: str, question: dict, context: str = "") -> str:
    base = question["question"]
    if group == "A":
        return base
    if group == "B":
        return f"请基于以下知识库上下文回答问题。若上下文不足，请明确说明。\n\n<context>\n{context}\n</context>\n\n问题：{base}"
    if group == "C":
        return (
            "请基于以下知识库上下文回答，并明确区分：\n"
            "1. knowledge_base_basis\n"
            "2. user_input\n"
            "3. model_reasoning\n"
            "4. uncertainty\n"
            "5. risk_or_validation_needed\n\n"
            f"<context>\n{context}\n</context>\n\n"
            f"问题：{base}"
        )
    raise ValueError(f"unknown group: {group}")


def placeholder_answer(group: str, question: dict) -> str:
    if group == "A":
        return "[PLACEHOLDER] Baseline model answer goes here. Do not use the knowledge vault."
    if group == "B":
        return "[PLACEHOLDER] Knowledge-vault answer goes here. Use relevant notes without strict output contract."
    return "[PLACEHOLDER] Governed knowledge-vault answer goes here with basis, reasoning, uncertainty, and risk."


def chat_completion(api_key: str, base_url: str, model: str, prompt: str, temperature: float, timeout: int) -> tuple[str, int | None]:
    if not api_key:
        raise RuntimeError("missing LLM API key; set LLM_API_KEY or provide --config")
    endpoint = base_url.rstrip("/")
    if not endpoint.endswith("/chat/completions"):
        endpoint = endpoint + "/chat/completions"
    body = {
        "model": model,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": DEFAULT_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    }
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {detail[:500]}") from exc
    answer = payload["choices"][0]["message"]["content"]
    usage = payload.get("usage", {})
    token_estimate = usage.get("total_tokens")
    return answer, token_estimate


def build_rows(
    dataset: list[dict],
    model: str,
    temperature: float,
    dry_run: bool,
    vault_root: Path,
    api_key: str = "",
    base_url: str = "",
    timeout: int = 120,
    completed: set[tuple[str, str]] | None = None,
    stream_out: Path | None = None,
) -> list[dict]:
    rows: list[dict] = []
    completed = completed or set()
    for question in dataset:
        for group in GROUPS:
            key = (question["question_id"], group)
            if key in completed:
                continue
            context = "" if group == "A" else read_context(vault_root, question.get("expected_knowledge_basis", []))
            prompt = group_prompt(group, question, context)
            started = time.perf_counter()
            token_estimate = None
            if dry_run:
                answer = placeholder_answer(group, question)
                latency_ms = None
            else:
                answer, token_estimate = chat_completion(api_key, base_url, model, prompt, temperature, timeout)
                latency_ms = round((time.perf_counter() - started) * 1000)
            row = {
                "question_id": question["question_id"],
                "group": group,
                "domain": question["domain"],
                "type": question["type"],
                "difficulty": question["difficulty"],
                "question": question["question"],
                "prompt": prompt,
                "answer": answer,
                "model": model,
                "temperature": temperature,
                "expected_knowledge_basis": question.get("expected_knowledge_basis", []),
                "scoring_focus": question.get("scoring_focus", ""),
                "notes_used": [],
                "latency_ms": latency_ms,
                "token_estimate": token_estimate,
                "created_at": datetime.now().isoformat(timespec="seconds"),
            }
            rows.append(row)
            if stream_out:
                append_jsonl_row(stream_out, row)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Run resumable A/B/C smoke-test prompts and raw output JSONL.")
    parser.add_argument("--dataset", required=True, help="Input question JSONL.")
    parser.add_argument("--out", required=True, help="Output JSONL.")
    parser.add_argument("--root", default=str(default_vault_root()), help="Knowledge vault root for context files.")
    parser.add_argument("--config", help="Optional shell export config file, e.g. /data/text.py.")
    parser.add_argument("--model", help="Model name; defaults to LLM_MODEL/config.")
    parser.add_argument("--temperature", type=float, default=0.1)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--dry-run", action="store_true", help="Write prompts and placeholder answers only.")
    parser.add_argument("--resume", action="store_true", help="Skip question/group pairs already present in --out.")
    args = parser.parse_args()

    dataset = read_jsonl(Path(args.dataset))
    out = Path(args.out)
    config = load_llm_config(Path(args.config) if args.config else None)
    model = args.model or config["model"]
    done = completed_keys(out) if args.resume else set()
    if not args.resume and out.exists():
        out.unlink()
    rows = build_rows(
        dataset,
        model,
        args.temperature,
        dry_run=args.dry_run,
        vault_root=Path(args.root),
        api_key=config["api_key"],
        base_url=config["base_url"],
        timeout=args.timeout,
        completed=done,
        stream_out=out,
    )
    print(f"questions: {len(dataset)}")
    print(f"rows: {len(rows)}")
    print(f"out: {args.out}")


if __name__ == "__main__":
    main()
