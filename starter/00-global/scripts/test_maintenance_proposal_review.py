from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


REVIEW_PATH = Path(__file__).with_name("maintenance-proposal-review.py")
PROPOSALS_PATH = Path(__file__).with_name("maintenance-proposals.py")


def load_review():
    spec = importlib.util.spec_from_file_location("maintenance_proposal_review", REVIEW_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_proposals():
    spec = importlib.util.spec_from_file_location("maintenance_proposals", PROPOSALS_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def sample_proposal(path: str = "quant/20-notes/review.md", proposal_id: str = "proposal-review") -> dict:
    return {
        "schema": "knowledge-maintenance-proposal-v1",
        "proposal_id": proposal_id,
        "source_task_id": "task-review",
        "path": path,
        "proposal_type": "metadata_update_proposal",
        "status": "proposed",
        "rationale": "useful but draft",
        "proposed_changes": ["Review scope and boundary."],
        "evidence_needed": ["human_review"],
        "risk_notes": ["Do not apply automatically."],
        "approval_required": True,
        "created_at": "2026-05-21T00:00:00",
    }


def write_proposals(root: Path, proposals: list[dict] | None = None) -> Path:
    path = root / "00-global" / "state" / "maintenance-proposals.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = proposals or [sample_proposal()]
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    return path


def write_tasks(root: Path) -> Path:
    path = root / "00-global" / "state" / "maintenance-tasks.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema": "knowledge-maintenance-task-v1",
                "task_id": "task-review",
                "source_candidate_id": "cid-review",
                "path": "quant/20-notes/review.md",
                "task_type": "manual_knowledge_review",
                "status": "open",
                "priority": "medium",
                "reason": "useful but draft",
                "recommended_action": "Queue for manual review",
                "verification_needed": "Human review required.",
                "created_at": "2026-05-21T00:00:00",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


class MaintenanceProposalReviewTests(unittest.TestCase):
    def test_parse_compact_decisions_maps_numbers_to_approval_statuses(self) -> None:
        review = load_review()

        decisions = review.parse_decisions("1A 2C 3E")

        self.assertEqual(decisions[1], "approved")
        self.assertEqual(decisions[2], "request_changes")
        self.assertEqual(decisions[3], "deferred")

    def test_render_batch_shows_proposals_and_options(self) -> None:
        review = load_review()

        text = review.render_batch([sample_proposal()], limit=5)

        self.assertIn("### 1.", text)
        self.assertIn("metadata_update_proposal", text)
        self.assertIn("A approved", text)
        self.assertIn("E deferred", text)

    def test_write_registry_records_approval_without_mutating_inputs(self) -> None:
        review = load_review()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            proposals_path = write_proposals(root)
            task_path = write_tasks(root)
            note = root / "quant" / "20-notes" / "review.md"
            note.parent.mkdir(parents=True)
            note.write_text("---\nstatus: draft\n---\n# Draft\n", encoding="utf-8")
            before_proposals = proposals_path.read_text(encoding="utf-8")
            before_tasks = task_path.read_text(encoding="utf-8")
            before_note = note.read_text(encoding="utf-8")

            registry_path = review.write_registry_decisions(root, [sample_proposal()], {1: "approved"}, note="looks safe")

            self.assertEqual(proposals_path.read_text(encoding="utf-8"), before_proposals)
            self.assertEqual(task_path.read_text(encoding="utf-8"), before_tasks)
            self.assertEqual(note.read_text(encoding="utf-8"), before_note)
            text = registry_path.read_text(encoding="utf-8")
            self.assertIn("# Maintenance Proposal Review Registry", text)
            self.assertIn("approved", text)
            self.assertIn("proposal-review", text)

    def test_proposal_generator_filters_approved_and_marks_request_changes(self) -> None:
        review = load_review()
        proposals = load_proposals()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_tasks(root)
            approved = sample_proposal("quant/20-notes/review.md", "approved-proposal")
            changed = sample_proposal("quant/20-notes/change.md", "changed-proposal")
            review.write_registry_decisions(root, [approved], {1: "approved"})
            review.write_registry_decisions(root, [changed], {1: "request_changes"})

            filtered = proposals.apply_review_registry([approved, changed], root)

        self.assertEqual([item["proposal_id"] for item in filtered], ["changed-proposal"])
        self.assertEqual(filtered[0]["prior_review_decision"], "request_changes")

    def test_cli_writes_registry_from_proposal_jsonl(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_proposals(root)

            result = subprocess.run(
                [sys.executable, str(REVIEW_PATH), "--root", str(root), "--decisions", "1A"],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("decisions_recorded: 1", result.stdout)
            self.assertTrue((root / "00-global" / "maintenance-proposal-review-registry.md").exists())


if __name__ == "__main__":
    unittest.main()
