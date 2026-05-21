from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


MODULE_PATH = Path(__file__).with_name("improvement-review.py")
LOOP_PATH = Path(__file__).with_name("improvement-loop.py")


def load_review():
    spec = importlib.util.spec_from_file_location("improvement_review", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_loop():
    spec = importlib.util.spec_from_file_location("improvement_loop", LOOP_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def sample_candidate(path: str = "quant/20-notes/draft.md", candidate_type: str = "frequently_used_but_draft") -> dict:
    return {
        "schema": "knowledge-improvement-candidate-v1",
        "created_at": "2026-05-20T00:00:00",
        "path": path,
        "candidate_type": candidate_type,
        "severity": "medium",
        "reason": "usage_count is 3 while status remains draft",
        "suggested_action": "Review scope and evidence.",
        "requires_human_review": True,
        "metadata_snapshot": {"status": "draft"},
    }


class ImprovementReviewTests(unittest.TestCase):
    def test_candidate_id_is_stable_from_path_type_and_reason(self) -> None:
        review = load_review()
        candidate = sample_candidate()

        first = review.candidate_id(candidate)
        second = review.candidate_id({**candidate, "severity": "high", "suggested_action": "Different"})

        self.assertEqual(first, second)
        self.assertEqual(len(first), 16)

    def test_parse_compact_decisions_maps_numbers_to_statuses(self) -> None:
        review = load_review()
        decisions = review.parse_decisions("1A 2C 3E")

        self.assertEqual(decisions[1], "accepted_for_review")
        self.assertEqual(decisions[2], "deferred")
        self.assertEqual(decisions[3], "converted_to_task")

    def test_render_batch_shows_numbered_candidates_and_options(self) -> None:
        review = load_review()
        text = review.render_batch([sample_candidate()], limit=5)

        self.assertIn("### 1.", text)
        self.assertIn("frequently_used_but_draft", text)
        self.assertIn("A accepted_for_review", text)
        self.assertIn("E converted_to_task", text)

    def test_write_registry_records_decisions_without_mutating_note_or_human_registry(self) -> None:
        review = load_review()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidate = sample_candidate()
            note = root / candidate["path"]
            note.parent.mkdir(parents=True)
            note.write_text("---\nstatus: draft\n---\n# Draft\n", encoding="utf-8")
            human_registry = root / "00-global" / "human-review-registry.md"
            human_registry.parent.mkdir(parents=True)
            human_registry.write_text("# Human Review Registry\n", encoding="utf-8")
            before_note = note.read_text(encoding="utf-8")
            before_registry = human_registry.read_text(encoding="utf-8")

            registry_path = review.write_registry_decisions(root, [candidate], {1: "rejected"}, note="not useful now")

            self.assertEqual(note.read_text(encoding="utf-8"), before_note)
            self.assertEqual(human_registry.read_text(encoding="utf-8"), before_registry)
            text = registry_path.read_text(encoding="utf-8")
            self.assertIn("# Improvement Review Registry", text)
            self.assertIn("rejected", text)
            self.assertIn(review.candidate_id(candidate), text)

    def test_loop_filters_resolved_candidates_and_marks_deferred_prior_decision(self) -> None:
        review = load_review()
        loop = load_loop()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            resolved = sample_candidate("quant/20-notes/resolved.md")
            deferred = sample_candidate("quant/20-notes/deferred.md")
            review.write_registry_decisions(root, [resolved], {1: "rejected"})
            review.write_registry_decisions(root, [deferred], {1: "deferred"})

            filtered = loop.apply_review_registry([resolved, deferred], root)

        self.assertEqual([item["path"] for item in filtered], ["quant/20-notes/deferred.md"])
        self.assertEqual(filtered[0]["prior_review_decision"], "deferred")

    def test_cli_writes_registry_from_candidate_jsonl(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidate = sample_candidate()
            jsonl = root / "00-global" / "state" / "improvement-candidates.jsonl"
            jsonl.parent.mkdir(parents=True)
            jsonl.write_text(json.dumps(candidate, ensure_ascii=False) + "\n", encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(MODULE_PATH),
                    "--root",
                    str(root),
                    "--decisions",
                    "1A",
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("decisions_recorded: 1", result.stdout)
            self.assertTrue((root / "00-global" / "improvement-review-registry.md").exists())


if __name__ == "__main__":
    unittest.main()
