from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


MODULE_PATH = Path(__file__).with_name("run_abc_smoke_test_v2.py")


def load_module():
    spec = importlib.util.spec_from_file_location("run_abc_smoke_test", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class RunnerPersistenceTests(unittest.TestCase):
    def test_append_jsonl_row_creates_parent_and_appends(self) -> None:
        runner = load_module()
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "nested" / "out.jsonl"
            runner.append_jsonl_row(path, {"question_id": "Q001", "group": "A"})
            runner.append_jsonl_row(path, {"question_id": "Q001", "group": "B"})

            rows = runner.read_jsonl(path)

        self.assertEqual([row["group"] for row in rows], ["A", "B"])

    def test_completed_keys_reads_existing_question_group_pairs(self) -> None:
        runner = load_module()
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "out.jsonl"
            runner.write_jsonl(path, [{"question_id": "Q001", "group": "A"}])

            keys = runner.completed_keys(path)

        self.assertEqual(keys, {("Q001", "A")})

    def test_build_rows_can_resume_and_stream_remaining_rows(self) -> None:
        runner = load_module()
        dataset = [
            {
                "question_id": "Q001",
                "type": "process",
                "difficulty": "easy",
                "domain": "global",
                "question": "测试问题？",
                "expected_knowledge_basis": [],
                "scoring_focus": "resume behavior",
            }
        ]
        with TemporaryDirectory() as tmp:
            out = Path(tmp) / "out.jsonl"
            runner.write_jsonl(out, [{"question_id": "Q001", "group": "A"}])
            rows = runner.build_rows(
                dataset,
                model="test-model",
                temperature=0.1,
                dry_run=True,
                vault_root=Path(tmp),
                completed={("Q001", "A")},
                stream_out=out,
            )

            written = runner.read_jsonl(out)

        self.assertEqual([row["group"] for row in rows], ["B", "C"])
        self.assertEqual([row["group"] for row in written], ["A", "B", "C"])


if __name__ == "__main__":
    unittest.main()
