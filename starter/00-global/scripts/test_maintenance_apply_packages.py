from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


MODULE_PATH = Path(__file__).with_name("maintenance-apply-packages.py")


def load_module():
    spec = importlib.util.spec_from_file_location("maintenance_apply_packages", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def sample_draft(draft_id: str = "draft-ready", path: str = "quant/20-notes/seed.md", change_type: str = "metadata_change_draft") -> dict:
    return {
        "schema": "knowledge-maintenance-change-draft-v1",
        "draft_id": draft_id,
        "proposal_id": f"proposal-{draft_id}",
        "source_task_id": f"task-{draft_id}",
        "path": path,
        "proposal_type": "metadata_update_proposal",
        "change_type": change_type,
        "status": "draft",
        "summary": "ready for package preview",
        "draft_steps": ["Open the target note and compare metadata."],
        "suggested_changes": ["Review scope and metadata."],
        "evidence_to_check": ["human_review"],
        "risk_notes": ["Do not apply automatically."],
        "approved_at": "2026-05-21T00:00:00",
        "approval_reason": "proposal approved",
        "final_approval_required": True,
        "created_at": "2026-05-21T00:00:00",
    }


def write_drafts(root: Path, drafts: list[dict]) -> Path:
    path = root / "00-global" / "state" / "maintenance-change-drafts.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in drafts), encoding="utf-8")
    return path


def write_final_review_registry(root: Path, rows: list[tuple[str, str]]) -> Path:
    path = root / "00-global" / "maintenance-change-draft-review-registry.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Maintenance Change Draft Review Registry",
        "",
        "| Draft ID | Proposal ID | Path | Change Type | Decision | Reviewed At | Reason | Apply Constraints |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for draft_id, decision in rows:
        lines.append(f"| {draft_id} | proposal-{draft_id} | quant/20-notes/seed.md | metadata_change_draft | {decision} | 2026-05-21T00:00:00 | test | constraints |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_note(root: Path, relpath: str = "quant/20-notes/seed.md", text: str = "---\nstatus: draft\n---\n# Seed\n") -> Path:
    path = root / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


class MaintenanceApplyPackageTests(unittest.TestCase):
    def test_generate_packages_uses_only_ready_to_apply_drafts(self) -> None:
        module = load_module()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_note(root)
            write_drafts(root, [sample_draft("ready"), sample_draft("rejected"), sample_draft("deferred")])
            write_final_review_registry(root, [("ready", "ready_to_apply"), ("rejected", "rejected"), ("deferred", "deferred")])

            packages = module.generate_packages(root)

        self.assertEqual([item["draft_id"] for item in packages], ["ready"])
        self.assertEqual(packages[0]["schema"], "knowledge-maintenance-apply-package-v1")
        self.assertEqual(packages[0]["status"], "ready_preview")
        self.assertTrue(packages[0]["apply_requires_explicit_confirmation"])

    def test_package_id_is_stable_for_same_draft(self) -> None:
        module = load_module()

        first = module.package_id("draft-1", "metadata_change_draft", "quant/20-notes/seed.md")
        second = module.package_id("draft-1", "metadata_change_draft", "quant/20-notes/seed.md")

        self.assertEqual(first, second)
        self.assertEqual(len(first), 16)

    def test_package_records_target_sha256(self) -> None:
        module = load_module()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            note_text = "---\nstatus: draft\n---\n# Seed\n"
            write_note(root, text=note_text)
            draft = sample_draft("ready")

            package = module.package_from_draft(root, draft)

        expected_sha = hashlib.sha256(note_text.encode("utf-8")).hexdigest()
        self.assertEqual(package["target_sha256"], expected_sha)
        self.assertTrue(package["target_exists"])
        self.assertIn("target_exists", package["preflight_checks"])

    def test_missing_target_generates_blocked_package_without_creating_note(self) -> None:
        module = load_module()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            draft = sample_draft("missing", "quant/20-notes/missing.md")

            package = module.package_from_draft(root, draft)

            self.assertFalse((root / "quant" / "20-notes" / "missing.md").exists())

        self.assertEqual(package["status"], "blocked_missing_target")
        self.assertFalse(package["target_exists"])
        self.assertEqual(package["target_sha256"], "")

    def test_invalid_target_path_is_blocked_without_reading_outside_vault(self) -> None:
        module = load_module()
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "vault"
            root.mkdir()
            outside = Path(tmp) / "outside.md"
            outside.write_text("secret", encoding="utf-8")
            draft = sample_draft("escape", "../outside.md")

            package = module.package_from_draft(root, draft)

        self.assertEqual(package["status"], "blocked_invalid_target_path")
        self.assertFalse(package["target_exists"])
        self.assertEqual(package["target_sha256"], "")

    def test_absolute_and_non_markdown_target_paths_are_blocked(self) -> None:
        module = load_module()
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "vault"
            root.mkdir()

            absolute = module.package_from_draft(root, sample_draft("absolute", str(Path(tmp) / "outside.md")))
            non_markdown = module.package_from_draft(root, sample_draft("text", "quant/20-notes/seed.txt"))

        self.assertEqual(absolute["status"], "blocked_invalid_target_path")
        self.assertEqual(non_markdown["status"], "blocked_invalid_target_path")

    def test_registry_mismatch_generates_blocked_package(self) -> None:
        module = load_module()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_note(root)
            write_drafts(root, [sample_draft("ready", "quant/20-notes/seed.md")])
            registry = root / "00-global" / "maintenance-change-draft-review-registry.md"
            registry.parent.mkdir(parents=True, exist_ok=True)
            registry.write_text(
                "# Maintenance Change Draft Review Registry\n\n"
                "| Draft ID | Proposal ID | Path | Change Type | Decision | Reviewed At | Reason | Apply Constraints |\n"
                "| --- | --- | --- | --- | --- | --- | --- | --- |\n"
                "| ready | proposal-ready | quant/20-notes/other.md | metadata_change_draft | ready_to_apply | 2026-05-21T00:00:00 | test | constraints |\n",
                encoding="utf-8",
            )

            packages = module.generate_packages(root)

        self.assertEqual(len(packages), 1)
        self.assertEqual(packages[0]["status"], "blocked_review_mismatch")
        self.assertTrue(packages[0]["review_mismatch"])

    def test_registry_proposal_or_change_type_mismatch_blocks_package(self) -> None:
        module = load_module()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_note(root)
            write_drafts(root, [sample_draft("ready", "quant/20-notes/seed.md")])
            registry = root / "00-global" / "maintenance-change-draft-review-registry.md"
            registry.parent.mkdir(parents=True, exist_ok=True)
            registry.write_text(
                "# Maintenance Change Draft Review Registry\n\n"
                "| Draft ID | Proposal ID | Path | Change Type | Decision | Reviewed At | Reason | Apply Constraints |\n"
                "| --- | --- | --- | --- | --- | --- | --- | --- |\n"
                "| ready | wrong-proposal | quant/20-notes/seed.md | evidence_collection_draft | ready_to_apply | 2026-05-21T00:00:00 | test | constraints |\n",
                encoding="utf-8",
            )

            packages = module.generate_packages(root)

        self.assertEqual(packages[0]["status"], "blocked_review_mismatch")
        self.assertTrue(packages[0]["review_mismatch"])

    def test_write_outputs_does_not_mutate_note_draft_or_registry(self) -> None:
        module = load_module()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            note = write_note(root)
            drafts_path = write_drafts(root, [sample_draft("ready")])
            registry_path = write_final_review_registry(root, [("ready", "ready_to_apply")])
            before_note = note.read_text(encoding="utf-8")
            before_drafts = drafts_path.read_text(encoding="utf-8")
            before_registry = registry_path.read_text(encoding="utf-8")

            outputs = module.write_outputs(root, module.generate_packages(root))

            self.assertEqual(note.read_text(encoding="utf-8"), before_note)
            self.assertEqual(drafts_path.read_text(encoding="utf-8"), before_drafts)
            self.assertEqual(registry_path.read_text(encoding="utf-8"), before_registry)
            self.assertTrue(outputs["markdown"].exists())
            self.assertTrue(outputs["jsonl"].exists())

    def test_write_outputs_removes_packages_that_are_no_longer_ready(self) -> None:
        module = load_module()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_note(root)
            write_drafts(root, [sample_draft("ready")])
            write_final_review_registry(root, [("ready", "ready_to_apply")])
            module.write_outputs(root, module.generate_packages(root))
            registry = root / "00-global" / "maintenance-change-draft-review-registry.md"
            registry.write_text(
                "# Maintenance Change Draft Review Registry\n\n"
                "| Draft ID | Proposal ID | Path | Change Type | Decision | Reviewed At | Reason | Apply Constraints |\n"
                "| --- | --- | --- | --- | --- | --- | --- | --- |\n"
                "| ready | proposal-ready | quant/20-notes/seed.md | metadata_change_draft | rejected | 2026-05-21T00:00:00 | test | constraints |\n",
                encoding="utf-8",
            )

            module.write_outputs(root, module.generate_packages(root))

            jsonl = root / "00-global" / "state" / "maintenance-apply-packages.jsonl"
            self.assertEqual(jsonl.read_text(encoding="utf-8"), "")
            markdown = (root / "00-global" / "maintenance-apply-packages.md").read_text(encoding="utf-8")
            self.assertIn("package_count: 0", markdown)

    def test_cli_generate_and_list(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_note(root)
            write_drafts(root, [sample_draft("ready")])
            write_final_review_registry(root, [("ready", "ready_to_apply")])

            generate = subprocess.run(
                [sys.executable, str(MODULE_PATH), "--root", str(root), "generate", "--write"],
                text=True,
                capture_output=True,
                check=False,
            )
            list_result = subprocess.run(
                [sys.executable, str(MODULE_PATH), "--root", str(root), "list"],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(generate.returncode, 0, generate.stderr)
            self.assertIn("package_count: 1", generate.stdout)
            self.assertTrue((root / "00-global" / "maintenance-apply-packages.md").exists())
            self.assertEqual(list_result.returncode, 0, list_result.stderr)
            self.assertIn("metadata_change_draft", list_result.stdout)


if __name__ == "__main__":
    unittest.main()
