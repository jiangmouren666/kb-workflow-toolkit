from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


MODULE_PATH = Path(__file__).with_name("context_builder.py")


def load_module():
    spec = importlib.util.spec_from_file_location("context_builder", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ContextBuilderTests(unittest.TestCase):
    def test_markdown_context_keeps_frontmatter_and_matching_section(self) -> None:
        builder = load_module()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            note = root / "note.md"
            note.write_text(
                """---
status: reviewed
evidence_level: user_experience
should_not_use_for: verified facts
---

# Note

## Unrelated

ignore this

## Quick Import

Save as draft and never mark reviewed or verified.
""",
                encoding="utf-8",
            )

            pack = builder.build_context_pack(
                root,
                "快速导入时是否可以标记 reviewed？",
                ["note.md"],
                scoring_focus="quick import draft never reviewed verified",
            )

        chunk = pack["selected_chunks"][0]
        self.assertIn("status: reviewed", chunk["text"])
        self.assertIn("## Quick Import", chunk["text"])
        self.assertNotIn("ignore this", chunk["text"])
        self.assertEqual(pack["metadata_used"][0]["status"], "reviewed")

    def test_python_context_extracts_relevant_function_windows(self) -> None:
        builder = load_module()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            script = root / "kb.py"
            script.write_text(
                """def unrelated():
    return "x"

def target_writable(target):
    return False, "not writable"

def run_auto_sync(root, reason):
    ok, message = target_writable(root)
    if not ok:
        print(f"auto_sync: skipped (target not writable: {message})")
        return
""",
                encoding="utf-8",
            )

            pack = builder.build_context_pack(
                root,
                "如果 WebDAV 挂载不可写，自动同步应该怎么办？",
                ["kb.py"],
                scoring_focus="skip when target not writable",
            )

        text = pack["selected_chunks"][0]["text"]
        self.assertIn("def target_writable", text)
        self.assertIn("def run_auto_sync", text)
        self.assertIn("auto_sync: skipped", text)

    def test_context_pack_records_missing_paths_and_can_append_jsonl(self) -> None:
        builder = load_module()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = root / "packs.jsonl"
            pack = builder.build_context_pack(root, "问题", ["missing.md"])
            builder.append_context_pack(out, pack)
            saved = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]

        self.assertEqual(pack["missing_evidence"], ["missing.md"])
        self.assertEqual(saved[0]["question"], "问题")


if __name__ == "__main__":
    unittest.main()
