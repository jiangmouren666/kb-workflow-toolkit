#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


KB_PATH = Path(__file__).with_name("kb.py")
SYNC_PATH = Path(__file__).with_name("sync-vault.py")


def load_kb():
    spec = importlib.util.spec_from_file_location("kb", KB_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_sync():
    spec = importlib.util.spec_from_file_location("sync_vault", SYNC_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class KbCliTests(unittest.TestCase):
    def test_init_vault_creates_local_first_structure_and_config(self) -> None:
        kb = load_kb()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "portable-kb"

            config = kb.init_vault(root)

            self.assertEqual(config["vault_root"], str(root))
            self.assertFalse(config["sync_enabled"])
            self.assertEqual(config["sync_target"], "")
            self.assertEqual(config["schema"], "knowledge-vault-config-v1")
            self.assertTrue((root / "00-global" / "state" / "vault-config.json").exists())
            self.assertTrue((root / "00-global" / "scripts").is_dir())
            self.assertTrue((root / "quant" / "10-standards").is_dir())
            self.assertTrue((root / "fiction-reasoning" / "10-standards").is_dir())

    def test_configure_vault_updates_optional_sync_target_without_enabling_by_default(self) -> None:
        kb = load_kb()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "portable-kb"
            target = Path(tmp) / "obsidian-target"
            target.mkdir()
            kb.init_vault(root)

            config = kb.configure_vault(root, sync_target=target)

            self.assertEqual(config["sync_target"], str(target))
            self.assertFalse(config["sync_enabled"])

    def test_safety_status_reads_vault_config_as_optional_target(self) -> None:
        kb = load_kb()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "portable-kb"
            target = Path(tmp) / "missing-target"
            kb.init_vault(root, sync_target=target, sync_enabled=True)

            status = kb.sync_safety_status(root)

        self.assertEqual(status["source_of_truth"], str(root.resolve()))
        self.assertEqual(status["sync_direction"], "local_to_optional_target_only")
        self.assertTrue(status["auto_sync_enabled"])
        self.assertEqual(status["auto_sync_target"], str(target))
        self.assertEqual(status["auto_sync_target_status"], "missing")

    def test_portable_vault_smoke_runs_without_obsidian_or_cloud_target(self) -> None:
        kb = load_kb()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "portable-kb"
            kb.init_vault(root)
            note = root / "quant" / "10-standards" / "portable-quant-standard.md"
            note.write_text(
                """---
type: standard
domain: quant
status: reviewed
confidence: high
evidence_level: user_experience
source: portable-smoke-test
updated: 2026-05-20
use_for:
  - leakage_review
scope: portable smoke test note
should_not_use_for: production trading decisions
time_sensitivity: medium
review_cycle: 180d
human_review:
  reviewer: test
  decision: accepted
  reviewed_at: 2026-05-20
  result: portable local-only note
usage_count: 0
last_used:
last_feedback:
failure_modes: []
improvement_notes: []
---

# Portable Quant Standard

## Rule
- 回测必须按 point-in-time 数据约束检查未来函数和数据泄漏。
""",
                encoding="utf-8",
            )
            benchmark = Path(tmp) / "benchmark.jsonl"
            benchmark.write_text(
                json.dumps(
                    {
                        "id": "q-portable-leakage",
                        "question": "量化因子回测怎么避免未来函数和数据泄漏？",
                        "domain": "quant",
                        "focus": "未来函数 数据泄漏 point-in-time",
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            scan = subprocess.run(
                [sys.executable, str(root / "00-global" / "scripts" / "scan-vault-strict.py"), "--root", str(root)],
                text=True,
                capture_output=True,
                check=False,
            )
            context_jsonl = Path(tmp) / "context.jsonl"
            context_md = Path(tmp) / "context.md"
            context = subprocess.run(
                [
                    sys.executable,
                    str(root / "00-global" / "evaluation" / "context_pack_builder_v2.py"),
                    "--root",
                    str(root),
                    "--question",
                    "量化因子回测怎么避免未来函数和数据泄漏？",
                    "--out",
                    str(context_jsonl),
                    "--markdown-out",
                    str(context_md),
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            eval_out = Path(tmp) / "eval.jsonl"
            evaluation = subprocess.run(
                [
                    sys.executable,
                    str(root / "00-global" / "evaluation" / "run_context_format_eval_v2.py"),
                    "--benchmark",
                    str(benchmark),
                    "--root",
                    str(root),
                    "--context-dir",
                    str(Path(tmp) / "contexts"),
                    "--out",
                    str(eval_out),
                    "--dry-run",
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(scan.returncode, 0, scan.stderr)
            self.assertIn("- total_findings:", scan.stdout)
            self.assertEqual(context.returncode, 0, context.stderr)
            self.assertTrue(context_jsonl.exists())
            self.assertTrue(context_md.exists())
            self.assertIn("Portable Quant Standard", context_md.read_text(encoding="utf-8"))
            self.assertEqual(evaluation.returncode, 0, evaluation.stderr)
            self.assertEqual(len(eval_out.read_text(encoding="utf-8").splitlines()), 3)

    def test_init_and_configure_commands_accept_root_after_subcommand(self) -> None:
        kb = load_kb()
        parser = kb.build_parser()

        init_args = parser.parse_args(["init", "--root", "/tmp/portable-kb"])
        configure_args = parser.parse_args(["configure", "--root", "/tmp/portable-kb", "--sync-target", "/tmp/target"])

        self.assertEqual(init_args.root, "/tmp/portable-kb")
        self.assertEqual(configure_args.sync_target, "/tmp/target")

    def test_improve_command_accepts_root_after_subcommand(self) -> None:
        kb = load_kb()
        parser = kb.build_parser()
        args = parser.parse_args(["improve", "--root", "/tmp/portable-kb", "--write"])

        self.assertEqual(args.root, "/tmp/portable-kb")
        self.assertTrue(args.write)

    def test_review_improvements_command_accepts_root_and_decisions(self) -> None:
        kb = load_kb()
        parser = kb.build_parser()
        args = parser.parse_args(["review-improvements", "--root", "/tmp/portable-kb", "--limit", "3", "--decisions", "1A 2D"])

        self.assertEqual(args.root, "/tmp/portable-kb")
        self.assertEqual(args.limit, 3)
        self.assertEqual(args.decisions, "1A 2D")

    def test_tasks_command_accepts_nested_actions_and_write(self) -> None:
        kb = load_kb()
        parser = kb.build_parser()
        generate_args = parser.parse_args(["tasks", "generate", "--root", "/tmp/portable-kb", "--write"])
        list_args = parser.parse_args(["tasks", "list", "--root", "/tmp/portable-kb"])

        self.assertEqual(generate_args.root, "/tmp/portable-kb")
        self.assertTrue(generate_args.write)
        self.assertEqual(list_args.root, "/tmp/portable-kb")

    def test_proposals_command_accepts_nested_actions_and_write(self) -> None:
        kb = load_kb()
        parser = kb.build_parser()
        generate_args = parser.parse_args(["proposals", "generate", "--root", "/tmp/portable-kb", "--write"])
        list_args = parser.parse_args(["proposals", "list", "--root", "/tmp/portable-kb"])

        self.assertEqual(generate_args.root, "/tmp/portable-kb")
        self.assertTrue(generate_args.write)
        self.assertEqual(list_args.root, "/tmp/portable-kb")

    def test_review_proposals_command_accepts_root_and_decisions(self) -> None:
        kb = load_kb()
        parser = kb.build_parser()
        args = parser.parse_args(["review-proposals", "--root", "/tmp/portable-kb", "--limit", "4", "--decisions", "1A 2D"])

        self.assertEqual(args.root, "/tmp/portable-kb")
        self.assertEqual(args.limit, 4)
        self.assertEqual(args.decisions, "1A 2D")

    def test_change_drafts_command_accepts_nested_actions_and_write(self) -> None:
        kb = load_kb()
        parser = kb.build_parser()
        generate_args = parser.parse_args(["change-drafts", "generate", "--root", "/tmp/portable-kb", "--write"])
        list_args = parser.parse_args(["change-drafts", "list", "--root", "/tmp/portable-kb"])

        self.assertEqual(generate_args.root, "/tmp/portable-kb")
        self.assertTrue(generate_args.write)
        self.assertEqual(list_args.root, "/tmp/portable-kb")

    def test_change_drafts_write_preserves_sources_through_kb_wrapper(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scripts = root / "00-global" / "scripts"
            scripts.mkdir(parents=True, exist_ok=True)
            shutil.copy2(KB_PATH.with_name("maintenance-change-drafts.py"), scripts / "maintenance-change-drafts.py")
            proposal_path = root / "00-global" / "state" / "maintenance-proposals.jsonl"
            proposal_path.parent.mkdir(parents=True, exist_ok=True)
            proposal = {
                "schema": "knowledge-maintenance-proposal-v1",
                "proposal_id": "approved-proposal",
                "source_task_id": "task-approved",
                "path": "quant/20-notes/seed.md",
                "proposal_type": "metadata_update_proposal",
                "status": "proposed",
                "rationale": "approved maintenance proposal",
                "proposed_changes": ["Review scope and metadata."],
                "evidence_needed": ["human_review"],
                "risk_notes": ["Do not apply automatically."],
                "approval_required": True,
                "created_at": "2026-05-21T00:00:00",
            }
            proposal_path.write_text(json.dumps(proposal, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
            registry = root / "00-global" / "maintenance-proposal-review-registry.md"
            registry.write_text(
                "# Maintenance Proposal Review Registry\n\n"
                "| Proposal ID | Path | Proposal Type | Decision | Reviewed At | Reason | Next Action |\n"
                "| --- | --- | --- | --- | --- | --- | --- |\n"
                "| approved-proposal | quant/20-notes/seed.md | metadata_update_proposal | approved | 2026-05-21T00:00:00 | test | next |\n",
                encoding="utf-8",
            )
            note = root / "quant" / "20-notes" / "seed.md"
            note.parent.mkdir(parents=True)
            note.write_text("---\nstatus: draft\n---\n# Seed\n", encoding="utf-8")
            before_proposal = proposal_path.read_text(encoding="utf-8")
            before_registry = registry.read_text(encoding="utf-8")
            before_note = note.read_text(encoding="utf-8")

            result = subprocess.run(
                [sys.executable, str(KB_PATH), "change-drafts", "generate", "--root", str(root), "--write"],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("draft_count: 1", result.stdout)
            self.assertEqual(proposal_path.read_text(encoding="utf-8"), before_proposal)
            self.assertEqual(registry.read_text(encoding="utf-8"), before_registry)
            self.assertEqual(note.read_text(encoding="utf-8"), before_note)
            self.assertTrue((root / "00-global" / "maintenance-change-drafts.md").exists())
            self.assertTrue((root / "00-global" / "state" / "maintenance-change-drafts.jsonl").exists())

    def test_review_change_drafts_command_accepts_root_and_decisions(self) -> None:
        kb = load_kb()
        parser = kb.build_parser()
        args = parser.parse_args(["review-change-drafts", "--root", "/tmp/portable-kb", "--limit", "4", "--decisions", "1A 2D"])

        self.assertEqual(args.root, "/tmp/portable-kb")
        self.assertEqual(args.limit, 4)
        self.assertEqual(args.decisions, "1A 2D")

    def test_review_change_drafts_write_preserves_sources_through_kb_wrapper(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scripts = root / "00-global" / "scripts"
            scripts.mkdir(parents=True, exist_ok=True)
            shutil.copy2(KB_PATH.with_name("maintenance-change-draft-review.py"), scripts / "maintenance-change-draft-review.py")
            draft_path = root / "00-global" / "state" / "maintenance-change-drafts.jsonl"
            draft_path.parent.mkdir(parents=True, exist_ok=True)
            draft = {
                "schema": "knowledge-maintenance-change-draft-v1",
                "draft_id": "draft-approved",
                "proposal_id": "proposal-approved",
                "source_task_id": "task-approved",
                "path": "quant/20-notes/seed.md",
                "proposal_type": "metadata_update_proposal",
                "change_type": "metadata_change_draft",
                "status": "draft",
                "summary": "approved proposal needs concrete review",
                "draft_steps": ["Open the target note and compare metadata."],
                "suggested_changes": ["Review scope and metadata."],
                "evidence_to_check": ["human_review"],
                "risk_notes": ["Do not apply automatically."],
                "final_approval_required": True,
                "created_at": "2026-05-21T00:00:00",
            }
            draft_path.write_text(json.dumps(draft, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
            note = root / "quant" / "20-notes" / "seed.md"
            note.parent.mkdir(parents=True)
            note.write_text("---\nstatus: draft\n---\n# Seed\n", encoding="utf-8")
            before_draft = draft_path.read_text(encoding="utf-8")
            before_note = note.read_text(encoding="utf-8")

            result = subprocess.run(
                [sys.executable, str(KB_PATH), "review-change-drafts", "--root", str(root), "--decisions", "1A"],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("decisions_recorded: 1", result.stdout)
            self.assertEqual(draft_path.read_text(encoding="utf-8"), before_draft)
            self.assertEqual(note.read_text(encoding="utf-8"), before_note)
            self.assertTrue((root / "00-global" / "maintenance-change-draft-review-registry.md").exists())

    def test_apply_packages_command_accepts_nested_actions_and_write(self) -> None:
        kb = load_kb()
        parser = kb.build_parser()
        generate_args = parser.parse_args(["apply-packages", "generate", "--root", "/tmp/portable-kb", "--write"])
        list_args = parser.parse_args(["apply-packages", "list", "--root", "/tmp/portable-kb"])

        self.assertEqual(generate_args.root, "/tmp/portable-kb")
        self.assertTrue(generate_args.write)
        self.assertEqual(list_args.root, "/tmp/portable-kb")

    def test_apply_packages_write_preserves_sources_through_kb_wrapper(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scripts = root / "00-global" / "scripts"
            scripts.mkdir(parents=True, exist_ok=True)
            shutil.copy2(KB_PATH.with_name("maintenance-apply-packages.py"), scripts / "maintenance-apply-packages.py")
            draft_path = root / "00-global" / "state" / "maintenance-change-drafts.jsonl"
            draft_path.parent.mkdir(parents=True, exist_ok=True)
            draft = {
                "schema": "knowledge-maintenance-change-draft-v1",
                "draft_id": "draft-ready",
                "proposal_id": "proposal-ready",
                "source_task_id": "task-ready",
                "path": "quant/20-notes/seed.md",
                "proposal_type": "metadata_update_proposal",
                "change_type": "metadata_change_draft",
                "status": "draft",
                "summary": "ready for package preview",
                "draft_steps": ["Open the target note and compare metadata."],
                "suggested_changes": ["Review scope and metadata."],
                "evidence_to_check": ["human_review"],
                "risk_notes": ["Do not apply automatically."],
                "final_approval_required": True,
                "created_at": "2026-05-21T00:00:00",
            }
            draft_path.write_text(json.dumps(draft, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
            registry = root / "00-global" / "maintenance-change-draft-review-registry.md"
            registry.write_text(
                "# Maintenance Change Draft Review Registry\n\n"
                "| Draft ID | Proposal ID | Path | Change Type | Decision | Reviewed At | Reason | Apply Constraints |\n"
                "| --- | --- | --- | --- | --- | --- | --- | --- |\n"
                "| draft-ready | proposal-ready | quant/20-notes/seed.md | metadata_change_draft | ready_to_apply | 2026-05-21T00:00:00 | test | constraints |\n",
                encoding="utf-8",
            )
            note = root / "quant" / "20-notes" / "seed.md"
            note.parent.mkdir(parents=True)
            note.write_text("---\nstatus: draft\n---\n# Seed\n", encoding="utf-8")
            before_draft = draft_path.read_text(encoding="utf-8")
            before_registry = registry.read_text(encoding="utf-8")
            before_note = note.read_text(encoding="utf-8")

            result = subprocess.run(
                [sys.executable, str(KB_PATH), "apply-packages", "generate", "--root", str(root), "--write"],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("package_count: 1", result.stdout)
            self.assertEqual(draft_path.read_text(encoding="utf-8"), before_draft)
            self.assertEqual(registry.read_text(encoding="utf-8"), before_registry)
            self.assertEqual(note.read_text(encoding="utf-8"), before_note)
            self.assertTrue((root / "00-global" / "maintenance-apply-packages.md").exists())
            self.assertTrue((root / "00-global" / "state" / "maintenance-apply-packages.jsonl").exists())

    def test_maintain_command_accepts_status_plan_and_apply_stub(self) -> None:
        kb = load_kb()
        parser = kb.build_parser()
        status_args = parser.parse_args(["maintain", "status", "--root", "/tmp/portable-kb"])
        plan_args = parser.parse_args(["maintain", "plan", "--root", "/tmp/portable-kb", "--write"])
        apply_args = parser.parse_args(["maintain", "apply", "--root", "/tmp/portable-kb", "--plan-id", "plan-123"])

        self.assertEqual(status_args.root, "/tmp/portable-kb")
        self.assertEqual(plan_args.root, "/tmp/portable-kb")
        self.assertTrue(plan_args.write)
        self.assertEqual(apply_args.plan_id, "plan-123")

    def test_maintain_plan_write_preserves_sources_through_kb_wrapper(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scripts = root / "00-global" / "scripts"
            scripts.mkdir(parents=True, exist_ok=True)
            shutil.copy2(KB_PATH.with_name("maintenance-apply-plans.py"), scripts / "maintenance-apply-plans.py")
            note = root / "quant" / "20-notes" / "seed.md"
            note.parent.mkdir(parents=True)
            note.write_text("---\nstatus: draft\n---\n# Seed\n", encoding="utf-8")
            registry = root / "00-global" / "improvement-review-registry.md"
            registry.write_text(
                "# Improvement Review Registry\n\n"
                "| Candidate ID | Path | Candidate Type | Decision | Reviewed At | Reason | Next Action |\n"
                "|---|---|---|---|---|---|---|\n"
                "| `candidate-ready` | `quant/20-notes/seed.md` | frequently_used_but_draft | accepted_for_review | 2026-05-21 | reviewed | Prepare maintenance plan. |\n",
                encoding="utf-8",
            )
            before_note = note.read_text(encoding="utf-8")
            before_registry = registry.read_text(encoding="utf-8")

            result = subprocess.run(
                [sys.executable, str(KB_PATH), "maintain", "plan", "--root", str(root), "--write"],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("apply_plan_count: 1", result.stdout)
            self.assertEqual(note.read_text(encoding="utf-8"), before_note)
            self.assertEqual(registry.read_text(encoding="utf-8"), before_registry)
            self.assertTrue((root / "00-global" / "maintenance-apply-plans.md").exists())
            self.assertTrue((root / "00-global" / "state" / "maintenance-apply-plans.jsonl").exists())

    def test_maintain_apply_stub_does_not_modify_note(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            note = root / "quant" / "20-notes" / "seed.md"
            note.parent.mkdir(parents=True)
            note.write_text("---\nstatus: draft\n---\n# Seed\n", encoding="utf-8")
            before_note = note.read_text(encoding="utf-8")

            result = subprocess.run(
                [sys.executable, str(KB_PATH), "maintain", "apply", "--root", str(root), "--plan-id", "plan-123"],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("apply_status: not_implemented", result.stdout)
            self.assertEqual(note.read_text(encoding="utf-8"), before_note)

    def test_maintain_apply_write_stub_does_not_modify_note(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            note = root / "quant" / "20-notes" / "seed.md"
            note.parent.mkdir(parents=True)
            note.write_text("---\nstatus: draft\n---\n# Seed\n", encoding="utf-8")
            before_note = note.read_text(encoding="utf-8")

            result = subprocess.run(
                [sys.executable, str(KB_PATH), "maintain", "apply", "--root", str(root), "--plan-id", "plan-123", "--write"],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("apply_status: not_implemented", result.stdout)
            self.assertEqual(note.read_text(encoding="utf-8"), before_note)

    def test_manifest_diff_detects_added_modified_and_deleted_files(self) -> None:
        kb = load_kb()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.md").write_text("one", encoding="utf-8")
            old = kb.build_manifest(root)

            (root / "a.md").write_text("two", encoding="utf-8")
            (root / "b.md").write_text("new", encoding="utf-8")
            (root / "deleted.md").write_text("gone", encoding="utf-8")
            new = kb.build_manifest(root)
            old["files"]["deleted.md"] = new["files"]["deleted.md"]
            del new["files"]["deleted.md"]

            diff = kb.diff_manifests(old, new)

            self.assertEqual(diff["added"], ["b.md"])
            self.assertEqual(diff["modified"], ["a.md"])
            self.assertEqual(diff["deleted"], ["deleted.md"])

    def test_lock_refuses_active_existing_lock(self) -> None:
        kb = load_kb()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = kb.state_dir(root)
            state.mkdir(parents=True)
            lock = state / "kb.lock"
            lock.write_text('{"created_at": "2999-01-01T00:00:00", "pid": 12345}\n', encoding="utf-8")

            with self.assertRaises(SystemExit):
                with kb.acquire_lock(root):
                    pass

    def test_root_argument_can_follow_subcommand(self) -> None:
        kb = load_kb()
        parser = kb.build_parser()
        args = parser.parse_args(["status", "--root", "/tmp/example-vault"])

        self.assertEqual(args.root, "/tmp/example-vault")

    def test_root_argument_can_follow_nested_autosync_action(self) -> None:
        kb = load_kb()
        parser = kb.build_parser()
        args = parser.parse_args(["autosync", "status", "--root", "/tmp/example-vault"])

        self.assertEqual(args.root, "/tmp/example-vault")

    def test_auto_sync_config_round_trip(self) -> None:
        kb = load_kb()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "vault"
            target = Path(tmp) / "obsidian"
            root.mkdir()
            target.mkdir()

            kb.save_auto_sync_config(root, target, enabled=True)
            config = kb.load_auto_sync_config(root)

            self.assertEqual(config["target"], str(target))
            self.assertTrue(config["enabled"])

    def test_sync_excludes_runtime_state_and_python_cache(self) -> None:
        sync = load_sync()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "keep.md").write_text("keep", encoding="utf-8")
            cache = root / "00-global" / "scripts" / "__pycache__"
            cache.mkdir(parents=True)
            (cache / "kb.cpython-313.pyc").write_bytes(b"cache")
            snapshots = root / "00-global" / "state" / "snapshots"
            snapshots.mkdir(parents=True)
            (snapshots / "20260518-000000-manifest.json").write_text("{}", encoding="utf-8")

            files = [path.relative_to(root).as_posix() for path in sync.iter_files(root)]

            self.assertEqual(files, ["keep.md"])

    def test_protected_file_capture_and_restore(self) -> None:
        kb = load_kb()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            protected = root / "00-global" / "scripts" / "sync-vault.py"
            protected.parent.mkdir(parents=True)
            protected.write_text("current", encoding="utf-8")

            kb.capture_protected_files(root, [protected])
            protected.write_text("stale", encoding="utf-8")
            result = kb.restore_protected_files(root)

            self.assertEqual(result["restored"], ["00-global/scripts/sync-vault.py"])
            self.assertEqual(protected.read_text(encoding="utf-8"), "current")

    def test_protected_file_drift_detects_modified_file(self) -> None:
        kb = load_kb()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            protected = root / "00-global" / "scripts" / "kb.py"
            protected.parent.mkdir(parents=True)
            protected.write_text("current", encoding="utf-8")

            kb.capture_protected_files(root, [protected])
            protected.write_text("stale", encoding="utf-8")
            drift = kb.protected_file_drift(root)

            self.assertEqual(drift["modified"], ["00-global/scripts/kb.py"])

    def test_legacy_reverse_sync_script_detects_unsafe_rsync_pull(self) -> None:
        kb = load_kb()
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "sync-vaults.sh"
            script.write_text('rsync -av "$OBSIDIAN/" "$LOCAL/"\n', encoding="utf-8")

            status = kb.legacy_reverse_sync_script_status(script)

            self.assertEqual(status, "unsafe")

    def test_legacy_reverse_sync_script_accepts_disabled_guard(self) -> None:
        kb = load_kb()
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "sync-vaults.sh"
            script.write_text("stale Obsidian-to-local writeback\nexit 2\n", encoding="utf-8")

            status = kb.legacy_reverse_sync_script_status(script)

            self.assertEqual(status, "disabled")

    def test_sync_safety_status_reports_protected_drift_and_legacy_script(self) -> None:
        kb = load_kb()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "vault"
            root.mkdir()
            protected = root / "00-global" / "scripts" / "kb.py"
            protected.parent.mkdir(parents=True)
            protected.write_text("current", encoding="utf-8")
            legacy = Path(tmp) / "sync-vaults.sh"
            legacy.write_text('rsync -av "$OBSIDIAN/" "$LOCAL/"\n', encoding="utf-8")
            kb.capture_protected_files(root, [protected])
            protected.write_text("stale", encoding="utf-8")

            status = kb.sync_safety_status(root, legacy_script=legacy)

            self.assertEqual(status["source_of_truth"], str(root))
            self.assertEqual(status["legacy_reverse_sync_script"], "unsafe")
            self.assertEqual(status["protected_file_drift"], 1)

    def test_sync_target_status_reports_missing_target(self) -> None:
        kb = load_kb()
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "missing" / "knowledge-vaults"

            status = kb.sync_target_status(target)

        self.assertEqual(status, "missing")

    def test_sync_safety_status_includes_target_status(self) -> None:
        kb = load_kb()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "vault"
            target = Path(tmp) / "missing-target"
            root.mkdir()
            kb.save_auto_sync_config(root, target, enabled=True)

            status = kb.sync_safety_status(root)

        self.assertEqual(status["auto_sync_target_status"], "missing")


if __name__ == "__main__":
    unittest.main()
