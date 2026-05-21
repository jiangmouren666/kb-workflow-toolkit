from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


MODULE_PATH = Path(__file__).with_name("maintenance-change-drafts.py")


def load_module():
    spec = importlib.util.spec_from_file_location("maintenance_change_drafts", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def proposal(proposal_id: str, proposal_type: str = "metadata_update_proposal", path: str = "quant/20-notes/seed.md") -> dict:
    return {
        "schema": "knowledge-maintenance-proposal-v1",
        "proposal_id": proposal_id,
        "source_task_id": f"task-{proposal_id}",
        "path": path,
        "proposal_type": proposal_type,
        "status": "proposed",
        "rationale": "approved maintenance proposal",
        "proposed_changes": ["Review scope and metadata."],
        "evidence_needed": ["human_review"],
        "risk_notes": ["Do not apply automatically."],
        "approval_required": True,
        "created_at": "2026-05-21T00:00:00",
    }


def write_proposals(root: Path, rows: list[dict]) -> Path:
    path = root / "00-global" / "state" / "maintenance-proposals.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    return path


def write_registry(root: Path, rows: list[tuple[str, str]]) -> Path:
    path = root / "00-global" / "maintenance-proposal-review-registry.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Maintenance Proposal Review Registry",
        "",
        "| Proposal ID | Path | Proposal Type | Decision | Reviewed At | Reason | Next Action |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for proposal_id, decision in rows:
        lines.append(f"| {proposal_id} | quant/20-notes/seed.md | metadata_update_proposal | {decision} | 2026-05-21T00:00:00 | test | next |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


class MaintenanceChangeDraftTests(unittest.TestCase):
    def test_generate_drafts_uses_only_approved_proposals(self) -> None:
        module = load_module()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_proposals(root, [proposal("approved"), proposal("rejected"), proposal("deferred")])
            write_registry(root, [("approved", "approved"), ("rejected", "rejected"), ("deferred", "deferred")])

            drafts = module.generate_drafts(root)

        self.assertEqual([item["proposal_id"] for item in drafts], ["approved"])
        self.assertEqual(drafts[0]["schema"], "knowledge-maintenance-change-draft-v1")
        self.assertEqual(drafts[0]["status"], "draft")
        self.assertTrue(drafts[0]["final_approval_required"])

    def test_draft_id_is_stable_for_same_proposal(self) -> None:
        module = load_module()

        first = module.draft_id("proposal-1", "metadata_update_proposal", "quant/20-notes/seed.md")
        second = module.draft_id("proposal-1", "metadata_update_proposal", "quant/20-notes/seed.md")

        self.assertEqual(first, second)
        self.assertEqual(len(first), 16)

    def test_change_plan_depends_on_proposal_type(self) -> None:
        module = load_module()

        metadata = module.draft_from_proposal(proposal("p1", "metadata_update_proposal"))
        evidence = module.draft_from_proposal(proposal("p2", "evidence_collection_plan"))
        external = module.draft_from_proposal(proposal("p3", "external_task_brief"))

        self.assertEqual(metadata["change_type"], "metadata_change_draft")
        self.assertEqual(evidence["change_type"], "evidence_collection_draft")
        self.assertEqual(external["change_type"], "external_task_draft")

    def test_write_outputs_does_not_mutate_source_proposals_or_notes(self) -> None:
        module = load_module()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            proposals_path = write_proposals(root, [proposal("approved")])
            write_registry(root, [("approved", "approved")])
            note = root / "quant" / "20-notes" / "seed.md"
            note.parent.mkdir(parents=True)
            note.write_text("---\nstatus: draft\n---\n# Seed\n", encoding="utf-8")
            before_proposals = proposals_path.read_text(encoding="utf-8")
            before_note = note.read_text(encoding="utf-8")

            outputs = module.write_outputs(root, module.generate_drafts(root))

            self.assertEqual(proposals_path.read_text(encoding="utf-8"), before_proposals)
            self.assertEqual(note.read_text(encoding="utf-8"), before_note)
            self.assertTrue(outputs["markdown"].exists())
            self.assertTrue(outputs["jsonl"].exists())
            self.assertIn("metadata_change_draft", outputs["markdown"].read_text(encoding="utf-8"))

    def test_cli_generate_and_list(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_proposals(root, [proposal("approved")])
            write_registry(root, [("approved", "approved")])

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
            self.assertIn("draft_count: 1", generate.stdout)
            self.assertTrue((root / "00-global" / "maintenance-change-drafts.md").exists())
            self.assertEqual(list_result.returncode, 0, list_result.stderr)
            self.assertIn("metadata_change_draft", list_result.stdout)


if __name__ == "__main__":
    unittest.main()
