#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path


GROUPS = ("A", "B", "C")


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


def group_prompt(group: str, question: dict) -> str:
    base = question["question"]
    if group == "A":
        return base
    if group == "B":
        return f"请基于我的知识库回答这个问题：{base}"
    if group == "C":
        return (
            "请基于知识库回答，并明确区分：\n"
            "1. knowledge_base_basis\n"
            "2. user_input\n"
            "3. model_reasoning\n"
            "4. uncertainty\n"
            "5. risk_or_validation_needed\n\n"
            f"问题：{base}"
        )
    raise ValueError(f"unknown group: {group}")


def placeholder_answer(group: str, question: dict) -> str:
    if group == "A":
        return "[PLACEHOLDER] Baseline model answer goes here. Do not use the knowledge vault."
    if group == "B":
        return "[PLACEHOLDER] Knowledge-vault answer goes here. Use relevant notes without strict output contract."
    return "[PLACEHOLDER] Governed knowledge-vault answer goes here with basis, reasoning, uncertainty, and risk."


def build_rows(dataset: list[dict], model: str, temperature: float, dry_run: bool) -> list[dict]:
    rows: list[dict] = []
    for question in dataset:
        for group in GROUPS:
            prompt = group_prompt(group, question)
            rows.append(
                {
                    "question_id": question["question_id"],
                    "group": group,
                    "domain": question["domain"],
                    "type": question["type"],
                    "difficulty": question["difficulty"],
                    "question": question["question"],
                    "prompt": prompt,
                    "answer": placeholder_answer(group, question) if dry_run else "",
                    "model": model,
                    "temperature": temperature,
                    "expected_knowledge_basis": question.get("expected_knowledge_basis", []),
                    "scoring_focus": question.get("scoring_focus", ""),
                    "notes_used": [],
                    "latency_ms": None,
                    "token_estimate": None,
                    "created_at": datetime.now().isoformat(timespec="seconds"),
                }
            )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate A/B/C smoke-test prompts and raw output JSONL.")
    parser.add_argument("--dataset", required=True, help="Input question JSONL.")
    parser.add_argument("--out", required=True, help="Output JSONL.")
    parser.add_argument("--model", default="manual-or-external-runner")
    parser.add_argument("--temperature", type=float, default=0.1)
    parser.add_argument("--dry-run", action="store_true", help="Write prompts and placeholder answers only.")
    args = parser.parse_args()

    dataset = read_jsonl(Path(args.dataset))
    rows = build_rows(dataset, args.model, args.temperature, dry_run=args.dry_run)
    write_jsonl(Path(args.out), rows)
    print(f"questions: {len(dataset)}")
    print(f"rows: {len(rows)}")
    print(f"out: {args.out}")


if __name__ == "__main__":
    main()
