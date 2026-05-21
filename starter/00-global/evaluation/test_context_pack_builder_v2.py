from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


MODULE_PATH = Path(__file__).with_name("context_pack_builder_v2.py")


def load_module():
    spec = importlib.util.spec_from_file_location("context_pack_builder_v2", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ContextPackBuilderV2Tests(unittest.TestCase):
    def test_registry_overlay_overrides_stale_frontmatter(self) -> None:
        builder = load_module()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "00-global").mkdir()
            (root / "00-global" / "human-review-registry.md").write_text(
                "| Path | Registry Status | Decision | Reviewed At | Use | Risk | Evidence Need | Boundary |\n"
                "|---|---|---|---|---|---|---|---|\n"
                "| `quant/checklist.md` | reviewed | `S=B` | 2026-05-17 | checklist | low | none | scope |\n",
                encoding="utf-8",
            )
            note = root / "quant" / "checklist.md"
            note.parent.mkdir()
            note.write_text("---\nstatus: draft\nconfidence: high\n---\n\n## Reviewed\ncontent\n", encoding="utf-8")

            pack = builder.build_context_pack(root, "是否 reviewed？", ["quant/checklist.md"], focus="reviewed registry")

        meta = pack["metadata_used"][0]
        self.assertEqual(meta["status"], "reviewed")
        self.assertEqual(meta["frontmatter_status"], "draft")
        self.assertTrue(meta["registry_overlay_applied"])

    def test_cli_writes_jsonl_context_pack(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            note = root / "note.md"
            note.write_text("---\nstatus: reviewed\n---\n\n## Quick Import\nSave as draft.\n", encoding="utf-8")
            out = root / "packs.jsonl"

            result = subprocess.run(
                [
                    sys.executable,
                    str(MODULE_PATH),
                    "--root",
                    str(root),
                    "--question",
                    "快速导入怎么处理？",
                    "--paths",
                    "note.md",
                    "--out",
                    str(out),
                ],
                text=True,
                capture_output=True,
                check=True,
            )

            rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]

        self.assertIn("context_pack_written", result.stdout)
        self.assertEqual(rows[0]["schema"], "knowledge-context-pack-v2")
        self.assertEqual(rows[0]["selected_chunks"][0]["path"], "note.md")

    def test_chunks_are_scored_and_reranked_by_relevance_and_trust(self) -> None:
        builder = load_module()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            unrelated = root / "unrelated.md"
            unrelated.write_text(
                "---\nstatus: draft\nconfidence: low\n---\n\n## Other\nNothing about sync.\n",
                encoding="utf-8",
            )
            relevant = root / "relevant.md"
            relevant.write_text(
                "---\nstatus: reviewed\nconfidence: high\nevidence_level: user_experience\n---\n\n"
                "## Auto Sync\nIf WebDAV is not writable, call target_writable and skip auto_sync clearly.\n",
                encoding="utf-8",
            )

            pack = builder.build_context_pack(
                root,
                "WebDAV 不可写时自动同步应该怎么办？",
                ["unrelated.md", "relevant.md"],
                focus="target_writable auto_sync not writable",
            )

        self.assertEqual(pack["selected_chunks"][0]["path"], "relevant.md")
        self.assertGreater(pack["selected_chunks"][0]["retrieval_score"], pack["selected_chunks"][1]["retrieval_score"])
        self.assertIn("term_hits", pack["selected_chunks"][0]["score_reasons"])
        self.assertEqual(pack["context_quality"]["top_path"], "relevant.md")
        self.assertEqual(pack["context_quality"]["missing_evidence_count"], 0)

    def test_auto_discovers_governance_and_domain_candidates(self) -> None:
        builder = load_module()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            governance = root / "00-global" / "current-governance-v2.md"
            governance.parent.mkdir(parents=True)
            governance.write_text("---\nstatus: reviewed\nconfidence: high\n---\n\nRegistry overlay rules.\n", encoding="utf-8")
            quant = root / "quant" / "10-standards" / "anti-lookahead-rules.md"
            quant.parent.mkdir(parents=True)
            quant.write_text(
                "---\nstatus: reviewed\nconfidence: high\n---\n\n## Anti Lookahead\n因子回测不能使用未来函数。\n",
                encoding="utf-8",
            )
            ml = root / "machine-learning" / "10-standards" / "leakage-prevention.md"
            ml.parent.mkdir(parents=True)
            ml.write_text("---\nstatus: draft\nconfidence: medium\n---\n\nLeakage prevention.\n", encoding="utf-8")

            paths = builder.discover_candidate_paths(root, "量化因子回测怎么防止未来函数？", focus="lookahead factor")

        self.assertIn("00-global/current-governance-v2.md", paths)
        self.assertIn("quant/10-standards/anti-lookahead-rules.md", paths)
        self.assertLess(paths.index("00-global/current-governance-v2.md"), paths.index("quant/10-standards/anti-lookahead-rules.md"))

    def test_auto_discovery_prefers_standards_over_domain_readmes(self) -> None:
        builder = load_module()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            standard = root / "quant" / "10-standards" / "anti-lookahead-rules.md"
            standard.parent.mkdir(parents=True)
            standard.write_text("---\nstatus: reviewed\nconfidence: high\n---\n\n未来函数 lookahead point-in-time.\n", encoding="utf-8")
            readme = root / "quant" / "00-inbox" / "README.md"
            readme.parent.mkdir(parents=True)
            readme.write_text("---\nstatus: draft\nconfidence: high\n---\n\n量化 inbox.\n", encoding="utf-8")

            paths = builder.discover_candidate_paths(root, "量化回测怎么避免未来函数？")

        self.assertIn("quant/10-standards/anti-lookahead-rules.md", paths)
        self.assertLess(paths.index("quant/10-standards/anti-lookahead-rules.md"), paths.index("quant/00-inbox/README.md"))

    def test_auto_discovers_framework_and_fiction_domain_standards(self) -> None:
        builder = load_module()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            framework = root / "framework-optimization" / "10-standards" / "version-benchmark-standard.md"
            framework.parent.mkdir(parents=True)
            framework.write_text("---\nstatus: reviewed\nconfidence: high\n---\n\nNext.js benchmark version regression.\n", encoding="utf-8")
            fiction = root / "fiction-reasoning" / "10-standards" / "textual-evidence-standard.md"
            fiction.parent.mkdir(parents=True)
            fiction.write_text("---\nstatus: reviewed\nconfidence: high\n---\n\n小说推理需要文本证据和伏笔一致性。\n", encoding="utf-8")

            framework_paths = builder.discover_candidate_paths(root, "Next.js 框架升级怎么做版本基准和性能回归？")
            fiction_paths = builder.discover_candidate_paths(root, "小说推理怎么检查伏笔和人物动机一致性？")

        self.assertIn("framework-optimization/10-standards/version-benchmark-standard.md", framework_paths)
        self.assertIn("fiction-reasoning/10-standards/textual-evidence-standard.md", fiction_paths)

    def test_cli_can_auto_discover_when_paths_are_omitted(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            note = root / "quant" / "10-standards" / "anti-lookahead-rules.md"
            note.parent.mkdir(parents=True)
            note.write_text("---\nstatus: reviewed\nconfidence: high\n---\n\n未来函数 and lookahead checklist.\n", encoding="utf-8")
            out = root / "packs.jsonl"

            subprocess.run(
                [
                    sys.executable,
                    str(MODULE_PATH),
                    "--root",
                    str(root),
                    "--question",
                    "量化回测怎么避免未来函数？",
                    "--out",
                    str(out),
                ],
                text=True,
                capture_output=True,
                check=True,
            )

            row = json.loads(out.read_text(encoding="utf-8").splitlines()[0])

        self.assertIn("quant/10-standards/anti-lookahead-rules.md", row["retrieved_files"])
        self.assertEqual(row["context_quality"]["candidate_source"], "auto_discovered")

    def test_render_markdown_context_block_includes_quality_scores_and_metadata(self) -> None:
        builder = load_module()
        pack = {
            "schema": "knowledge-context-pack-v2",
            "question": "问题？",
            "focus": "focus",
            "context_quality": {
                "top_path": "note.md",
                "top_score": 7,
                "candidate_source": "provided",
                "candidate_count": 1,
                "selected_count": 1,
                "missing_evidence_count": 0,
            },
            "metadata_used": [
                {
                    "path": "note.md",
                    "status": "reviewed",
                    "confidence": "high",
                    "evidence_level": "user_experience",
                    "registry_overlay_applied": True,
                    "frontmatter_status": "draft",
                }
            ],
            "missing_evidence": [],
            "selected_chunks": [
                {
                    "path": "note.md",
                    "retrieval_score": 7,
                    "score_reasons": ["term_hits", "reviewed_status"],
                    "why_selected": "frontmatter plus matching markdown section",
                    "text": "核心证据",
                }
            ],
        }

        markdown = builder.render_markdown_context(pack)

        self.assertIn("<context_pack>", markdown)
        self.assertIn("type: context-pack", markdown)
        self.assertIn("# Context Pack V2", markdown)
        self.assertIn("top_path: `note.md`", markdown)
        self.assertIn("| `note.md` | reviewed | high | user_experience | true | draft |", markdown)
        self.assertIn("retrieval_score: 7", markdown)
        self.assertIn("score_reasons: term_hits, reviewed_status", markdown)
        self.assertIn("核心证据", markdown)

    def test_cli_writes_markdown_context_block(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            note = root / "note.md"
            note.write_text("---\nstatus: reviewed\nconfidence: high\n---\n\n## Evidence\n核心证据\n", encoding="utf-8")
            out = root / "packs.jsonl"
            md_out = root / "context.md"

            subprocess.run(
                [
                    sys.executable,
                    str(MODULE_PATH),
                    "--root",
                    str(root),
                    "--question",
                    "Evidence?",
                    "--paths",
                    "note.md",
                    "--out",
                    str(out),
                    "--markdown-out",
                    str(md_out),
                ],
                text=True,
                capture_output=True,
                check=True,
            )

            markdown = md_out.read_text(encoding="utf-8")

        self.assertIn("<context_pack>", markdown)
        self.assertIn("## Selected Chunks", markdown)


if __name__ == "__main__":
    unittest.main()
