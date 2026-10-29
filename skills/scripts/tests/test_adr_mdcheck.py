"""Fixture tests for adr-mdcheck --root and meta/data coverage."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "adr-mdcheck.py"


def write_adr(path, slug, *, status="Accepted", date="2026-10-29", extra=""):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\ntitle: {slug}\nstatus: {status}\ndate: {date}\n{extra}---\n\nFixture.\n",
        encoding="utf-8",
    )


class AdrMdcheckFixtureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "asset-root"
        self.meta = self.root / "decisions" / "adr" / "meta"
        self.data = self.root / "decisions" / "adr" / "data"
        self.meta.mkdir(parents=True)
        self.data.mkdir(parents=True)
        (self.root / "decisions" / "external").mkdir()
        (self.root / "decisions" / "KNOWLEDGE.md").write_text("# Fixture index\n", encoding="utf-8")

    def run_check(self):
        return subprocess.run([sys.executable, "-B", str(SCRIPT), "--root", str(self.root)],
                              text=True, capture_output=True)

    def test_valid_meta_data_and_supersedes_pair_pass(self):
        write_adr(self.meta / "old.md", "old", status="Superseded",
                  extra="superseded_by: new\n")
        write_adr(self.data / "new.md", "new", extra="supersedes: old\n")
        p = self.run_check()
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("2 件（adr/meta + adr/data），ERROR 0", p.stdout)

    def test_invalid_record_in_data_directory_is_detected(self):
        write_adr(self.meta / "valid.md", "valid")
        write_adr(self.data / "bad-data.md", "bad-data", status="Unknown")
        p = self.run_check()
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn("I1 bad-data", p.stdout)
        self.assertIn("2 件（adr/meta + adr/data）", p.stdout)

    def test_symlink_root_is_rejected(self):
        alias = self.root.parent / "root-link"
        alias.symlink_to(self.root, target_is_directory=True)
        p = subprocess.run([sys.executable, "-B", str(SCRIPT), "--root", str(alias)],
                           text=True, capture_output=True)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("--root must be an existing non-symlink directory", p.stderr)

    def test_sync_count_refuses_knowledge_symlink_outside_root(self):
        outside = self.root.parent / "outside-knowledge.md"
        original = "# External fixture\n<!-- 计数：meta 0 / data 0 -->\n"
        outside.write_text(original, encoding="utf-8")
        knowledge = self.root / "decisions" / "KNOWLEDGE.md"
        knowledge.unlink()
        knowledge.symlink_to(outside)
        p = subprocess.run([sys.executable, "-B", str(SCRIPT), "--root", str(self.root),
                            "--sync-count"], text=True, capture_output=True)
        self.assertNotEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("decisions/ symlinks are not supported", p.stderr)
        self.assertEqual(outside.read_text(encoding="utf-8"), original)


if __name__ == "__main__":
    unittest.main()
