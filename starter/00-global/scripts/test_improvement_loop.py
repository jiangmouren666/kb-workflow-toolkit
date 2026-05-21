from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


MODULE_PATH = Path(__file__).with_name("improvement-loop.py")


def load_module():
    spec = importlib.util.spec_from_file_location("improvement_loop", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_note(path: Path, frontmatter: str, body: str = "# Note\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{frontmatter.strip()}\n---\n\n{body}", encoding="utf-8")


class ImprovementLoopTests(unittest.TestCase):
    def test_candidates_capture_metadata_and_do_not_mutate_notes(self) -> None:
        loop = load_module()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            note = root / "quant" / "20-notes" / "draft-factor.md"
            write_note(
                note,
                """
type: note
domain: quant
status: draft
confidence: medium
evidence_level: source_claim
source: test
updated: 2026-05-20
usage_count: 5
time_sensitivity: high
review_cycle: 30d
""",
                body="# Draft Factor\nUsed often but still draft.\n",
            )
            before = note.read_text(encoding="utf-8")

            candidates = loop.build_candidates(root)

            self.assertEqual(note.read_text(encoding="utf-8"), before)
            self.assertTrue(any(item["candidate_type"] == "frequently_used_but_draft" for item in candidates))
            candidate = next(item for item in candidates if item["candidate_type"] == "frequently_used_but_draft")
            self.assertEqual(candidate["path"], "quant/20-notes/draft-factor.md")
            self.assertEqual(candidate["severity"], "medium")
            self.assertTrue(candidate["requires_human_review"])
            self.assertEqual(candidate["metadata_snapshot"]["status"], "draft")
            self.assertIn("suggested_action", candidate)

    def test_detects_stale_negative_feedback_and_weak_verified_evidence(self) -> None:
        loop = load_module()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_note(
                root / "ai-agent" / "20-notes" / "stale-agent.md",
                """
type: note
domain: ai-agent
status: reviewed
confidence: high
evidence_level: user_experience
source: test
updated: 2025-01-01
time_sensitivity: high
review_cycle: 30d
usage_count: 1
last_feedback: stale
""",
            )
            write_note(
                root / "machine-learning" / "20-notes" / "weak-verified.md",
                """
type: note
domain: machine-learning
status: verified
confidence: high
evidence_level: source_claim
source: test
updated: 2026-05-20
usage_count: 0
""",
            )

            types = {item["candidate_type"] for item in loop.build_candidates(root)}

        self.assertIn("stale_high_risk", types)
        self.assertIn("negative_feedback", types)
        self.assertIn("missing_evidence_for_verified", types)

    def test_context_run_low_quality_signals_become_candidates(self) -> None:
        loop = load_module()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            runs = root / "00-global" / "evaluation" / "runs"
            runs.mkdir(parents=True)
            (runs / "context.jsonl").write_text(
                json.dumps(
                    {
                        "question_id": "q-low",
                        "question": "缺少证据的问题",
                        "context_pack_path": str(runs / "pack.jsonl"),
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            (runs / "pack.jsonl").write_text(
                json.dumps(
                    {
                        "context_quality": {
                            "top_path": "",
                            "top_score": 0,
                            "selected_count": 0,
                            "missing_evidence_count": 2,
                        },
                        "missing_evidence": ["missing.md"],
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )

            candidates = loop.build_candidates(root)

        context_candidates = [item for item in candidates if item["candidate_type"] == "low_quality_context_signal"]
        self.assertEqual(len(context_candidates), 1)
        self.assertEqual(context_candidates[0]["path"], "00-global/evaluation/runs/context.jsonl")
        self.assertEqual(context_candidates[0]["severity"], "medium")

    def test_write_outputs_markdown_and_jsonl_without_changing_note(self) -> None:
        loop = load_module()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            note = root / "quant" / "20-notes" / "feedback.md"
            write_note(
                note,
                """
type: note
domain: quant
status: reviewed
confidence: medium
evidence_level: user_experience
source: test
updated: 2026-05-20
last_feedback: incomplete
""",
            )
            before = note.read_text(encoding="utf-8")

            result = loop.write_outputs(root, loop.build_candidates(root))

            self.assertEqual(note.read_text(encoding="utf-8"), before)
            self.assertTrue(result["markdown"].exists())
            self.assertTrue(result["jsonl"].exists())
            self.assertIn("# Improvement Candidates", result["markdown"].read_text(encoding="utf-8"))
            rows = [json.loads(line) for line in result["jsonl"].read_text(encoding="utf-8").splitlines()]
            self.assertTrue(rows)
            self.assertEqual(rows[0]["schema"], "knowledge-improvement-candidate-v1")

    def test_cli_dry_run_does_not_write_outputs(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_note(
                root / "quant" / "20-notes" / "draft.md",
                """
type: note
domain: quant
status: draft
confidence: low
evidence_level: source_claim
source: test
updated: 2026-05-20
usage_count: 3
""",
            )

            result = subprocess.run(
                [sys.executable, str(MODULE_PATH), "--root", str(root)],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("candidate_count:", result.stdout)
            self.assertFalse((root / "00-global" / "improvement-candidates.md").exists())
            self.assertFalse((root / "00-global" / "state" / "improvement-candidates.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
