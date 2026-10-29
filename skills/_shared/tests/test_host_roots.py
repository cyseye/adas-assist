"""Fixture tests for explicit asset/data roots in shared_state."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "shared_state.py"
PROBE = (
    "import importlib.util,json;"
    f"s=importlib.util.spec_from_file_location('shared_state',{str(SCRIPT)!r});"
    "m=importlib.util.module_from_spec(s);s.loader.exec_module(m);"
    "print(json.dumps({'asset':str(m.asset_root()),'data':str(m.data_root())}))"
)


class HostRootsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.asset = self.base / "asset"
        self.asset.mkdir()
        (self.asset / "skills").mkdir()
        self.data = self.base / "runtime-data"
        self.data.mkdir()
        self.cwd = self.base / "unrelated-cwd"
        self.cwd.mkdir()
        (self.cwd / ".codex").mkdir()

    def invoke(self, asset=None, data=None):
        env = os.environ.copy()
        env.pop("ADAS_ASSIST_ASSET_ROOT", None)
        env.pop("ADAS_ASSIST_DATA_ROOT", None)
        if asset is not None:
            env["ADAS_ASSIST_ASSET_ROOT"] = str(asset)
        if data is not None:
            env["ADAS_ASSIST_DATA_ROOT"] = str(data)
        return subprocess.run([sys.executable, "-B", "-c", PROBE], cwd=self.cwd,
                              env=env, text=True, capture_output=True)

    def test_explicit_roots_select_distinct_asset_and_data_fixtures(self):
        p = self.invoke(self.asset, self.data)
        self.assertEqual(p.returncode, 0, p.stderr)
        import json
        result = json.loads(p.stdout)
        self.assertEqual(Path(result["asset"]), self.asset.resolve())
        self.assertEqual(Path(result["data"]), self.data.resolve())

    def test_missing_pair_and_relative_roots_fail_closed(self):
        for asset, data in ((self.asset, None), (None, self.data),
                            ("relative-assets", self.data), (self.asset, "relative-data")):
            with self.subTest(asset=asset, data=data):
                p = self.invoke(asset, data)
                self.assertNotEqual(p.returncode, 0)
                self.assertTrue(any(message in p.stderr for message in (
                    "ADAS_ASSIST_ASSET_ROOT and ADAS_ASSIST_DATA_ROOT must be supplied together",
                    "adas-assist roots must be absolute paths")), p.stderr)

    def test_missing_roots_never_fall_back_to_host_configuration(self):
        p = self.invoke()
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("must be supplied together", p.stderr)

    def test_asset_root_without_skills_directory_is_rejected(self):
        empty = self.base / "empty"
        empty.mkdir()
        p = self.invoke(empty, self.data)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("must contain skills/", p.stderr)

    def test_data_root_build_symlink_cannot_redirect_state_write(self):
        outside = self.base / "outside-build"
        outside.mkdir()
        (self.data / ".build").symlink_to(outside, target_is_directory=True)
        code = PROBE.replace(
            "print(json.dumps({'asset':str(m.asset_root()),'data':str(m.data_root())}))",
            "m.atomic_write(m.data_root() / '.build' / 'state.json', 'fixture-state')",
        )
        env = os.environ.copy()
        env["ADAS_ASSIST_ASSET_ROOT"] = str(self.asset)
        env["ADAS_ASSIST_DATA_ROOT"] = str(self.data)
        p = subprocess.run([sys.executable, "-B", "-c", code], cwd=self.cwd, env=env,
                           text=True, capture_output=True)
        self.assertNotEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertFalse((outside / "state.json").exists())


if __name__ == "__main__":
    unittest.main()
