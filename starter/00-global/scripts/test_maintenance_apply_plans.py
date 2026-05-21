from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


MODULE_PATH = Path(__file__).with_name("maintenance-apply-plans.py")


def load_module():
    spec = importlib.util.spec_from_file_location("maintenance_apply_plans", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_review_registry(root: Path, rows: list[dict]) -> Path:
    path = root / "00-global" / "improvement-review-registry.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Improvement Review Registry",
        "",
        "| Candidate ID | Path | Candidate Type | Decision | Reviewed At | Reason | Next Action |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{row['candidate_id']}`",
                    f"`{row['path']}`",
                    row["candidate_type"],
                    row["decision"],
                    "2026-05-21",
                    row.get("reason", "reviewed"),
                    row.get("next_action", "Prepare a safe maintenance plan."),
                ]
            )
            + " |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_candidates(root: Path, rows: list[dict] | None = None) -> Path:
    path = root / "00-global" / "state" / "improvement-candidates.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = rows or [
        {
            "candidate_id": "candidate-ready",
            "path": "quant/20-notes/seed.md",
            "candidate_type": "frequently_used_but_draft",
            "severity": "medium",
            "reason": "frequently used draft",
            "suggested_action": "Review metadata and scope.",
        }
    ]
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    return path


def write_note(root: Path, relpath: str = "quant/20-notes/seed.md", text: str = "---\nstatus: draft\n---\n# Seed\n") -> Path:
    path = root / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


class MaintenanceApplyPlanTests(unittest.TestCase):
    def test_generate_plans_from_actionable_review_decisions(self) -> None:
        module = load_module()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_note(root)
            write_review_registry(
                root,
                [
                    {"candidate_id": "candidate-ready", "path": "quant/20-notes/seed.md", "candidate_type": "frequently_used_but_draft", "decision": "accepted_for_review"},
                    {"candidate_id": "candidate-rejected", "path": "quant/20-notes/rejected.md", "candidate_type": "negative_feedback", "decision": "rejected"},
                ],
            )

            plans = module.generate_plans(root)

        self.assertEqual([item["source_candidate_id"] for item in plans], ["candidate-ready"])
        self.assertEqual(plans[0]["schema"], "knowledge-maintenance-apply-plan-v1")
        self.assertEqual(plans[0]["status"], "ready_preview")
        self.assertTrue(plans[0]["apply_requires_explicit_confirmation"])

    def test_plan_id_is_stable_for_same_review_entry(self) -> None:
        module = load_module()

        first = module.plan_id("candidate-ready", "accepted_for_review", "quant/20-notes/seed.md")
        second = module.plan_id("candidate-ready", "accepted_for_review", "quant/20-notes/seed.md")

        self.assertEqual(first, second)
        self.assertEqual(len(first), 16)

    def test_ready_plan_records_target_sha256(self) -> None:
        module = load_module()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            text = "---\nstatus: draft\n---\n# Seed\n"
            write_note(root, text=text)
            entry = {
                "candidate_id": "candidate-ready",
                "path": "quant/20-notes/seed.md",
                "candidate_type": "frequently_used_but_draft",
                "decision": "accepted_for_review",
                "reason": "reviewed",
                "next_action": "Prepare maintenance plan.",
            }

            plan = module.plan_from_review_entry(root, entry)

        self.assertEqual(plan["target_sha256"], hashlib.sha256(text.encode("utf-8")).hexdigest())
        self.assertEqual(plan["status"], "ready_preview")
        self.assertIn("target_sha256_recorded", plan["preflight_checks"])

    def test_fiction_reasoning_plan_uses_domain_specific_suggestions(self) -> None:
        module = load_module()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_note(root, "fiction-reasoning/20-notes/outline.md")
            entry = {
                "candidate_id": "fiction-outline",
                "path": "fiction-reasoning/20-notes/outline.md",
                "candidate_type": "frequently_used_but_draft",
                "decision": "accepted_for_review",
                "reason": "frequently used fiction outline",
                "next_action": "Prepare maintenance plan.",
            }

            plan = module.plan_from_review_entry(root, entry)

        operations = "\n".join(plan["proposed_operations"])
        requirements = "\n".join(plan["evidence_requirements"])
        self.assertIn("worldbuilding", operations)
        self.assertIn("character", operations)
        self.assertIn("ability boundary", operations)
        self.assertIn("spoiler_scope", requirements)
        self.assertIn("timeline_position", requirements)

    def test_programming_plan_uses_code_validation_suggestions(self) -> None:
        module = load_module()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_note(root, "programming/20-notes/qlib-workflow-by-code-example.md")
            entry = {
                "candidate_id": "qlib-example",
                "path": "programming/20-notes/qlib-workflow-by-code-example.md",
                "candidate_type": "frequently_used_but_draft",
                "decision": "accepted_for_review",
                "reason": "frequently used code example",
                "next_action": "Prepare maintenance plan.",
            }

            plan = module.plan_from_review_entry(root, entry)

        operations = "\n".join(plan["proposed_operations"])
        requirements = "\n".join(plan["evidence_requirements"])
        self.assertIn("runnable command", operations)
        self.assertIn("dependency versions", operations)
        self.assertIn("quant workflow", operations)
        self.assertIn("runnable_command", requirements)
        self.assertIn("expected_output", requirements)

    def test_quant_plan_uses_backtest_validation_suggestions(self) -> None:
        module = load_module()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_note(root, "quant/20-notes/factor-backtest.md")
            entry = {
                "candidate_id": "factor-backtest",
                "path": "quant/20-notes/factor-backtest.md",
                "candidate_type": "frequently_used_but_draft",
                "decision": "accepted_for_review",
                "reason": "frequently used quant note",
                "next_action": "Prepare maintenance plan.",
            }

            plan = module.plan_from_review_entry(root, entry)

        operations = "\n".join(plan["proposed_operations"])
        requirements = "\n".join(plan["evidence_requirements"])
        self.assertIn("future leakage", operations)
        self.assertIn("transaction cost", operations)
        self.assertIn("data availability", operations)
        self.assertIn("train_test_split", requirements)
        self.assertIn("transaction_costs", requirements)

    def test_missing_and_invalid_targets_generate_blocked_plans(self) -> None:
        module = load_module()
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "vault"
            root.mkdir()

            missing = module.plan_from_review_entry(
                root,
                {"candidate_id": "missing", "path": "quant/20-notes/missing.md", "candidate_type": "missing_feedback_fields", "decision": "accepted_for_review"},
            )
            escaped = module.plan_from_review_entry(
                root,
                {"candidate_id": "escape", "path": "../outside.md", "candidate_type": "missing_feedback_fields", "decision": "accepted_for_review"},
            )

        self.assertEqual(missing["status"], "blocked_missing_target")
        self.assertEqual(escaped["status"], "blocked_invalid_target_path")
        self.assertEqual(escaped["target_sha256"], "")

    def test_write_outputs_does_not_mutate_note_registry_or_candidates(self) -> None:
        module = load_module()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            note = write_note(root)
            registry = write_review_registry(
                root,
                [{"candidate_id": "candidate-ready", "path": "quant/20-notes/seed.md", "candidate_type": "frequently_used_but_draft", "decision": "accepted_for_review"}],
            )
            candidates = write_candidates(root)
            before_note = note.read_text(encoding="utf-8")
            before_registry = registry.read_text(encoding="utf-8")
            before_candidates = candidates.read_text(encoding="utf-8")

            outputs = module.write_outputs(root, module.generate_plans(root))

            self.assertEqual(note.read_text(encoding="utf-8"), before_note)
            self.assertEqual(registry.read_text(encoding="utf-8"), before_registry)
            self.assertEqual(candidates.read_text(encoding="utf-8"), before_candidates)
            self.assertTrue(outputs["markdown"].exists())
            self.assertTrue(outputs["jsonl"].exists())

    def test_status_counts_candidates_reviews_and_plans(self) -> None:
        module = load_module()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_note(root)
            write_candidates(root)
            write_review_registry(
                root,
                [{"candidate_id": "candidate-ready", "path": "quant/20-notes/seed.md", "candidate_type": "frequently_used_but_draft", "decision": "accepted_for_review"}],
            )
            module.write_outputs(root, module.generate_plans(root))

            status = module.status_summary(root)

        self.assertEqual(status["candidate_count"], 1)
        self.assertEqual(status["review_decision_count"], 1)
        self.assertEqual(status["apply_plan_count"], 1)

    def test_cli_generate_list_and_status(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_note(root)
            write_review_registry(
                root,
                [{"candidate_id": "candidate-ready", "path": "quant/20-notes/seed.md", "candidate_type": "frequently_used_but_draft", "decision": "accepted_for_review"}],
            )

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
            status = subprocess.run(
                [sys.executable, str(MODULE_PATH), "--root", str(root), "status"],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(generate.returncode, 0, generate.stderr)
            self.assertIn("apply_plan_count: 1", generate.stdout)
            self.assertEqual(list_result.returncode, 0, list_result.stderr)
            self.assertIn("ready_preview", list_result.stdout)
            self.assertEqual(status.returncode, 0, status.stderr)
            self.assertIn("review_decision_count: 1", status.stdout)


if __name__ == "__main__":
    unittest.main()
