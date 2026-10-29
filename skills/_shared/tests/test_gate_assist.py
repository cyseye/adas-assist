"""Result-level CLI regressions for gate-assist verify-judge."""
import json
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "gate-assist.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("gate_assist", SCRIPT)
gate_assist = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate_assist)
NAMES = ["正确性", "安全性", "规范性", "完整性"]
WEIGHTS = [0.4, 0.3, 0.2, 0.1]


def report(*, tier="standard", round_no=1, severity=None, must_fix=None, floor=80,
           score_dimension=None, prev_scores=None):
    dims = []
    for name, weight in zip(NAMES, WEIGHTS):
        issues = []
        if severity and (score_dimension is None or score_dimension == name):
            issues = [{"severity": severity}]
        dims.append({"name": name, "weight": weight, "floor": floor,
                     "issues": issues})
    result = {"tier": tier, "round": round_no, "dimensions": dims}
    if must_fix is not None:
        result["must_fix"] = must_fix
    if prev_scores is not None:
        result["prev_scores"] = prev_scores
    return result


def run(data, *args):
    return subprocess.run([sys.executable, "-B", str(SCRIPT), "verify-judge", *args],
                          input=json.dumps(data, ensure_ascii=False), text=True,
                          capture_output=True)


class VerifyJudgeTests(unittest.TestCase):
    def test_valid_clean_pass(self):
        p = run(report())
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads(p.stdout)["verdict"], "PASS")

    def test_clean_terminal_rounds_and_plateau_still_pass(self):
        cases = [("full", 5, []), ("standard", 3, []), ("standard", 2, [100])]
        for tier, round_no, prev_scores in cases:
            with self.subTest(tier=tier, round_no=round_no, prev_scores=prev_scores):
                p = run(report(tier=tier, round_no=round_no, prev_scores=prev_scores),
                        "--tier", tier)
                self.assertEqual(p.returncode, 0, p.stderr)
                self.assertEqual(json.loads(p.stdout)["verdict"], "PASS")

    def test_floor_breach_blocks_high_total(self):
        p = run(report(severity="P0", score_dimension="正确性"))
        self.assertEqual(p.returncode, 0, p.stderr)
        result = json.loads(p.stdout)
        self.assertGreaterEqual(result["total"], 90)
        self.assertEqual(result["verdict"], "FIXABLE")

    def test_must_fix_never_pass_and_survives_final_pcf(self):
        data = report(tier="full", round_no=5, must_fix=[{"type": "x"}])
        p = run(data, "--tier", "full")
        self.assertEqual(p.returncode, 0, p.stderr)
        result = json.loads(p.stdout)
        self.assertEqual(result["verdict"], "PCF")
        self.assertIn("must_fix=1", result["constraints"])
        self.assertEqual(result["must_fix_count"], 1)

    def test_security_p0_is_automatically_must_fix(self):
        p = run(report(severity="P0", score_dimension="安全性"))
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads(p.stdout)["verdict"], "FIXABLE")

    def test_floor_breach_survives_full_final_pcf(self):
        p = run(report(tier="full", round_no=5, severity="P0"), "--tier", "full")
        self.assertEqual(p.returncode, 0, p.stderr)
        result = json.loads(p.stdout)
        self.assertEqual(result["verdict"], "PCF")
        self.assertTrue(any(item.startswith("floor_breaches=") for item in result["constraints"]))

    def test_standard_and_full_terminal_rounds(self):
        for tier, final_round, earlier in [("standard", 3, 2), ("full", 5, 4)]:
            with self.subTest(tier=tier):
                at_final = run(report(tier=tier, round_no=final_round, severity="P0"), "--tier", tier)
                before = run(report(tier=tier, round_no=earlier, severity="P0"), "--tier", tier)
                self.assertEqual(json.loads(at_final.stdout)["verdict"], "PCF")
                self.assertEqual(json.loads(before.stdout)["verdict"], "FIXABLE")

    def test_critical_is_full_only_and_uses_sixty(self):
        data = report(tier="full", severity="P0", score_dimension="正确性")
        for dim in data["dimensions"]:
            dim["issues"] = [{"severity": "P0"}] * 3
        full = json.loads(run(data, "--tier", "full").stdout)
        standard_data = dict(data, tier="standard")
        standard = json.loads(run(standard_data, "--tier", "standard").stdout)
        self.assertEqual(full["verdict"], "PCF")
        self.assertEqual(standard["verdict"], "FIXABLE")

    def test_slug_rejects_path_traversal(self):
        for slug in ("", ".", "..", "../outside", "a/b", "a\\b"):
            with self.subTest(slug=slug), self.assertRaises(ValueError):
                gate_assist.build_dir(slug)

    def test_build_dir_rejects_data_root_symlink_escape(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            asset = base / "asset"
            (asset / "skills").mkdir(parents=True)
            data, outside = base / "data", base / "outside"
            data.mkdir(); outside.mkdir()
            (data / ".build").symlink_to(outside, target_is_directory=True)
            old_asset = os.environ.get("ADAS_ASSIST_ASSET_ROOT")
            old_data = os.environ.get("ADAS_ASSIST_DATA_ROOT")
            try:
                os.environ["ADAS_ASSIST_ASSET_ROOT"] = str(asset)
                os.environ["ADAS_ASSIST_DATA_ROOT"] = str(data)
                with self.assertRaisesRegex(ValueError, "escapes ADAS_ASSIST_DATA_ROOT"):
                    gate_assist.build_dir("fixture")
            finally:
                if old_asset is None:
                    os.environ.pop("ADAS_ASSIST_ASSET_ROOT", None)
                else:
                    os.environ["ADAS_ASSIST_ASSET_ROOT"] = old_asset
                if old_data is None:
                    os.environ.pop("ADAS_ASSIST_DATA_ROOT", None)
                else:
                    os.environ["ADAS_ASSIST_DATA_ROOT"] = old_data

    def test_finish_batch_rejects_state_symlink_escape(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            asset = base / "asset"
            (asset / "skills").mkdir(parents=True)
            data, outside, cwd = base / "data", base / "outside", base / "cwd"
            data.mkdir(); outside.mkdir(); cwd.mkdir()
            (data / ".state").symlink_to(outside, target_is_directory=True)
            env = os.environ.copy()
            env["ADAS_ASSIST_ASSET_ROOT"] = str(asset)
            env["ADAS_ASSIST_DATA_ROOT"] = str(data)
            p = subprocess.run([sys.executable, "-B", str(SCRIPT), "finish-batch", "--write"],
                               cwd=cwd, env=env, text=True, capture_output=True)
            self.assertNotEqual(p.returncode, 0, p.stdout + p.stderr)
            self.assertFalse((outside / "finish-verdicts.jsonl").exists())

    def test_pcf_save_rejects_leaf_symlink_and_preserves_external_sentinel(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            asset = base / "asset"
            (asset / "skills").mkdir(parents=True)
            data, outside = base / "data", base / "outside.md"
            data.mkdir()
            outside.write_text("sentinel", encoding="utf-8")
            target_dir = data / ".build" / "fixture"
            target_dir.mkdir(parents=True)
            (target_dir / "pcf.proposer.md").symlink_to(outside)
            content = base / "content.md"
            content.write_text("replacement", encoding="utf-8")
            env = os.environ.copy()
            env["ADAS_ASSIST_ASSET_ROOT"] = str(asset)
            env["ADAS_ASSIST_DATA_ROOT"] = str(data)
            p = subprocess.run([sys.executable, "-B", str(SCRIPT), "pcf-save", "--slug",
                                "fixture", "--role", "proposer", "--content-file", str(content)],
                               cwd=base, env=env, text=True, capture_output=True)
            self.assertNotEqual(p.returncode, 0, p.stdout + p.stderr)
            self.assertEqual(outside.read_text(encoding="utf-8"), "sentinel")

    def test_pcf_context_rejects_leaf_symlink_and_does_not_read_external_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            asset = base / "asset"
            (asset / "skills").mkdir(parents=True)
            data, outside = base / "data", base / "outside.md"
            data.mkdir()
            outside.write_text("private sentinel", encoding="utf-8")
            target_dir = data / ".build" / "fixture"
            target_dir.mkdir(parents=True)
            (target_dir / "pcf.proposer.md").symlink_to(outside)
            env = os.environ.copy()
            env["ADAS_ASSIST_ASSET_ROOT"] = str(asset)
            env["ADAS_ASSIST_DATA_ROOT"] = str(data)
            p = subprocess.run([sys.executable, "-B", str(SCRIPT), "pcf-context", "--slug",
                                "fixture", "--to", "critic"], cwd=base, env=env,
                               text=True, capture_output=True)
            self.assertNotEqual(p.returncode, 0, p.stdout + p.stderr)
            self.assertNotIn("private sentinel", p.stdout)
            self.assertEqual(outside.read_text(encoding="utf-8"), "private sentinel")

    def test_plateau_and_threshold_boundary(self):
        p = run(report(must_fix=[{"type": "x"}], prev_scores=[100]))
        self.assertEqual(json.loads(p.stdout)["verdict"], "PCF")
        threshold = report()
        threshold["thresholds"] = {"pass": 90, "critical": 60, "converge": 5, "max_rounds": 3}
        self.assertEqual(run(threshold).returncode, 0)
        threshold["thresholds"]["critical"] = 70
        self.assertNotEqual(run(threshold).returncode, 0)

    def test_quick_is_rejected_by_scored_command(self):
        p = run(report(tier="quick"), "--tier", "quick")
        self.assertNotEqual(p.returncode, 0)

    def test_invalid_inputs_fail_closed(self):
        cases = []
        d = report(); del d["dimensions"][0]["floor"]; cases.append(d)
        d = report(severity="BLOCKER"); cases.append(d)
        d = report(severity=None); d["dimensions"][0]["issues"] = [{}]; cases.append(d)
        d = report(); d["dimensions"][0]["weight"] = -0.1; cases.append(d)
        d = report(); d["dimensions"][0]["weight"] = float("nan"); cases.append(d)
        d = report(); d["dimensions"][0]["floor"] = 0; cases.append(d)
        d = report(); d["dimensions"][0]["floor"] = 79; cases.append(d)
        d = report(); d["dimensions"] = []; cases.append(d)
        d = report(); d["dimensions"][0]["issues"] = None; cases.append(d)
        for data in cases:
            with self.subTest(data=data):
                self.assertNotEqual(run(data).returncode, 0)

    def test_base_profile_unknown_severity_rejected(self):
        data = {"dimensions": [{"name": "d", "weight": 1, "floor": 80,
                                "issues": [{"severity": "P0"}]}]}
        self.assertNotEqual(run(data, "--profile", "base").returncode, 0)

    def test_profile_base_known_severity_keeps_legacy_json_fields(self):
        data = {"dimensions": [{"name": "d", "weight": 1, "floor": 80,
                                "issues": [{"severity": "BLOCKER"}]}]}
        p = run(data, "--profile", "base")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(set(json.loads(p.stdout)),
                         {"verdict", "reason", "total", "dimension_scores", "floor_breaches"})


if __name__ == "__main__":
    unittest.main()
