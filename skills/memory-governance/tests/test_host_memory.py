from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]


def load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, BASE / "scripts" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


scan = load("scan_memory", "scan-memory.py")
replay_mod = load("recall_replay", "recall-replay.py")


class HostMemoryTests(unittest.TestCase):
    def test_scan_detects_all_four_structural_signals(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "present.md").write_text("[[absent]]", encoding="utf-8")
            (root / "unlisted.md").write_text("orphan file", encoding="utf-8")
            (root / "MEMORY.md").write_text(
                "<!-- 计数：9 -->\n- [Present](present.md) — \n- [Gone](gone.md) — hook\n",
                encoding="utf-8")
            edges = [s["edge"] for s in scan.scan_memory_signals(root)]
            self.assertEqual(len(edges), 4)
            self.assertTrue(any("孤儿索引行" in x and "漏索引文件" in x for x in edges))
            self.assertTrue(any("悬空" in x for x in edges))
            self.assertTrue(any("计数锚点" in x for x in edges))
            self.assertTrue(any("钩子缺失" in x for x in edges))

    def test_explicit_missing_index_is_reported_and_valid_index_is_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            missing = scan.scan_memory_signals(root)
            self.assertEqual(len(missing), 1)
            self.assertIn("缺少记忆索引", missing[0]["edge"])
            self.assertEqual(scan._scan_index(root / "MEMORY.md"), [])  # legacy behavior
            (root / "a.md").write_text("body", encoding="utf-8")
            (root / "MEMORY.md").write_text("<!-- 计数：1 -->\n- [A](a.md) — useful hook\n", encoding="utf-8")
            self.assertEqual(scan.scan_memory_signals(root), [])

    def test_index_cannot_hide_escape_behind_existing_filename(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "memory"
            root.mkdir()
            (root / "a.md").write_text("local body", encoding="utf-8")
            (root / "MEMORY.md").write_text("- [A](../a.md) — hook\n", encoding="utf-8")
            self.assertTrue(any("超出本层正文范围" in row["edge"]
                                for row in scan.scan_memory_signals(root)))
            self.assertEqual(scan._scan_index(root / "MEMORY.md"), [])  # legacy unchanged

    def test_repository_index_points_to_content_and_production_recall_uses_it(self):
        root = BASE.parents[1] / "memory"
        index = root / "MEMORY.md"
        text = index.read_text(encoding="utf-8")
        links = list(scan.IDX_LINE_RE.finditer(text))
        self.assertTrue(links)
        self.assertEqual(scan.scan_memory_signals(root), [])
        bodies = {p.resolve() for p in root.glob("*.md") if p.name != "MEMORY.md"}
        self.assertEqual({(root / m.group(2)).resolve() for m in links}, bodies)
        for line in text.splitlines():
            self.assertTrue(not line.strip() or line.startswith(("#", "<!--"))
                            or scan.IDX_LINE_RE.fullmatch(line), line)
        kr = replay_mod._load_kr(root)
        entries = kr._load_memory_index(index)
        self.assertEqual({Path(e["path"]).resolve() for e in entries}, bodies)
        self.assertTrue(all(p.read_text(encoding="utf-8").strip() for p in bodies))
        result = replay_mod.replay(kr, ["用户偏好 工作方式"], entries)
        self.assertEqual(result["probes_hit"], 1)

    def test_fixture_replay_hit_and_miss(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "MEMORY.md").write_text("- [General note](entry.md) — routine checklist\n", encoding="utf-8")
            (root / "entry.md").write_text("---\ntrigger: quasar widget\n---\nbody\n", encoding="utf-8")
            kr = replay_mod._load_kr(root)
            entries = kr._load_memory_index(root / "MEMORY.md")
            self.assertIn("quasar widget", entries[0]["anchor"])
            result = replay_mod.replay(kr, ["quasar widget", "orchard unrelated"], entries)
            self.assertEqual(result["probes_hit"], 1)
            self.assertEqual(result["hit_rate"], 0.5)

    def test_parser_has_no_host_sources_or_default_memory_lookup(self):
        kr = replay_mod._load_kr()
        self.assertTrue(hasattr(kr, "_tokens"))
        self.assertFalse(hasattr(kr, "REPO"))
        self.assertFalse(hasattr(kr, "KNOWLEDGE"))
        with self.assertRaisesRegex(ValueError, "memory-root is required"):
            scan.scan_memory_signals()

    def test_replay_rejects_index_escape_and_symlink_escape(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "memory"
            root.mkdir()
            index = root / "MEMORY.md"
            index.write_text("- [Escape](../outside.md) — hook\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                replay_mod._validate_index_paths(index, root)
            outside = base / "outside.md"
            outside.write_text("---\ntrigger: privateword\n---\n", encoding="utf-8")
            (root / "alias.md").symlink_to(outside)
            index.write_text("- [Alias](alias.md) — hook\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                replay_mod._validate_index_paths(index, root)

    def test_missing_probe_data_is_no_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(replay_mod._probes(root), [])
            kr = replay_mod._load_kr(root)
            self.assertIsNone(replay_mod.replay(kr, [], [])["hit_rate"])

    def test_cli_empty_fixture_reports_no_evidence_and_writes_only_data_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            memory, data, isolated_home = base / "memory", base / "data", base / "home"
            memory.mkdir()
            data.mkdir()
            isolated_home.mkdir()
            env = dict(os.environ, HOME=str(isolated_home))
            cmd = [sys.executable, str(BASE / "scripts" / "recall-replay.py"), "r0",
                   "--memory-root", str(memory), "--data-root", str(data)]
            result = subprocess.run(cmd, capture_output=True, text=True, env=env)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("探针 0 条", result.stdout)
            report = data / ".adas-assist" / ".build" / "memory-replay-r0.json"
            self.assertTrue(report.is_file())
            self.assertFalse((isolated_home / ".adas-assist").exists())

    def test_fixture_data_paths_and_tag_cannot_escape_or_leak_sentinel(self):
        sentinel_text = "SENTINEL_OUTSIDE_DATA_ROOT_9f31"
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            memory = base / "memory"
            memory.mkdir()
            isolated_home = base / "home"
            isolated_home.mkdir()
            sentinel = base / "outside.json"
            sentinel.write_text(sentinel_text, encoding="utf-8")
            env = dict(os.environ, HOME=str(isolated_home))

            def run(data: Path, tag: str):
                cmd = [sys.executable, str(BASE / "scripts" / "recall-replay.py"), tag,
                       "--memory-root", str(memory), "--data-root", str(data)]
                return subprocess.run(cmd, capture_output=True, text=True, env=env)

            cases = []
            for name, tag, target_name in (
                ("probe", "r0", "reflex-hooks.jsonl"),
                ("output", "r0", "memory-replay-r0.json"),
                ("baseline", "r1", "memory-replay-r0.json"),
            ):
                data = base / name
                protected = data / ".adas-assist" / ".build" / target_name
                protected.parent.mkdir(parents=True)
                try:
                    protected.symlink_to(sentinel)
                except OSError:
                    self.skipTest("symlinks unavailable")
                cases.append((run(data, tag), name))
            cases.append((run(base / "tag_escape", "../outside"), "tag"))

            for result, label in cases:
                self.assertNotEqual(result.returncode, 0, label)
                self.assertNotIn(sentinel_text, result.stdout + result.stderr, label)
                self.assertEqual(sentinel.read_text(encoding="utf-8"), sentinel_text, label)

    def test_scan_does_not_follow_symlinked_memory_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root, outside = base / "memory", base / "outside.md"
            root.mkdir()
            outside.write_text("[[secret]]", encoding="utf-8")
            (root / "MEMORY.md").write_text("", encoding="utf-8")
            try:
                (root / "linked.md").symlink_to(outside)
            except OSError:
                self.skipTest("symlinks unavailable")
            # Explicit roots must not traverse content outside the supplied root.
            signals = scan.scan_memory_signals(root)
            self.assertFalse(any("secret" in s["edge"] for s in signals))

    def test_scan_rejects_symlinked_memory_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root, external = base / "memory", base / "external.md"
            root.mkdir()
            external.write_text("private", encoding="utf-8")
            try:
                (root / "MEMORY.md").symlink_to(external)
            except OSError:
                self.skipTest("symlinks unavailable")
            with self.assertRaises(ValueError):
                scan.scan_memory_signals(root)


if __name__ == "__main__":
    unittest.main()
