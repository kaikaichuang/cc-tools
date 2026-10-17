"""Tests for bin/cc-archive against a fake HOME laid out like Claude Code's.

    python3 -m unittest discover -s tests
"""
import json
import os
import re
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

CLI = Path(__file__).resolve().parent.parent / "bin" / "cc-archive"
A = "aaaaaaaa-0000-0000-0000-000000000001"
B = "bbbbbbbb-0000-0000-0000-000000000002"


def record(type, ts, **fields):
    return json.dumps({"type": type, "timestamp": ts, **fields})


class CcArchiveTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name).resolve()
        self.project = self.home / "proj_x"
        self.project.mkdir()
        self.live = self.home / ".claude/projects" / re.sub(r"[^a-zA-Z0-9]", "-", str(self.project))
        self.live.mkdir(parents=True)
        self.archived = self.home / ".local/share/cc-archive" / self.live.name
        (self.home / ".claude/sessions").mkdir()
        old = time.time() - 3600

        (self.live / f"{A}.jsonl").write_text("\n".join([
            record("user", "2026-01-01T10:00:00Z", message={"content": "first prompt A"}),
            record("ai-title", None, aiTitle="ai title A"),
            record("custom-title", None, customTitle="my name A"),
            record("ai-title", None, aiTitle="newer ai title A"),
        ]))
        (self.live / A).mkdir()
        (self.live / A / "tool.txt").write_text("x")
        (self.live / f"{B}.jsonl").write_text(record("user", "2026-01-02T10:00:00Z", message={"content": "prompt B"}))
        for p in [*self.live.iterdir(), self.live / A / "tool.txt"]:
            os.utime(p, (old, old))

    def tearDown(self):
        self.tmp.cleanup()

    def cli(self, *args, cwd=None):
        env = {**os.environ, "HOME": str(self.home)}
        env.pop("CC_ARCHIVE_DIR", None)
        r = subprocess.run([str(CLI), *args], cwd=cwd or self.project, env=env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def set_open(self, sid):
        (self.home / ".claude/sessions/1.json").write_text(json.dumps({"pid": os.getpid(), "sessionId": sid}))

    def test_list_matches_resume(self):
        lines = self.cli().splitlines()  # piped: plain list, newest first
        self.assertTrue(lines[0].startswith("bbbbbbbb"))
        self.assertIn("my name A", lines[1])  # /rename title beats AI title

    def test_archive_and_restore(self):
        self.assertIn("archived", self.cli("aaaa"))
        self.assertFalse((self.live / f"{A}.jsonl").exists())
        self.assertTrue((self.archived / A / "tool.txt").exists())  # side folder moves too
        self.assertIn("aaaaaaaa", self.cli("-l"))

        self.assertIn("restored", self.cli("-r", "aaaa"))
        self.assertTrue((self.live / A / "tool.txt").exists())
        self.assertGreater((self.live / f"{A}.jsonl").stat().st_mtime, time.time() - 60)  # touched

    def test_open_session_is_archived_when_it_closes(self):
        self.set_open(A)
        self.assertIn("when it closes", self.cli("aaaa"))
        self.cli("--pending")
        self.assertTrue((self.live / f"{A}.jsonl").exists())  # still open

        (self.home / ".claude/sessions/1.json").unlink()
        self.cli("--pending")
        self.assertTrue((self.archived / f"{A}.jsonl").exists())

    def test_unknown_registry_format_falls_back_to_file_age(self):
        (self.home / ".claude/sessions/1.json").write_text(json.dumps({"process": 1}))
        os.utime(self.live / f"{A}.jsonl")  # just written
        self.assertIn("when it closes", self.cli("aaaa"))
        self.assertIn("archived", self.cli("bbbb"))  # untouched for an hour

    def test_restore_cancels_pending(self):
        self.set_open(A)
        self.cli("aaaa")
        self.assertIn("no longer", self.cli("-r", "aaaa"))
        (self.home / ".claude/sessions/1.json").unlink()
        self.cli("--pending")
        self.assertTrue((self.live / f"{A}.jsonl").exists())

    def test_full_id_found_from_any_directory(self):
        self.assertIn("archived", self.cli(A, cwd=self.home))
        self.assertTrue((self.archived / f"{A}.jsonl").exists())

    def test_restore_all(self):
        self.cli("aaaa", "bbbb")
        self.cli("--restore-all", cwd=self.home)
        self.assertEqual(len(list(self.live.glob("*.jsonl"))), 2)


if __name__ == "__main__":
    unittest.main()
