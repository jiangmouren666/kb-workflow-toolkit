from __future__ import annotations

import contextlib
import io
import importlib.util
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock


MODULE_PATH = Path(__file__).with_name("sync-vault.py")


def load_module():
    spec = importlib.util.spec_from_file_location("sync_vault", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class SyncVaultTests(unittest.TestCase):
    def test_plan_sync_treats_unreadable_target_as_changed(self) -> None:
        sync = load_module()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            target = root / "target"
            source.mkdir()
            target.mkdir()
            (source / "note.md").write_text("new", encoding="utf-8")
            (target / "note.md").write_text("old", encoding="utf-8")

            with mock.patch.object(sync, "sha256", side_effect=["source-hash", OSError("io error")]):
                to_copy, same = sync.plan_sync(source, target)

        self.assertEqual([src.name for src, _dst in to_copy], ["note.md"])
        self.assertEqual(same, [])

    def test_copy_with_rebuild_unlinks_and_retries_on_oserror(self) -> None:
        sync = load_module()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "source.md"
            dst = root / "target.md"
            src.write_text("content", encoding="utf-8")
            dst.write_text("stale", encoding="utf-8")

            calls = []

            def flaky_copy2(_src: Path, _dst: Path) -> None:
                calls.append("copy")
                if len(calls) == 1:
                    raise OSError("io error")
                _dst.write_text(_src.read_text(encoding="utf-8"), encoding="utf-8")

            with mock.patch.object(sync.shutil, "copy2", side_effect=flaky_copy2):
                sync.copy_with_rebuild(src, dst)

            self.assertEqual(calls, ["copy", "copy"])
            self.assertEqual(dst.read_text(encoding="utf-8"), "content")

    def test_copy_with_rebuild_reports_unlink_failure(self) -> None:
        sync = load_module()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "source.md"
            dst = root / "target.md"
            src.write_text("content", encoding="utf-8")
            dst.write_text("stale", encoding="utf-8")

            with (
                mock.patch.object(sync.shutil, "copy2", side_effect=OSError("io error")),
                mock.patch.object(sync.Path, "unlink", side_effect=OSError("unlink error")),
            ):
                error = sync.copy_with_rebuild(src, dst)

            self.assertIn("unlink failed", error)

    def test_copy_with_rebuild_rebuilds_when_copy_silently_leaves_stale_content(self) -> None:
        sync = load_module()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "source.md"
            dst = root / "target.md"
            src.write_text("content", encoding="utf-8")
            dst.write_text("stale", encoding="utf-8")

            calls = []

            def flaky_copy2(_src: Path, _dst: Path) -> None:
                calls.append("copy")
                if len(calls) == 1:
                    return
                _dst.write_text(_src.read_text(encoding="utf-8"), encoding="utf-8")

            with mock.patch.object(sync.shutil, "copy2", side_effect=flaky_copy2):
                error = sync.copy_with_rebuild(src, dst)

            self.assertIsNone(error)
            self.assertEqual(calls, ["copy", "copy"])
            self.assertEqual(dst.read_text(encoding="utf-8"), "content")

    def test_copy_with_rebuild_reports_error_when_retry_stays_stale(self) -> None:
        sync = load_module()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "source.md"
            dst = root / "target.md"
            src.write_text("content", encoding="utf-8")
            dst.write_text("stale", encoding="utf-8")

            with mock.patch.object(sync.shutil, "copy2", return_value=None):
                error = sync.copy_with_rebuild(src, dst)

            self.assertIn("target hash stayed stale", error)

    def test_main_exits_nonzero_when_write_reports_copy_error(self) -> None:
        sync = load_module()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            target = root / "target"
            source.mkdir()
            target.mkdir()
            (source / "note.md").write_text("new", encoding="utf-8")
            (target / "note.md").write_text("old", encoding="utf-8")

            with (
                mock.patch.object(sys, "argv", ["sync-vault.py", "--source", str(source), "--target", str(target), "--write"]),
                mock.patch.object(sync.shutil, "copy2", return_value=None),
                contextlib.redirect_stdout(io.StringIO()),
            ):
                with self.assertRaises(SystemExit) as raised:
                    sync.main()

        self.assertEqual(raised.exception.code, 1)


if __name__ == "__main__":
    unittest.main()
