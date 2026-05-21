from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


MODULE_PATH = Path(__file__).with_name("build-starter.py")


def load_module():
    spec = importlib.util.spec_from_file_location("build_starter", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class BuildStarterTests(unittest.TestCase):
    def test_build_starter_copies_only_template_files(self) -> None:
        builder = load_module()
        source_root = MODULE_PATH.resolve().parents[2]
        with TemporaryDirectory() as tmp:
            target = Path(tmp) / "starter"

            manifest = builder.build_starter(source_root, target)
            files = set(manifest["files"])

            self.assertIn("bootstrap-local-vault.py", files)
            self.assertIn("starter-manifest.json", files)
            self.assertIn("00-global/scripts/kb.py", files)
            self.assertIn("00-global/scripts/build-starter.py", files)
            self.assertIn("00-global/scripts/improvement-loop.py", files)
            self.assertIn("00-global/scripts/improvement-review.py", files)
            self.assertIn("00-global/scripts/maintenance-tasks.py", files)
            self.assertIn("00-global/scripts/maintenance-proposals.py", files)
            self.assertIn("00-global/scripts/maintenance-proposal-review.py", files)
            self.assertIn("00-global/scripts/maintenance-change-drafts.py", files)
            self.assertIn("00-global/scripts/maintenance-change-draft-review.py", files)
            self.assertIn("00-global/scripts/maintenance-apply-packages.py", files)
            self.assertIn("00-global/scripts/maintenance-apply-plans.py", files)
            self.assertIn("00-global/scripts/test_improvement_loop.py", files)
            self.assertIn("00-global/scripts/test_improvement_review.py", files)
            self.assertIn("00-global/scripts/test_maintenance_tasks.py", files)
            self.assertIn("00-global/scripts/test_maintenance_proposals.py", files)
            self.assertIn("00-global/scripts/test_maintenance_proposal_review.py", files)
            self.assertIn("00-global/scripts/test_maintenance_change_drafts.py", files)
            self.assertIn("00-global/scripts/test_maintenance_change_draft_review.py", files)
            self.assertIn("00-global/scripts/test_maintenance_apply_packages.py", files)
            self.assertIn("00-global/scripts/test_maintenance_apply_plans.py", files)
            self.assertIn("00-global/evaluation/context_pack_builder_v2.py", files)
            self.assertIn("00-global/usage-guide.md", files)
            self.assertIn("quant/10-standards/anti-lookahead-rules.md", files)
            self.assertIn("fiction-reasoning/10-standards/textual-evidence-standard.md", files)
            self.assertTrue((target / "education" / "10-standards").is_dir())
            self.assertFalse(any(path.startswith("00-global/state/") for path in files))
            self.assertFalse(any(path.startswith("00-global/evaluation/runs/") for path in files))
            self.assertFalse(any(path.startswith("00-global/audit-reports/") for path in files))
            self.assertFalse(any("webdav" in path.lower() for path in files))

    def test_build_starter_does_not_embed_personal_paths(self) -> None:
        builder = load_module()
        source_root = MODULE_PATH.resolve().parents[2]
        with TemporaryDirectory() as tmp:
            target = Path(tmp) / "starter"

            builder.build_starter(source_root, target)
            combined_text = "\n".join(
                path.read_text(encoding="utf-8", errors="replace")
                for path in target.rglob("*")
                if path.is_file() and path.suffix in {".md", ".py", ".json"}
            )
            personal_vault_path = "/" + "data" + "/" + "knowledge-vaults"
            obsidian_mount_path = "/" + "mnt" + "/" + "obsidian"

        self.assertNotIn(personal_vault_path, combined_text)
        self.assertNotIn(obsidian_mount_path, combined_text)

    def test_starter_bootstrap_creates_portable_local_vault(self) -> None:
        builder = load_module()
        source_root = MODULE_PATH.resolve().parents[2]
        with TemporaryDirectory() as tmp:
            starter = Path(tmp) / "starter"
            vault = Path(tmp) / "new-vault"
            builder.build_starter(source_root, starter)

            bootstrap = subprocess.run(
                [
                    sys.executable,
                    str(starter / "bootstrap-local-vault.py"),
                    "--root",
                    str(vault),
                    "--template",
                    str(starter),
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            config = json.loads((vault / "00-global" / "state" / "vault-config.json").read_text(encoding="utf-8"))
            task_seed = vault / "quant" / "20-notes" / "task-seed.md"
            task_seed.parent.mkdir(parents=True, exist_ok=True)
            task_seed.write_text(
                "---\n"
                "type: note\n"
                "domain: quant\n"
                "status: draft\n"
                "confidence: low\n"
                "evidence_level: source_claim\n"
                "source: starter-test\n"
                "updated: 2026-05-20\n"
                "usage_count: 3\n"
                "---\n\n"
                "# Task Seed\n",
                encoding="utf-8",
            )
            scan = subprocess.run(
                [sys.executable, str(vault / "00-global" / "scripts" / "scan-vault-strict.py"), "--root", str(vault)],
                text=True,
                capture_output=True,
                check=False,
            )
            context_jsonl = Path(tmp) / "context.jsonl"
            context_md = Path(tmp) / "context.md"
            context = subprocess.run(
                [
                    sys.executable,
                    str(vault / "00-global" / "evaluation" / "context_pack_builder_v2.py"),
                    "--root",
                    str(vault),
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
            benchmark = Path(tmp) / "benchmark.jsonl"
            benchmark.write_text(
                json.dumps(
                    {
                        "id": "q-portable",
                        "domain": "quant",
                        "question": "量化因子回测怎么避免未来函数和数据泄漏？",
                        "focus": "未来函数 数据泄漏 point-in-time",
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            eval_out = Path(tmp) / "eval.jsonl"
            evaluation = subprocess.run(
                [
                    sys.executable,
                    str(vault / "00-global" / "evaluation" / "run_context_format_eval_v2.py"),
                    "--benchmark",
                    str(benchmark),
                    "--root",
                    str(vault),
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
            improve = subprocess.run(
                [sys.executable, str(vault / "00-global" / "scripts" / "kb.py"), "improve", "--root", str(vault), "--write"],
                text=True,
                capture_output=True,
                check=False,
            )
            review = subprocess.run(
                [
                    sys.executable,
                    str(vault / "00-global" / "scripts" / "kb.py"),
                    "review-improvements",
                    "--root",
                    str(vault),
                    "--decisions",
                    "1A",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            tasks = subprocess.run(
                [sys.executable, str(vault / "00-global" / "scripts" / "kb.py"), "tasks", "generate", "--root", str(vault), "--write"],
                text=True,
                capture_output=True,
                check=False,
            )
            task_list = subprocess.run(
                [sys.executable, str(vault / "00-global" / "scripts" / "kb.py"), "tasks", "list", "--root", str(vault)],
                text=True,
                capture_output=True,
                check=False,
            )
            proposals = subprocess.run(
                [sys.executable, str(vault / "00-global" / "scripts" / "kb.py"), "proposals", "generate", "--root", str(vault), "--write"],
                text=True,
                capture_output=True,
                check=False,
            )
            proposal_list = subprocess.run(
                [sys.executable, str(vault / "00-global" / "scripts" / "kb.py"), "proposals", "list", "--root", str(vault)],
                text=True,
                capture_output=True,
                check=False,
            )
            proposal_review = subprocess.run(
                [
                    sys.executable,
                    str(vault / "00-global" / "scripts" / "kb.py"),
                    "review-proposals",
                    "--root",
                    str(vault),
                    "--decisions",
                    "1A",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            change_drafts = subprocess.run(
                [sys.executable, str(vault / "00-global" / "scripts" / "kb.py"), "change-drafts", "generate", "--root", str(vault), "--write"],
                text=True,
                capture_output=True,
                check=False,
            )
            change_draft_list = subprocess.run(
                [sys.executable, str(vault / "00-global" / "scripts" / "kb.py"), "change-drafts", "list", "--root", str(vault)],
                text=True,
                capture_output=True,
                check=False,
            )
            change_draft_review = subprocess.run(
                [
                    sys.executable,
                    str(vault / "00-global" / "scripts" / "kb.py"),
                    "review-change-drafts",
                    "--root",
                    str(vault),
                    "--decisions",
                    "1A",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            apply_packages = subprocess.run(
                [sys.executable, str(vault / "00-global" / "scripts" / "kb.py"), "apply-packages", "generate", "--root", str(vault), "--write"],
                text=True,
                capture_output=True,
                check=False,
            )
            apply_package_list = subprocess.run(
                [sys.executable, str(vault / "00-global" / "scripts" / "kb.py"), "apply-packages", "list", "--root", str(vault)],
                text=True,
                capture_output=True,
                check=False,
            )
            maintain_plan = subprocess.run(
                [sys.executable, str(vault / "00-global" / "scripts" / "kb.py"), "maintain", "plan", "--root", str(vault), "--write"],
                text=True,
                capture_output=True,
                check=False,
            )
            maintain_status = subprocess.run(
                [sys.executable, str(vault / "00-global" / "scripts" / "kb.py"), "maintain", "status", "--root", str(vault)],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(bootstrap.returncode, 0, bootstrap.stderr)
            self.assertEqual(config["vault_root"], str(vault.resolve()))
            self.assertFalse(config["sync_enabled"])
            self.assertEqual(config["sync_target"], "")
            self.assertEqual(scan.returncode, 0, scan.stderr)
            self.assertIn("- total_findings:", scan.stdout)
            self.assertEqual(context.returncode, 0, context.stderr)
            self.assertTrue(context_jsonl.exists())
            self.assertTrue(context_md.exists())
            self.assertEqual(evaluation.returncode, 0, evaluation.stderr)
            self.assertEqual(len(eval_out.read_text(encoding="utf-8").splitlines()), 3)
            self.assertEqual(improve.returncode, 0, improve.stderr)
            self.assertIn("candidate_count:", improve.stdout)
            self.assertTrue((vault / "00-global" / "improvement-candidates.md").exists())
            self.assertEqual(review.returncode, 0, review.stderr)
            self.assertIn("decisions_recorded: 1", review.stdout)
            self.assertTrue((vault / "00-global" / "improvement-review-registry.md").exists())
            self.assertEqual(tasks.returncode, 0, tasks.stderr)
            self.assertIn("task_count:", tasks.stdout)
            self.assertTrue((vault / "00-global" / "maintenance-tasks.md").exists())
            self.assertTrue((vault / "00-global" / "state" / "maintenance-tasks.jsonl").exists())
            self.assertEqual(task_list.returncode, 0, task_list.stderr)
            self.assertIn("manual_knowledge_review", task_list.stdout)
            self.assertEqual(proposals.returncode, 0, proposals.stderr)
            self.assertIn("proposal_count:", proposals.stdout)
            self.assertTrue((vault / "00-global" / "maintenance-proposals.md").exists())
            self.assertTrue((vault / "00-global" / "state" / "maintenance-proposals.jsonl").exists())
            self.assertEqual(proposal_list.returncode, 0, proposal_list.stderr)
            self.assertIn("metadata_update_proposal", proposal_list.stdout)
            self.assertEqual(proposal_review.returncode, 0, proposal_review.stderr)
            self.assertIn("decisions_recorded: 1", proposal_review.stdout)
            self.assertTrue((vault / "00-global" / "maintenance-proposal-review-registry.md").exists())
            self.assertEqual(change_drafts.returncode, 0, change_drafts.stderr)
            self.assertIn("draft_count: 1", change_drafts.stdout)
            self.assertTrue((vault / "00-global" / "maintenance-change-drafts.md").exists())
            self.assertTrue((vault / "00-global" / "state" / "maintenance-change-drafts.jsonl").exists())
            self.assertEqual(change_draft_list.returncode, 0, change_draft_list.stderr)
            self.assertIn("metadata_change_draft", change_draft_list.stdout)
            self.assertEqual(change_draft_review.returncode, 0, change_draft_review.stderr)
            self.assertIn("decisions_recorded: 1", change_draft_review.stdout)
            self.assertTrue((vault / "00-global" / "maintenance-change-draft-review-registry.md").exists())
            self.assertEqual(apply_packages.returncode, 0, apply_packages.stderr)
            self.assertIn("package_count: 1", apply_packages.stdout)
            self.assertTrue((vault / "00-global" / "maintenance-apply-packages.md").exists())
            self.assertTrue((vault / "00-global" / "state" / "maintenance-apply-packages.jsonl").exists())
            self.assertEqual(apply_package_list.returncode, 0, apply_package_list.stderr)
            self.assertIn("metadata_change_draft", apply_package_list.stdout)
            self.assertEqual(maintain_plan.returncode, 0, maintain_plan.stderr)
            self.assertIn("apply_plan_count: 1", maintain_plan.stdout)
            self.assertTrue((vault / "00-global" / "maintenance-apply-plans.md").exists())
            self.assertTrue((vault / "00-global" / "state" / "maintenance-apply-plans.jsonl").exists())
            self.assertEqual(maintain_status.returncode, 0, maintain_status.stderr)
            self.assertIn("apply_plan_count: 1", maintain_status.stdout)


if __name__ == "__main__":
    unittest.main()
