from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


MODULE_PATH = Path(__file__).with_name("maintenance-tasks.py")


def load_module():
    spec = importlib.util.spec_from_file_location("maintenance_tasks", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def registry_text() -> str:
    return """---
type: registry
domain: global
status: draft
confidence: high
source: improvement-review.py
updated: 2026-05-21
---

# Improvement Review Registry

| Candidate ID | Path | Candidate Type | Decision | Reviewed At | Reason | Next Action |
|---|---|---|---|---|---|---|
| `cid-review` | `quant/20-notes/review.md` | frequently_used_but_draft | accepted_for_review | 2026-05-21 | useful but draft | Queue for manual knowledge maintenance |
| `cid-evidence` | `ml/20-notes/evidence.md` | missing_evidence_for_verified | needs_more_evidence | 2026-05-21 | weak evidence | Collect source evidence |
| `cid-task` | `ai-agent/20-notes/task.md` | negative_feedback | converted_to_task | 2026-05-21 | needs rewrite | Track externally |
| `cid-deferred` | `quant/20-notes/deferred.md` | stale_high_risk | deferred | 2026-05-21 | later | Revisit later |
| `cid-rejected` | `quant/20-notes/rejected.md` | conflict_candidate | rejected | 2026-05-21 | false alarm | Suppress |
"""


class MaintenanceTasksTests(unittest.TestCase):
    def test_generates_tasks_for_actionable_review_decisions_only(self) -> None:
        tasks = load_module()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry = root / "00-global" / "improvement-review-registry.md"
            registry.parent.mkdir(parents=True)
            registry.write_text(registry_text(), encoding="utf-8")

            generated = tasks.generate_tasks(root)

        self.assertEqual({item["task_type"] for item in generated}, {"manual_knowledge_review", "evidence_collection", "external_task"})
        self.assertEqual({item["source_candidate_id"] for item in generated}, {"cid-review", "cid-evidence", "cid-task"})
        self.assertTrue(all(item["status"] == "open" for item in generated))
        self.assertTrue(all(len(item["task_id"]) == 16 for item in generated))

    def test_task_id_is_stable_and_deduplicates_existing_tasks(self) -> None:
        tasks = load_module()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry = root / "00-global" / "improvement-review-registry.md"
            registry.parent.mkdir(parents=True)
            registry.write_text(registry_text(), encoding="utf-8")
            first = tasks.generate_tasks(root)
            outputs = tasks.write_outputs(root, first)
            second = tasks.generate_tasks(root)

            review_task = next(item for item in first if item["source_candidate_id"] == "cid-review")
            self.assertEqual(review_task["task_id"], tasks.task_id("cid-review", "accepted_for_review", review_task["path"]))
            self.assertEqual(second, [])
            self.assertTrue(outputs["markdown"].exists())
            self.assertTrue(outputs["jsonl"].exists())

    def test_write_outputs_does_not_mutate_note_or_review_registry(self) -> None:
        tasks = load_module()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            note = root / "quant" / "20-notes" / "review.md"
            note.parent.mkdir(parents=True)
            note.write_text("---\nstatus: draft\n---\n# Draft\n", encoding="utf-8")
            registry = root / "00-global" / "improvement-review-registry.md"
            registry.parent.mkdir(parents=True)
            registry.write_text(registry_text(), encoding="utf-8")
            before_note = note.read_text(encoding="utf-8")
            before_registry = registry.read_text(encoding="utf-8")

            outputs = tasks.write_outputs(root, tasks.generate_tasks(root))

            self.assertEqual(note.read_text(encoding="utf-8"), before_note)
            self.assertEqual(registry.read_text(encoding="utf-8"), before_registry)
            self.assertIn("# Maintenance Tasks", outputs["markdown"].read_text(encoding="utf-8"))
            rows = [json.loads(line) for line in outputs["jsonl"].read_text(encoding="utf-8").splitlines()]
            self.assertEqual(rows[0]["schema"], "knowledge-maintenance-task-v1")

    def test_cli_generate_dry_run_does_not_write_outputs(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry = root / "00-global" / "improvement-review-registry.md"
            registry.parent.mkdir(parents=True)
            registry.write_text(registry_text(), encoding="utf-8")

            result = subprocess.run(
                [sys.executable, str(MODULE_PATH), "--root", str(root), "generate"],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("task_count: 3", result.stdout)
            self.assertFalse((root / "00-global" / "maintenance-tasks.md").exists())
            self.assertFalse((root / "00-global" / "state" / "maintenance-tasks.jsonl").exists())

    def test_cli_list_reads_existing_tasks(self) -> None:
        tasks = load_module()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry = root / "00-global" / "improvement-review-registry.md"
            registry.parent.mkdir(parents=True)
            registry.write_text(registry_text(), encoding="utf-8")
            tasks.write_outputs(root, tasks.generate_tasks(root))

            result = subprocess.run(
                [sys.executable, str(MODULE_PATH), "--root", str(root), "list"],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("task_count: 3", result.stdout)
            self.assertIn("manual_knowledge_review", result.stdout)


if __name__ == "__main__":
    unittest.main()
