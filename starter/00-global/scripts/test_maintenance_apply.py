from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


MODULE_PATH = Path(__file__).with_name("maintenance-apply.py")


def load_module():
    spec = importlib.util.spec_from_file_location("maintenance_apply", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_note(root: Path, relpath: str = "quant/20-notes/seed.md", text: str | None = None) -> Path:
    note = root / relpath
    note.parent.mkdir(parents=True, exist_ok=True)
    note.write_text(text or "---\nstatus: draft\n---\n# Seed\n", encoding="utf-8")
    return note


def write_plan(root: Path, plan: dict) -> Path:
    path = root / "00-global" / "state" / "maintenance-apply-plans.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(plan, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return path


def base_plan(note_text: str, relpath: str = "quant/20-notes/seed.md") -> dict:
    return {
        "schema": "knowledge-maintenance-apply-plan-v1",
        "plan_id": "plan-ready",
        "path": relpath,
        "status": "ready_preview",
        "target_sha256": sha256_text(note_text),
        "safe_operations": [
            {
                "operation": "metadata_patch",
                "mode": "missing_only",
                "fields": {
                    "review_cycle": "180d",
                    "time_sensitivity": "medium",
                },
            },
            {"operation": "append_review_note"},
            {
                "operation": "split_draft_scaffold",
                "scaffolds": [
                    {
                        "path": "quant/20-notes/seed-split-notes.md",
                        "title": "Seed Split Notes",
                    }
                ],
            },
        ],
        "evidence_requirements": ["human_review", "benchmark"],
        "proposed_operations": ["Review metadata and split if needed."],
    }


class MaintenanceApplyTests(unittest.TestCase):
    def test_dry_run_does_not_modify_target_or_create_scaffold(self) -> None:
        module = load_module()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            text = "---\nstatus: draft\n---\n# Seed\n"
            note = write_note(root, text=text)
            write_plan(root, base_plan(text))

            result = module.apply_plan(root, "plan-ready", write=False, confirm="")
            self.assertEqual(result["status"], "dry_run")
            self.assertEqual(note.read_text(encoding="utf-8"), text)
            self.assertFalse((root / "quant/20-notes/seed-split-notes.md").exists())

    def test_write_requires_matching_confirmation(self) -> None:
        module = load_module()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            text = "---\nstatus: draft\n---\n# Seed\n"
            note = write_note(root, text=text)
            write_plan(root, base_plan(text))

            result = module.apply_plan(root, "plan-ready", write=True, confirm="")
            self.assertEqual(result["status"], "blocked_missing_confirmation")
            self.assertEqual(note.read_text(encoding="utf-8"), text)

    def test_hash_mismatch_blocks_apply(self) -> None:
        module = load_module()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = "---\nstatus: draft\n---\n# Seed\n"
            note = write_note(root, text=original)
            plan = base_plan(original)
            write_plan(root, plan)
            note.write_text("---\nstatus: draft\n---\n# Changed\n", encoding="utf-8")

            result = module.apply_plan(root, "plan-ready", write=True, confirm="plan-ready")
            self.assertEqual(result["status"], "blocked_target_sha256_mismatch")

    def test_confirmed_write_applies_safe_operations_and_records_rollback(self) -> None:
        module = load_module()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            text = "---\nstatus: draft\n---\n# Seed\n"
            note = write_note(root, text=text)
            write_plan(root, base_plan(text))

            result = module.apply_plan(root, "plan-ready", write=True, confirm="plan-ready")
            updated = note.read_text(encoding="utf-8")
            self.assertEqual(result["status"], "applied")
            self.assertIn("review_cycle: 180d", updated)
            self.assertIn("time_sensitivity: medium", updated)
            self.assertIn("## Maintenance Review", updated)
            self.assertTrue((root / "quant/20-notes/seed-split-notes.md").exists())
            rollback_files = list((root / "00-global" / "state" / "rollback").rglob("rollback-manifest.json"))
            self.assertEqual(len(rollback_files), 1)
            manifest = json.loads(rollback_files[0].read_text(encoding="utf-8"))
            self.assertEqual(manifest["plan_id"], "plan-ready")
            self.assertEqual(manifest["target_before_sha256"], sha256_text(text))

    def test_cli_write_applies_only_with_confirm(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            text = "---\nstatus: draft\n---\n# Seed\n"
            write_note(root, text=text)
            write_plan(root, base_plan(text))

            result = subprocess.run(
                [
                    sys.executable,
                    str(MODULE_PATH),
                    "--root",
                    str(root),
                    "--plan-id",
                    "plan-ready",
                    "--write",
                    "--confirm",
                    "plan-ready",
                ],
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("apply_status: applied", result.stdout)


if __name__ == "__main__":
    unittest.main()
