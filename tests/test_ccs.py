"""Tests for bin/ccs against a fake HOME laid out like Claude Code's.

    python3 -m unittest discover -s tests
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

CLI = Path(__file__).resolve().parent.parent / "bin" / "ccs"
A = "aaaaaaaa-0000-0000-0000-000000000001"
B = "bbbbbbbb-0000-0000-0000-000000000002"
C = "cccccccc-0000-0000-0000-000000000003"


def record(type, ts, **fields):
    return json.dumps({"type": type, "timestamp": ts, **fields}, separators=(",", ":"))  # as Claude writes them


class CcArchiveTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name).resolve()
        self.project = self.home / "proj_x"
        self.project.mkdir()
        self.live = self.home / ".claude/projects" / re.sub(r"[^a-zA-Z0-9]", "-", str(self.project))
        self.live.mkdir(parents=True)
        self.archived = self.home / ".local/share/ccs" / self.live.name
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
        env.pop("CCS_DIR", None)
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

    def cli_fails(self, *args):
        env = {**os.environ, "HOME": str(self.home)}
        env.pop("CCS_DIR", None)
        r = subprocess.run([str(CLI), *args], cwd=self.project, env=env, capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0, r.stdout)
        return r.stderr

    def test_unknown_registry_format_moves_nothing_unless_forced(self):
        (self.home / ".claude/sessions/1.json").write_text(json.dumps({"process": 1}))
        self.assertIn("cannot tell", self.cli_fails("bbbb"))  # an hour idle proves nothing
        self.assertTrue((self.live / f"{B}.jsonl").exists())
        self.assertIn("archived", self.cli("-f", "bbbb"))

    def test_unreadable_registry_entry_keeps_pending_session(self):
        self.set_open(A)
        self.cli("aaaa")
        (self.home / ".claude/sessions/1.json").write_text('{"pid": 1, "sessio')  # caught mid-write
        self.cli("--pending")
        self.assertTrue((self.live / f"{A}.jsonl").exists())

    def test_ambiguous_prefix_on_restore_does_nothing(self):
        other = "aaaaaaaa-0000-0000-0000-000000000009"
        (self.live / f"{other}.jsonl").write_text(record("user", "2026-01-04T10:00:00Z", message={"content": "x"}))
        old = time.time() - 3600
        os.utime(self.live / f"{other}.jsonl", (old, old))
        self.cli(other)  # archived
        self.set_open(A)
        self.cli(A)  # pending
        self.assertIn("ambiguous", self.cli_fails("-r", "aaaa"))
        self.assertTrue((self.archived / f"{other}.jsonl").exists())
        self.assertIn(A[:8], self.cli("-r", A))  # a full id still works

    def test_malformed_records_do_not_break_the_list(self):
        with open(self.live / f"{B}.jsonl", "a") as f:
            f.write("\n".join(["", "[1, 2]", '"text"', '{"type":"user","message":"not a dict"}',
                                '{"timestamp":5}', '{"type":"ai-title","aiTitle":["x"]}', "{broken"]))
        self.assertIn("prompt B", self.cli())

    def in_process(self, code):
        """Run code with bin/ccs loaded as module m, in the fake HOME."""
        r = subprocess.run(
            [sys.executable, "-c", "import sys, shutil; from importlib.machinery import SourceFileLoader;"
             f"m = SourceFileLoader('ccs', {str(CLI)!r}).load_module()\n" + code],
            env={**os.environ, "HOME": str(self.home)}, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def test_failed_move_puts_back_what_moved(self):
        out = self.in_process(
            "real, calls = shutil.move, []\n"
            "def flaky(a, b):\n"
            "    calls.append(a)\n"
            "    if len(calls) == 2: raise OSError('disk full')\n"
            "    return real(a, b)\n"
            "shutil.move = flaky\n"
            "live = m.PROJECTS / m.project_key(" + repr(str(self.project)) + ")\n"
            "try: m.move(live, m.archive_dir(live), " + repr(A) + ")\n"
            "except ValueError as e: print(e)\n")
        self.assertIn("nothing was moved", out)
        self.assertTrue((self.live / f"{A}.jsonl").exists())
        self.assertTrue((self.live / A / "tool.txt").exists())
        self.assertFalse(self.archived.exists() and any(self.archived.iterdir()))

    def test_uninstall_restores_everything_and_removes_ccs(self):
        self.cli("bbbb")  # archived
        self.set_open(A)
        self.cli("aaaa")  # pending
        bin_dir = self.home / ".local/bin"
        bin_dir.mkdir(parents=True)
        (bin_dir / "ccs").symlink_to(CLI)
        (bin_dir / "other").write_text("not ours")
        fake = self.home / "fakebin"
        fake.mkdir()
        (fake / "claude").write_text(f"#!/bin/sh\necho \"$@\" >> {self.home}/claude-calls\n")
        (fake / "claude").chmod(0o755)
        env = {**os.environ, "HOME": str(self.home), "PATH": f"{fake}:{os.environ['PATH']}"}
        r = subprocess.run([str(CLI), "--uninstall"], cwd=self.project, env=env,
                           stdin=subprocess.DEVNULL, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)

        self.assertTrue((self.live / f"{B}.jsonl").exists())
        self.assertTrue((self.live / f"{A}.jsonl").exists())
        self.assertFalse((self.home / ".local/share/ccs").exists())
        self.assertFalse((bin_dir / "ccs").exists())
        self.assertTrue((bin_dir / "other").exists())
        calls = (self.home / "claude-calls").read_text()
        self.assertIn("plugin uninstall ccs@cc-tools", calls)
        self.assertIn("plugin marketplace remove cc-tools", calls)

    def test_session_a_live_job_started_with_counts_as_open(self):
        # the job named after A now hosts another conversation, but may still go back to A
        (self.home / ".claude/sessions/1.json").write_text(
            json.dumps({"pid": os.getpid(), "sessionId": B, "jobId": A[:8]}))
        self.assertIn("when it closes", self.cli("aaaa"))

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

    def copy_of_a(self, sid, extra=0, linked=True):
        """Make sid a copy of A the way Claude Code does when moving A to the background."""
        lines = (self.live / f"{A}.jsonl").read_text().splitlines()
        lines += [record("user", f"2026-01-03T10:00:0{i}Z", message={"content": "more"}) for i in range(extra)]
        (self.live / f"{sid}.jsonl").write_text("\n".join(lines))
        if linked:
            with open(self.live / f"{A}.jsonl", "a") as f:
                f.write("\n" + record("continued-in", None, sessionId=A, continuedInSessionId=sid))
        old = time.time() - 3600
        os.utime(self.live / f"{A}.jsonl", (old, old))
        os.utime(self.live / f"{sid}.jsonl", (old - 60, old - 60))

    def test_copy_with_fewer_messages_is_archived(self):
        self.copy_of_a(C)
        self.cli("--pending")
        self.assertTrue((self.archived / f"{C}.jsonl").exists())
        self.assertTrue((self.live / f"{A}.jsonl").exists())

    def test_untouched_copy_loses_to_the_original_even_if_newer(self):
        self.copy_of_a(C)
        os.utime(self.live / f"{A}.jsonl", (time.time() - 7200, time.time() - 7200))  # copy is newer
        self.cli("--pending")
        self.assertTrue((self.archived / f"{C}.jsonl").exists())
        self.assertTrue((self.live / f"{A}.jsonl").exists())

    def test_original_is_archived_when_the_copy_has_more(self):
        self.copy_of_a(C, extra=2)  # the conversation went on in the copy
        self.cli("--pending")
        self.assertTrue((self.archived / f"{A}.jsonl").exists())
        self.assertTrue((self.live / f"{C}.jsonl").exists())

    def test_branch_is_never_archived(self):
        self.copy_of_a(C, linked=False)  # /branch, --fork-session: no continued-in record
        self.cli("--pending")
        self.assertTrue((self.live / f"{C}.jsonl").exists())

    def test_open_copy_is_left_alone(self):
        self.copy_of_a(C)
        self.set_open(C)
        self.cli("--pending")
        self.assertTrue((self.live / f"{C}.jsonl").exists())

    def test_copy_restored_by_hand_stays(self):
        self.copy_of_a(C)
        self.cli("--pending")
        self.cli("-r", "cccc")
        self.cli("--pending")
        self.assertTrue((self.live / f"{C}.jsonl").exists())

    def open_command(self, agents):
        """bin/ccs's open_command, with `claude agents --json` answering agents."""
        fake = self.home / "bin"
        fake.mkdir(exist_ok=True)
        (fake / "claude").write_text(f"#!/bin/sh\necho '{json.dumps(agents)}'\n")
        (fake / "claude").chmod(0o755)
        r = subprocess.run(
            [sys.executable, "-c", "import sys; from importlib.machinery import SourceFileLoader;"
             f"m = SourceFileLoader('cca', {str(CLI)!r}).load_module(); print(m.open_command({A!r}))"],
            env={**os.environ, "HOME": str(self.home), "PATH": f"{fake}:{os.environ['PATH']}"},
            capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout.strip()

    def test_enter_attaches_to_a_running_background_session(self):
        out = self.open_command([{"id": "aaaaaaaa", "kind": "background", "sessionId": A}])
        self.assertIn("'claude', 'attach', 'aaaaaaaa'", out)

    def test_enter_resumes_a_session_nothing_runs(self):
        out = self.open_command([{"id": "bbbbbbbb", "kind": "background", "sessionId": B}])
        self.assertIn(f"'claude', '--resume', '{A}'", out)

    def test_enter_refuses_a_session_open_in_another_window(self):
        out = self.open_command([{"kind": "interactive", "sessionId": A}])
        self.assertIn("another claude window", out)

    def test_restore_all(self):
        self.cli("aaaa", "bbbb")
        self.cli("--restore-all", cwd=self.home)
        self.assertEqual(len(list(self.live.glob("*.jsonl"))), 2)


if __name__ == "__main__":
    unittest.main()
