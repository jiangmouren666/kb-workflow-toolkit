from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


REVIEW_PATH = Path(__file__).with_name("maintenance-change-draft-review.py")
DRAFTS_PATH = Path(__file__).with_name("maintenance-change-drafts.py")


def load_review():
    spec = importlib.util.spec_from_file_location("maintenance_change_draft_review", REVIEW_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_drafts():
    spec = importlib.util.spec_from_file_location("maintenance_change_drafts", DRAFTS_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def sample_draft(path: str = "quant/20-notes/seed.md", draft_id: str = "draft-review") -> dict:
    return {
        "schema": "knowledge-maintenance-change-draft-v1",
        "draft_id": draft_id,
        "proposal_id": f"proposal-{draft_id}",
        "source_task_id": f"task-{draft_id}",
        "path": path,
        "proposal_type": "metadata_update_proposal",
        "change_type": "metadata_change_draft",
        "status": "draft",
        "summary": "approved proposal needs concrete review",
        "draft_steps": ["Open the target note and compare metadata."],
        "suggested_changes": ["Review scope and metadata."],
        "evidence_to_check": ["human_review"],
        "risk_notes": ["Do not apply automatically."],
        "approved_at": "2026-05-21T00:00:00",
        "approval_reason": "test approval",
        "final_approval_required": True,
        "created_at": "2026-05-21T00:00:00",
    }


def write_drafts(root: Path, drafts: list[dict] | None = None) -> Path:
    path = root / "00-global" / "state" / "maintenance-change-drafts.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = drafts or [sample_draft()]
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    return path


class MaintenanceChangeDraftReviewTests(unittest.TestCase):
    def test_parse_compact_decisions_maps_numbers_to_final_approval_statuses(self) -> None:
        review = load_review()

        decisions = review.parse_decisions("1A 2C 3E")

        self.assertEqual(decisions[1], "ready_to_apply")
        self.assertEqual(decisions[2], "request_changes")
        self.assertEqual(decisions[3], "deferred")

    def test_parse_compact_decisions_rejects_partial_invalid_tokens(self) -> None:
        review = load_review()

        with self.assertRaises(SystemExit):
            review.parse_decisions("1A 2Z")

    def test_render_batch_shows_drafts_and_options(self) -> None:
        review = load_review()

        text = review.render_batch([sample_draft()], limit=5)

        self.assertIn("### 1.", text)
        self.assertIn("metadata_change_draft", text)
        self.assertIn("A ready_to_apply", text)
        self.assertIn("E deferred", text)

    def test_write_registry_records_decision_without_mutating_inputs(self) -> None:
        review = load_review()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            drafts_path = write_drafts(root)
            note = root / "quant" / "20-notes" / "seed.md"
            note.parent.mkdir(parents=True)
            note.write_text("---\nstatus: draft\n---\n# Seed\n", encoding="utf-8")
            before_drafts = drafts_path.read_text(encoding="utf-8")
            before_note = note.read_text(encoding="utf-8")

            registry_path = review.write_registry_decisions(root, [sample_draft()], {1: "ready_to_apply"}, note="safe after review")

            self.assertEqual(drafts_path.read_text(encoding="utf-8"), before_drafts)
            self.assertEqual(note.read_text(encoding="utf-8"), before_note)
            text = registry_path.read_text(encoding="utf-8")
            self.assertIn("# Maintenance Change Draft Review Registry", text)
            self.assertIn("ready_to_apply", text)
            self.assertIn("draft-review", text)

    def test_draft_generator_filters_ready_and_marks_request_changes(self) -> None:
        review = load_review()
        drafts = load_drafts()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            ready = sample_draft("quant/20-notes/ready.md", "ready-draft")
            changed = sample_draft("quant/20-notes/change.md", "changed-draft")
            review.write_registry_decisions(root, [ready], {1: "ready_to_apply"})
            review.write_registry_decisions(root, [changed], {1: "request_changes"})

            filtered = drafts.apply_draft_review_registry([ready, changed], root)

        self.assertEqual([item["draft_id"] for item in filtered], ["changed-draft"])
        self.assertEqual(filtered[0]["prior_review_decision"], "request_changes")

    def test_change_drafts_write_preserves_raw_jsonl_after_final_review(self) -> None:
        review = load_review()
        drafts = load_drafts()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            ready = sample_draft("quant/20-notes/ready.md", "ready-draft")
            changed = sample_draft("quant/20-notes/change.md", "changed-draft")
            write_drafts(root, [ready, changed])
            review.write_registry_decisions(root, [ready], {1: "ready_to_apply"})
            review.write_registry_decisions(root, [changed], {1: "request_changes"})
            before_jsonl = (root / "00-global" / "state" / "maintenance-change-drafts.jsonl").read_text(encoding="utf-8")

            drafts.write_outputs(root, [])

            after_jsonl = (root / "00-global" / "state" / "maintenance-change-drafts.jsonl").read_text(encoding="utf-8")
            self.assertEqual(after_jsonl, before_jsonl)
            markdown = (root / "00-global" / "maintenance-change-drafts.md").read_text(encoding="utf-8")
            self.assertNotIn("ready-draft", markdown)
            self.assertIn("changed-draft", markdown)
            self.assertIn("prior_review_decision: `request_changes`", markdown)

    def test_change_drafts_write_does_not_persist_prior_review_fields(self) -> None:
        drafts = load_drafts()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            changed = sample_draft("quant/20-notes/change.md", "changed-draft")
            changed["prior_review_decision"] = "request_changes"
            changed["prior_reviewed_at"] = "2026-05-21T00:00:00"

            drafts.write_outputs(root, [changed])

            rows = [
                json.loads(line)
                for line in (root / "00-global" / "state" / "maintenance-change-drafts.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            self.assertEqual(rows[0]["draft_id"], "changed-draft")
            self.assertNotIn("prior_review_decision", rows[0])
            self.assertNotIn("prior_reviewed_at", rows[0])

    def test_change_drafts_list_applies_final_review_registry(self) -> None:
        review = load_review()
        drafts = load_drafts()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            ready = sample_draft("quant/20-notes/ready.md", "ready-draft")
            changed = sample_draft("quant/20-notes/change.md", "changed-draft")
            write_drafts(root, [ready, changed])
            review.write_registry_decisions(root, [ready], {1: "ready_to_apply"})
            review.write_registry_decisions(root, [changed], {1: "request_changes"})

            listed = drafts.all_drafts(root)

        self.assertEqual([item["draft_id"] for item in listed], ["changed-draft"])
        self.assertEqual(listed[0]["prior_review_decision"], "request_changes")

    def test_cli_writes_registry_from_draft_jsonl(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_drafts(root)

            result = subprocess.run(
                [sys.executable, str(REVIEW_PATH), "--root", str(root), "--decisions", "1A"],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("decisions_recorded: 1", result.stdout)
            self.assertTrue((root / "00-global" / "maintenance-change-draft-review-registry.md").exists())


if __name__ == "__main__":
    unittest.main()
