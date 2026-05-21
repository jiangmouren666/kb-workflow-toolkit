#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path


DEFAULT_SYSTEM_PROMPT = "你是严谨的中文知识库评估助手。只基于给定上下文回答；上下文不足时要明确说明。"
GROUPS = ("no_context", "json_context", "markdown_context")
CONTEXT_BUILDER_PATH = Path(__file__).with_name("context_pack_builder_v2.py")


def default_vault_root() -> Path:
    return Path(__file__).resolve().parents[2]


def read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def append_jsonl(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def parse_export_config(path: Path | None) -> dict[str, str]:
    if path is None or not path.exists():
        return {}
    config: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line.startswith("export ") or "=" not in line:
            continue
        key, value = line[len("export ") :].split("=", 1)
        config[key.strip()] = value.strip().strip('"').strip("'")
    return config


def load_llm_config(config_path: Path | None) -> dict[str, str]:
    config = parse_export_config(config_path)
    return {
        "api_key": os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY") or config.get("LLM_API_KEY", ""),
        "base_url": os.environ.get("LLM_BASE_URL") or config.get("LLM_BASE_URL", "https://api.openai.com/v1"),
        "model": os.environ.get("LLM_MODEL") or config.get("LLM_MODEL", "gpt-4o-mini"),
    }


def latest_jsonl_row(path: Path) -> dict:
    rows = read_jsonl(path)
    if not rows:
        raise ValueError(f"empty JSONL: {path}")
    return rows[-1]


def read_benchmark_jsonl(path: Path) -> list[dict]:
    items = read_jsonl(path)
    for idx, item in enumerate(items, 1):
        if not item.get("question"):
            raise ValueError(f"benchmark row {idx} missing question")
        item.setdefault("id", f"q{idx:03d}")
        item.setdefault("domain", "unknown")
        item.setdefault("focus", "")
    return items


def load_context_builder(path: Path = CONTEXT_BUILDER_PATH):
    spec = importlib.util.spec_from_file_location("context_pack_builder_v2", path)
    module = importlib.util.module_from_spec(spec)
    if spec.loader is None:
        raise RuntimeError(f"cannot load context builder: {path}")
    spec.loader.exec_module(module)
    return module


def write_context_artifacts(context_dir: Path, question_id: str, pack: dict, markdown_context: str) -> tuple[Path, Path]:
    context_dir.mkdir(parents=True, exist_ok=True)
    pack_path = context_dir / f"{question_id}-context-pack.jsonl"
    markdown_path = context_dir / f"{question_id}-context-pack.md"
    pack_path.write_text(json.dumps(pack, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(markdown_context.rstrip() + "\n", encoding="utf-8")
    return pack_path, markdown_path


def build_prompts(question: str, context_pack: dict, markdown_context: str) -> list[dict]:
    json_context = json.dumps(context_pack, ensure_ascii=False, indent=2, sort_keys=True)
    return [
        {
            "group": "no_context",
            "prompt": f"请不使用知识库上下文，直接回答问题：\n\n{question}",
        },
        {
            "group": "json_context",
            "prompt": (
                "请基于以下 JSON context pack 回答问题。重点关注 context_quality、retrieval_score、metadata_used、missing_evidence。\n\n"
                f"```json\n{json_context}\n```\n\n问题：{question}"
            ),
        },
        {
            "group": "markdown_context",
            "prompt": (
                "请基于以下 Markdown context block 回答问题。若上下文不足，请明确说明。\n\n"
                f"{markdown_context}\n\n问题：{question}"
            ),
        },
    ]


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
    usage = payload.get("usage", {})
    return payload["choices"][0]["message"]["content"], usage.get("total_tokens")


def run_eval(
    question: str,
    context_pack_path: Path,
    markdown_context_path: Path,
    out: Path,
    model: str,
    dry_run: bool = False,
    api_key: str = "",
    base_url: str = "",
    temperature: float = 0.1,
    timeout: int = 120,
) -> list[dict]:
    context_pack = latest_jsonl_row(context_pack_path)
    markdown_context = markdown_context_path.read_text(encoding="utf-8")
    rows: list[dict] = []
    for item in build_prompts(question, context_pack, markdown_context):
        started = time.perf_counter()
        token_estimate = None
        if dry_run:
            answer = f"[DRY_RUN] {item['group']} answer placeholder."
            latency_ms = None
        else:
            answer, token_estimate = chat_completion(api_key, base_url, model, item["prompt"], temperature, timeout)
            latency_ms = round((time.perf_counter() - started) * 1000)
        row = {
            "group": item["group"],
            "question": question,
            "prompt": item["prompt"],
            "answer": answer,
            "model": model,
            "temperature": temperature,
            "latency_ms": latency_ms,
            "token_estimate": token_estimate,
            "context_pack_path": str(context_pack_path),
            "markdown_context_path": str(markdown_context_path),
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        rows.append(row)
        append_jsonl(out, row)
    return rows


def run_benchmark(
    root: Path,
    benchmark_path: Path,
    out: Path,
    context_dir: Path,
    model: str,
    dry_run: bool = False,
    api_key: str = "",
    base_url: str = "",
    temperature: float = 0.1,
    timeout: int = 120,
    max_chars_per_file: int = 2800,
) -> list[dict]:
    builder = load_context_builder()
    rows: list[dict] = []
    for item in read_benchmark_jsonl(benchmark_path):
        pack = builder.build_context_pack(
            root,
            item["question"],
            paths=item.get("paths"),
            focus=item.get("focus", ""),
            max_chars_per_file=max_chars_per_file,
        )
        pack["artifact_id"] = f"{context_dir.name}-{item['id']}"
        markdown_context = builder.render_markdown_context(pack)
        pack_path, markdown_path = write_context_artifacts(context_dir, item["id"], pack, markdown_context)
        item_rows = run_eval(
            question=item["question"],
            context_pack_path=pack_path,
            markdown_context_path=markdown_path,
            out=out,
            model=model,
            dry_run=dry_run,
            api_key=api_key,
            base_url=base_url,
            temperature=temperature,
            timeout=timeout,
        )
        for row in item_rows:
            row["question_id"] = item["id"]
            row["domain"] = item.get("domain", "unknown")
            row["focus"] = item.get("focus", "")
        if item_rows:
            existing = read_jsonl(out)
            rewritten = existing[: -len(item_rows)] + item_rows
            out.write_text(
                "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rewritten),
                encoding="utf-8",
            )
        rows.extend(item_rows)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare no-context, JSON-context, and Markdown-context answer prompts.")
    parser.add_argument("--question")
    parser.add_argument("--benchmark")
    parser.add_argument("--root", default=str(default_vault_root()))
    parser.add_argument("--context-dir")
    parser.add_argument("--context-pack")
    parser.add_argument("--markdown-context")
    parser.add_argument("--out", required=True)
    parser.add_argument("--config", help="Optional shell export config file.")
    parser.add_argument("--model")
    parser.add_argument("--temperature", type=float, default=0.1)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    config = load_llm_config(Path(args.config) if args.config else None)
    model = args.model or config["model"]
    out = Path(args.out)
    if out.exists():
        out.unlink()
    if args.benchmark:
        rows = run_benchmark(
            root=Path(args.root),
            benchmark_path=Path(args.benchmark),
            out=out,
            context_dir=Path(args.context_dir) if args.context_dir else out.with_suffix("").parent / "context-format-contexts",
            model=model,
            dry_run=args.dry_run,
            api_key=config["api_key"],
            base_url=config["base_url"],
            temperature=args.temperature,
            timeout=args.timeout,
        )
    else:
        if not args.question or not args.context_pack or not args.markdown_context:
            raise SystemExit("--question, --context-pack, and --markdown-context are required without --benchmark")
        rows = run_eval(
            question=args.question,
            context_pack_path=Path(args.context_pack),
            markdown_context_path=Path(args.markdown_context),
            out=out,
            model=model,
            dry_run=args.dry_run,
            api_key=config["api_key"],
            base_url=config["base_url"],
            temperature=args.temperature,
            timeout=args.timeout,
        )
    print(f"rows: {len(rows)}")
    print(f"out: {out}")


if __name__ == "__main__":
    main()
