from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


MODULE_PATH = Path(__file__).with_name("run_context_format_eval_v2.py")


def load_module():
    spec = importlib.util.spec_from_file_location("run_context_format_eval_v2", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ContextFormatEvalV2Tests(unittest.TestCase):
    def test_build_prompts_compares_no_json_and_markdown_context(self) -> None:
        runner = load_module()
        question = "量化因子回测怎么避免未来函数和数据泄漏？"
        pack = {
            "schema": "knowledge-context-pack-v2",
            "context_quality": {"top_path": "note.md", "top_score": 7},
            "selected_chunks": [{"path": "note.md", "text": "核心证据"}],
        }
        markdown = "<context_pack>\n核心证据\n</context_pack>\n"

        prompts = runner.build_prompts(question, pack, markdown)

        self.assertEqual([item["group"] for item in prompts], ["no_context", "json_context", "markdown_context"])
        self.assertNotIn("核心证据", prompts[0]["prompt"])
        self.assertIn('"schema": "knowledge-context-pack-v2"', prompts[1]["prompt"])
        self.assertIn("<context_pack>", prompts[2]["prompt"])

    def test_dry_run_writes_three_rows(self) -> None:
        runner = load_module()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            pack_path = root / "pack.jsonl"
            markdown_path = root / "pack.md"
            out = root / "out.jsonl"
            pack_path.write_text(json.dumps({"schema": "knowledge-context-pack-v2"}, ensure_ascii=False) + "\n", encoding="utf-8")
            markdown_path.write_text("<context_pack>\n证据\n</context_pack>\n", encoding="utf-8")

            rows = runner.run_eval(
                question="问题？",
                context_pack_path=pack_path,
                markdown_context_path=markdown_path,
                out=out,
                model="test-model",
                dry_run=True,
            )

            saved = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]

        self.assertEqual(len(rows), 3)
        self.assertEqual([row["group"] for row in saved], ["no_context", "json_context", "markdown_context"])
        self.assertTrue(all(row["answer"].startswith("[DRY_RUN]") for row in saved))

    def test_read_benchmark_jsonl_requires_question(self) -> None:
        runner = load_module()
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "benchmark.jsonl"
            path.write_text(
                json.dumps({"id": "q1", "domain": "quant", "question": "问题一"}, ensure_ascii=False)
                + "\n"
                + json.dumps({"id": "q2", "domain": "machine-learning", "question": "问题二"}, ensure_ascii=False)
                + "\n",
                encoding="utf-8",
            )

            items = runner.read_benchmark_jsonl(path)

        self.assertEqual([item["id"] for item in items], ["q1", "q2"])
        self.assertEqual(items[0]["question"], "问题一")

    def test_run_benchmark_dry_run_writes_three_rows_per_question(self) -> None:
        runner = load_module()
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "vault"
            runs = root / "00-global" / "evaluation" / "runs"
            (root / "00-global").mkdir(parents=True)
            (root / "quant" / "10-standards").mkdir(parents=True)
            (root / "machine-learning" / "10-standards").mkdir(parents=True)
            for rel in [
                "00-global/current-governance-v2.md",
                "00-global/human-review-registry.md",
                "00-global/write-protection-policy.md",
                "00-global/routing-rules.md",
            ]:
                (root / rel).write_text("---\ntype: standard\nstatus: reviewed\nconfidence: high\n---\n# Global\n", encoding="utf-8")
            (root / "quant" / "10-standards" / "backtest-standards.md").write_text(
                "---\ntype: standard\ndomain: quant-factor\nstatus: reviewed\nconfidence: high\n---\n# Backtest\n未来函数 point-in-time\n",
                encoding="utf-8",
            )
            (root / "machine-learning" / "10-standards" / "leakage-prevention.md").write_text(
                "---\ntype: standard\ndomain: machine-learning\nstatus: reviewed\nconfidence: high\n---\n# Leakage\n数据泄漏 time series\n",
                encoding="utf-8",
            )
            benchmark = runs / "benchmark.jsonl"
            benchmark.parent.mkdir(parents=True)
            benchmark.write_text(
                json.dumps({"id": "q-quant", "domain": "quant", "question": "怎么避免未来函数？"}, ensure_ascii=False)
                + "\n"
                + json.dumps({"id": "q-ml", "domain": "machine-learning", "question": "怎么避免数据泄漏？"}, ensure_ascii=False)
                + "\n",
                encoding="utf-8",
            )
            out = runs / "out.jsonl"
            context_dir = runs / "contexts"

            rows = runner.run_benchmark(
                root=root,
                benchmark_path=benchmark,
                out=out,
                context_dir=context_dir,
                model="test-model",
                dry_run=True,
            )
            saved = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
            context_paths_exist = all(Path(row["context_pack_path"]).exists() for row in saved)
            markdown_paths_exist = all(Path(row["markdown_context_path"]).exists() for row in saved)

        self.assertEqual(len(rows), 6)
        self.assertEqual(len(saved), 6)
        self.assertEqual({row["question_id"] for row in saved}, {"q-quant", "q-ml"})
        self.assertEqual([row["group"] for row in saved[:3]], ["no_context", "json_context", "markdown_context"])
        self.assertTrue(context_paths_exist)
        self.assertTrue(markdown_paths_exist)


if __name__ == "__main__":
    unittest.main()
