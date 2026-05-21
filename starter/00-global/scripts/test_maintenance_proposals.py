from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


MODULE_PATH = Path(__file__).with_name("maintenance-proposals.py")


def load_module():
    spec = importlib.util.spec_from_file_location("maintenance_proposals", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def task_rows() -> list[dict]:
    return [
        {
            "schema": "knowledge-maintenance-task-v1",
            "task_id": "task-review",
            "source_candidate_id": "cid-review",
            "path": "quant/20-notes/review.md",
            "task_type": "manual_knowledge_review",
            "status": "open",
            "priority": "medium",
            "reason": "useful but draft",
            "recommended_action": "Queue for manual knowledge maintenance",
            "verification_needed": "Human review should confirm scope.",
            "created_at": "2026-05-21T00:00:00",
        },
        {
            "schema": "knowledge-maintenance-task-v1",
            "task_id": "task-evidence",
            "source_candidate_id": "cid-evidence",
            "path": "machine-learning/20-notes/evidence.md",
            "task_type": "evidence_collection",
            "status": "open",
            "priority": "high",
            "reason": "weak evidence",
            "recommended_action": "Collect source evidence",
            "verification_needed": "Collect official docs or experiments.",
            "created_at": "2026-05-21T00:00:00",
        },
        {
            "schema": "knowledge-maintenance-task-v1",
            "task_id": "task-external",
            "source_candidate_id": "cid-task",
            "path": "ai-agent/20-notes/task.md",
            "task_type": "external_task",
            "status": "open",
            "priority": "medium",
            "reason": "needs rewrite",
            "recommended_action": "Track externally",
            "verification_needed": "Bring results back as evidence.",
            "created_at": "2026-05-21T00:00:00",
        },
        {
            "schema": "knowledge-maintenance-task-v1",
            "task_id": "task-closed",
            "source_candidate_id": "cid-closed",
            "path": "quant/20-notes/closed.md",
            "task_type": "manual_knowledge_review",
            "status": "done",
            "priority": "low",
            "reason": "closed",
            "recommended_action": "No action",
            "verification_needed": "None",
            "created_at": "2026-05-21T00:00:00",
        },
    ]


def write_tasks(root: Path, rows: list[dict] | None = None) -> Path:
    path = root / "00-global" / "state" / "maintenance-tasks.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in (rows or task_rows())), encoding="utf-8")
    return path


class MaintenanceProposalsTests(unittest.TestCase):
    def test_generates_proposals_for_open_tasks_only(self) -> None:
        proposals = load_module()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_tasks(root)

            generated = proposals.generate_proposals(root)

        self.assertEqual(
            {item["proposal_type"] for item in generated},
            {"metadata_update_proposal", "evidence_collection_plan", "external_task_brief"},
        )
        self.assertEqual({item["source_task_id"] for item in generated}, {"task-review", "task-evidence", "task-external"})
        self.assertTrue(all(item["status"] == "proposed" for item in generated))
        self.assertTrue(all(item["approval_required"] is True for item in generated))
        self.assertTrue(all(len(item["proposal_id"]) == 16 for item in generated))

    def test_proposal_id_is_stable_and_deduplicates_existing_proposals(self) -> None:
        proposals = load_module()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_tasks(root)
            first = proposals.generate_proposals(root)
            outputs = proposals.write_outputs(root, first)
            second = proposals.generate_proposals(root)

            review_proposal = next(item for item in first if item["source_task_id"] == "task-review")
            self.assertEqual(
                review_proposal["proposal_id"],
                proposals.proposal_id("task-review", "manual_knowledge_review", review_proposal["path"]),
            )
            self.assertEqual(second, [])
            self.assertTrue(outputs["markdown"].exists())
            self.assertTrue(outputs["jsonl"].exists())

    def test_write_outputs_does_not_mutate_note_task_queue_or_registry(self) -> None:
        proposals = load_module()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            note = root / "quant" / "20-notes" / "review.md"
            note.parent.mkdir(parents=True)
            note.write_text("---\nstatus: draft\n---\n# Draft\n", encoding="utf-8")
            task_path = write_tasks(root)
            review_registry = root / "00-global" / "improvement-review-registry.md"
            review_registry.parent.mkdir(parents=True, exist_ok=True)
            review_registry.write_text("# Improvement Review Registry\n", encoding="utf-8")
            before_note = note.read_text(encoding="utf-8")
            before_tasks = task_path.read_text(encoding="utf-8")
            before_registry = review_registry.read_text(encoding="utf-8")

            outputs = proposals.write_outputs(root, proposals.generate_proposals(root))

            self.assertEqual(note.read_text(encoding="utf-8"), before_note)
            self.assertEqual(task_path.read_text(encoding="utf-8"), before_tasks)
            self.assertEqual(review_registry.read_text(encoding="utf-8"), before_registry)
            self.assertIn("# Maintenance Proposals", outputs["markdown"].read_text(encoding="utf-8"))
            rows = [json.loads(line) for line in outputs["jsonl"].read_text(encoding="utf-8").splitlines()]
            self.assertEqual(rows[0]["schema"], "knowledge-maintenance-proposal-v1")

    def test_cli_generate_dry_run_does_not_write_outputs(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_tasks(root)

            result = subprocess.run(
                [sys.executable, str(MODULE_PATH), "--root", str(root), "generate"],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("proposal_count: 3", result.stdout)
            self.assertFalse((root / "00-global" / "maintenance-proposals.md").exists())
            self.assertFalse((root / "00-global" / "state" / "maintenance-proposals.jsonl").exists())

    def test_cli_list_reads_existing_proposals(self) -> None:
        proposals = load_module()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_tasks(root)
            proposals.write_outputs(root, proposals.generate_proposals(root))

            result = subprocess.run(
                [sys.executable, str(MODULE_PATH), "--root", str(root), "list"],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("proposal_count: 3", result.stdout)
            self.assertIn("metadata_update_proposal", result.stdout)


if __name__ == "__main__":
    unittest.main()
