from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


MODULE_PATH = Path(__file__).with_name("trust-drift-report.py")


def load_module():
    spec = importlib.util.spec_from_file_location("trust_drift_report", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_note(root: Path, relpath: str, text: str) -> Path:
    path = root / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def write_registry(root: Path) -> Path:
    path = root / "00-global" / "human-review-registry.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "# Human Review Registry\n\n"
        "| Path | Registry Status | Decision | Reviewed At | Use | Risk | Evidence Need | Boundary |\n"
        "|---|---|---|---|---|---|---|---|\n"
        "| `quant/20-notes/reviewed.md` | reviewed | `S=B,U=C,R=B,E=E` | 2026-05-21 | decision/risk review | medium | none for now | reviewed boundary |\n"
        "| `quant/20-notes/missing.md` | reviewed | `S=B,U=C,R=B,E=E` | 2026-05-21 | decision/risk review | medium | none for now | missing target |\n",
        encoding="utf-8",
    )
    return path


class TrustDriftReportTests(unittest.TestCase):
    def test_detects_registry_frontmatter_mismatch_and_missing_target(self) -> None:
        module = load_module()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_registry(root)
            write_note(
                root,
                "quant/20-notes/reviewed.md",
                "---\ntype: note\ndomain: quant\nstatus: draft\nconfidence: low\nevidence_level: source_claim\nsource: test\nupdated: 2026-05-21\n---\n# Reviewed\n",
            )

            findings = module.generate_findings(root)

        finding_types = {item["finding_type"] for item in findings}
        self.assertIn("frontmatter_registry_mismatch", finding_types)
        self.assertIn("registry_target_missing", finding_types)

    def test_detects_verified_without_strong_evidence_or_checklist(self) -> None:
        module = load_module()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_note(
                root,
                "programming/20-notes/api.md",
                "---\ntype: note\ndomain: programming\nstatus: verified\nconfidence: high\nevidence_level: source_claim\nsource: unclear\nupdated: 2026-05-21\nhuman_review:\n  reviewer: user\n---\n# API\n",
            )

            findings = module.generate_findings(root)

        finding_types = {item["finding_type"] for item in findings}
        self.assertIn("verified_without_strong_evidence", finding_types)
        self.assertIn("verified_missing_evidence_checklist", finding_types)

    def test_write_outputs_reports_without_mutating_notes(self) -> None:
        module = load_module()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            note = write_note(
                root,
                "programming/20-notes/api.md",
                "---\ntype: note\ndomain: programming\nstatus: verified\nconfidence: high\nevidence_level: source_claim\nsource: unclear\nupdated: 2026-05-21\nhuman_review:\n  reviewer: user\n---\n# API\n",
            )
            before = note.read_text(encoding="utf-8")
            outputs = module.write_outputs(root, module.generate_findings(root))

            self.assertEqual(note.read_text(encoding="utf-8"), before)
            self.assertTrue(outputs["markdown"].exists())
            self.assertTrue(outputs["jsonl"].exists())
            rows = [json.loads(line) for line in outputs["jsonl"].read_text(encoding="utf-8").splitlines() if line.strip()]

        self.assertGreaterEqual(len(rows), 1)

    def test_cli_write_outputs_summary(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_note(
                root,
                "programming/20-notes/api.md",
                "---\ntype: note\ndomain: programming\nstatus: verified\nconfidence: high\nevidence_level: source_claim\nsource: unclear\nupdated: 2026-05-21\nhuman_review:\n  reviewer: user\n---\n# API\n",
            )

            result = subprocess.run(
                [sys.executable, str(MODULE_PATH), "--root", str(root), "--write"],
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("trust_drift_count:", result.stdout)
        self.assertIn("wrote_markdown:", result.stdout)


if __name__ == "__main__":
    unittest.main()
