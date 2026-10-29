"""Static repository inventory and protocol markers; not a runtime compatibility suite."""
from __future__ import annotations

import ast
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
REPORT = Path("/tmp/adas-validation-repository-contract.json")
EXPECTED_SHARED_PROTOCOLS = (
    "assessment-protocol.md",
    "pcf-execution-flow.md",
    "review-gate-skeleton.md",
    "socratic-inquiry.md",
)


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def all_source_paths() -> list[str]:
    excluded = {".git", "__pycache__", ".build"}
    paths = []
    for path in ROOT.rglob("*"):
        rel = relative(path)
        if any(part in excluded for part in Path(rel).parts) or path.suffix == ".pyc":
            continue
        if path.is_file() or path.is_symlink():
            paths.append(rel)
    return sorted(set(paths))


def symlink_inventory() -> list[dict]:
    rows = []
    for link in sorted((ROOT / ".agents" / "skills").iterdir()):
        if not link.is_symlink():
            continue
        target = link.resolve()
        rows.append({"link": relative(link), "target": relative(target),
                     "samefile": link.exists() and link.samefile(target)})
    return rows


def source_inventory() -> dict:
    paths = all_source_paths()
    python_files = [ROOT / rel for rel in paths if rel.endswith(".py")]
    ast_rows = []
    for path in python_files:
        ast.parse(path.read_text(encoding="utf-8"), filename=relative(path))
        ast_rows.append(relative(path))
    json_files = [ROOT / rel for rel in paths if rel.endswith(".json")]
    json_rows = []
    for path in json_files:
        value = json.loads(path.read_text(encoding="utf-8"))
        json_rows.append({"path": relative(path), "top_level_type": type(value).__name__,
                          "fields": list(value) if isinstance(value, dict) else []})
    return {"python_ast_files": ast_rows, "json_files": json_rows}


def categorized_files() -> dict:
    symlinks = symlink_inventory()
    skills = []
    for entry in sorted((ROOT / ".agents" / "skills").iterdir()):
        if entry.name in {"_shared", "scripts"}:
            continue
        skill_doc = entry / "SKILL.md"
        if skill_doc.is_file():
            skills.append({"name": entry.name, "entry": relative(entry),
                           "target": relative(entry.resolve()),
                           "skill_document": relative(skill_doc)})

    decisions = sorted(relative(p) for p in (ROOT / "decisions").rglob("*") if p.is_file())
    decision_links = []
    link_re = re.compile(r"\[[^]]+\]\(([^)]+)\)")
    for rel in decisions:
        path = ROOT / rel
        if path.name.lower() == "knowledge.md":
            for target in link_re.findall(path.read_text(encoding="utf-8")):
                if "://" in target or target.startswith("#"):
                    continue
                resolved = (path.parent / target.split("#", 1)[0]).resolve()
                decision_links.append({"source": rel, "target": target,
                                       "exists": resolved.exists()})

    memory_paths = sorted(relative(p) for p in (ROOT / "memory").rglob("*") if p.is_file())
    universe = set(all_source_paths())
    categories = {
        "host_discovery": sorted(p for p in universe if p.startswith(".agents/")),
        "skills": sorted(p for p in universe if p.startswith("skills/")),
        "commands": sorted(p for p in universe if p.startswith("commands/")),
        "roles": sorted(p for p in universe if p.startswith("agents/")),
        "standards": sorted(p for p in universe if p.startswith("standards/")),
        "memory": sorted(p for p in universe if p.startswith("memory/")),
        "decisions": sorted(p for p in universe if p.startswith("decisions/")),
        "bootstrap": sorted(p for p in universe if p.startswith("bootstrap/")),
        "project_docs": sorted(p for p in universe if p.startswith("doc/")),
        "repository_entrypoints": sorted(p for p in universe if p in {
            ".gitignore", "AGENTS.md", "README.md"}),
    }
    classified = [path for paths in categories.values() for path in paths]
    unclassified = sorted(universe - set(classified))
    multiply_classified = sorted(path for path in set(classified) if classified.count(path) > 1)
    docs_range = sorted(p for p in universe if p.startswith("doc/") or
                        Path(p).name in {"AGENTS.md", "README.md", "EVOLUTION.md", "SKILL.md"})
    return {
        "skill_discovery_entries": skills,
        "skill_documents": [row["skill_document"] for row in skills],
        "support_entries_without_skill_document": [row["link"] for row in symlinks
                                                   if Path(row["link"]).name == "scripts"],
        "commands": sorted(relative(p) for p in (ROOT / "commands").glob("*.md") if p.is_file()),
        "roles": sorted({relative(p) for pattern in ("agents/*.md", "skills/**/agents/*.md")
                          for p in ROOT.glob(pattern) if p.is_file()}),
        "standards": sorted(relative(p) for p in (ROOT / "standards").rglob("*.md") if p.is_file()),
        "memory_assets": memory_paths,
        "decision_indexes_and_records": decisions,
        "decision_index_files": [p for p in decisions if p.lower().endswith("knowledge.md")],
        "decision_record_files": [p for p in decisions if not p.lower().endswith("knowledge.md")],
        "decision_index_links": decision_links,
        "shared_protocols": [relative(ROOT / "skills" / "_shared" / p) for p in EXPECTED_SHARED_PROTOCOLS],
        "skill_links": symlinks,
        "all_source_paths": sorted(universe),
        "path_categories": categories,
        "unclassified_paths": unclassified,
        "multiply_classified_paths": multiply_classified,
        "readable_project_docs_and_history": docs_range,
        "shared_markdown_protocols": sorted(p for p in universe if p.startswith("skills/_shared/") and p.endswith(".md")),
        "references": sorted(p for p in universe if p.startswith("skills/") and "/references/" in p),
        "templates": sorted(p for p in universe if p.startswith("skills/") and "/templates/" in p),
        "bootstrap_json": sorted(p for p in universe if p.startswith("bootstrap/") and p.endswith(".json")),
    }


def template_contracts() -> dict:
    base = ROOT / "skills" / "devils-panel"
    consumer = (base / "references" / "integration-mapping.md").read_text(encoding="utf-8")
    result = {}
    for name in ("adversary-report.json", "adversary-summary.json"):
        fields = list(json.loads((base / "templates" / name).read_text(encoding="utf-8")))
        mentioned = [field for field in fields if field in consumer]
        missing = [field for field in fields if field not in consumer]
        result[name] = {"template_fields": fields, "consumer_mentions": mentioned,
                        "unreferenced_fields": missing,
                        "static_alignment": "complete" if not missing else "partial"}
    return result


def run_secret_scan_fixture() -> dict:
    """Run the shared scanner helpers from a copied, disposable fixture directory."""
    shared = ROOT / "skills" / "_shared" / "scripts"
    patterns_src = ROOT / "skills" / "_shared" / "security-patterns.json"
    with tempfile.TemporaryDirectory(prefix="repo_contract_secret_") as tmp:
        sandbox = Path(tmp)
        script = sandbox / "secret-scan.py"
        shutil.copy2(shared / "secret-scan.py", script)
        patterns = json.loads(patterns_src.read_text(encoding="utf-8"))["patterns"]
        code = (
            "# -*- coding: utf-8 -*-\n"
            "import importlib.util,json,re\n"
            f"spec=importlib.util.spec_from_file_location('secret_scan',{str(script)!r})\n"
            "m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)\n"
            f"patterns={patterns!r}\n"
            "def hits(text):\n"
            " out=[]\n"
            " for variant, value in m.normalized_texts(text).items():\n"
            "  for p in patterns:\n"
            "   if p.get('level') == 'L2' and re.search(p['re'], value, re.I): out.append(p['id'])\n"
            " return sorted(set(out))\n"
            "print(json.dumps({'positive':hits('synthetic sk-12345678901234567890'),"
            "'negative':hits('ordinary public documentation')}))\n"
        )
        harness = sandbox / "run_fixture.py"
        harness.write_text(code, encoding="utf-8")
        run = subprocess.run([sys.executable, str(harness)], cwd=sandbox,
                             capture_output=True, text=True)
        if run.returncode:
            raise RuntimeError(f"isolated secret-scan fixture failed: {run.stderr[-1200:]}")
        result = json.loads(run.stdout)
        result["isolated_temp_directory"] = True
        result["positive_is_synthetic"] = True
        result["scanner_source"] = relative(shared / "secret-scan.py")
        return result


def build_report() -> dict:
    assets = categorized_files()
    links = assets["skill_links"]
    discoveries = assets["skill_discovery_entries"]
    source = source_inventory()
    return {
        "scope": "static inventory and protocol markers; not full runtime compatibility",
        "assets": assets,
        "counts": {
            "skill_symlinks": len(links),
            "skill_discovery_entries": len(discoveries),
            "skill_documents": len(assets["skill_documents"]),
            "commands": len(assets["commands"]),
            "roles": len(assets["roles"]),
            "standards": len(assets["standards"]),
            "memory_assets": len(assets["memory_assets"]),
            "decision_indexes_and_records": len(assets["decision_indexes_and_records"]),
            "python_ast_files": len(source["python_ast_files"]),
            "json_files": len(source["json_files"]),
            "all_source_paths": len(assets["all_source_paths"]),
            "references": len(assets["references"]),
            "templates": len(assets["templates"]),
            "shared_markdown_protocols": len(assets["shared_markdown_protocols"]),
            "bootstrap_json": len(assets["bootstrap_json"]),
        },
        "source_inventory": source,
        "template_contracts": template_contracts(),
        "secret_scan_fixture": run_secret_scan_fixture(),
    }


class RepositoryContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()
        REPORT.write_text(json.dumps(cls.report, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8")

    def test_symlink_inventory_resolves_to_same_files(self):
        links = self.report["assets"]["skill_links"]
        expected = {"skills/_shared", "skills/scripts"} | {
            relative(source) for source in (ROOT / "skills").iterdir()
            if (source / "SKILL.md").is_file()
        }
        self.assertEqual({row["target"] for row in links}, expected)
        self.assertEqual(len(links), len(expected))
        self.assertTrue(all(row["samefile"] for row in links), links)

    def test_discovery_and_asset_categories_are_fully_enumerated(self):
        assets = self.report["assets"]
        self.assertEqual(len(assets["skill_discovery_entries"]), 14)
        self.assertEqual(len(assets["commands"]), 2)
        self.assertEqual(len(assets["roles"]), 5)
        self.assertEqual(len(assets["standards"]), 6)
        self.assertIn("memory/MEMORY.md", assets["memory_assets"])
        self.assertIn("memory/USER-PREFERENCES.md", assets["memory_assets"])
        self.assertIn("decisions/KNOWLEDGE.md", assets["decision_indexes_and_records"])
        self.assertTrue(all((ROOT / p).is_file() for p in assets["shared_protocols"]))
        self.assertEqual(assets["unclassified_paths"], [])
        self.assertEqual(assets["multiply_classified_paths"], [])
        self.assertTrue(assets["references"])
        self.assertTrue(assets["templates"])
        self.assertTrue(assets["shared_markdown_protocols"])
        self.assertEqual(assets["bootstrap_json"], [])
        self.assertFalse((ROOT / "CLAUDE.md").exists())
        self.assertFalse((ROOT / "bootstrap").exists())
        self.assertFalse((ROOT / "package").exists())
        for source in (ROOT / "skills").iterdir():
            if (source / "SKILL.md").is_file() or source.name in {"_shared", "scripts"}:
                entry = ROOT / ".agents/skills" / source.name
                self.assertTrue(entry.is_symlink(), str(entry))
                self.assertFalse(Path(entry.readlink()).is_absolute())
                self.assertEqual(entry.resolve(), source.resolve())

    def test_document_links_are_relative_and_resolve(self):
        # Placeholders document a schema, rather than naming an existing file.
        documents = [ROOT / name for name in ("README.md", "AGENTS.md")]
        for directory in ("skills", "commands", "agents", "standards", "doc"):
            documents.extend((ROOT / directory).rglob("*.md"))
        failures = []
        for path in documents:
            for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
                if target.startswith("#") or "{" in target:
                    continue
                if "://" in target or target.startswith(("/", "~")) or not (path.parent / target.split("#", 1)[0]).exists():
                    failures.append((relative(path), target))
        self.assertEqual(failures, [])

    def test_active_documentation_does_not_address_user_global_assets(self):
        documents = [ROOT / name for name in ("README.md", "AGENTS.md")]
        for directory in ("skills", "commands", "agents", "standards"):
            documents.extend((ROOT / directory).rglob("*.md"))
        forbidden = re.compile(r"~/\.claude/(?:skills|agents|standards|decisions)/|/Users/[^/]+/")
        failures = [relative(path) for path in documents
                    if forbidden.search(path.read_text(encoding="utf-8"))]
        self.assertEqual(failures, [])

    def test_python_sources_parse_and_json_assets_load(self):
        source = self.report["source_inventory"]
        self.assertTrue(source["python_ast_files"])
        self.assertTrue(source["json_files"])
        self.assertEqual(self.report["counts"]["python_ast_files"], len(source["python_ast_files"]))

    def test_devils_template_fields_are_reported_against_static_consumer_vocabulary(self):
        contracts = self.report["template_contracts"]
        self.assertEqual(contracts["adversary-report.json"]["static_alignment"], "complete")
        # Static field alignment does not establish runtime behavior.
        self.assertEqual(contracts["adversary-summary.json"]["unreferenced_fields"],
                         [])

    def test_secret_scanner_synthetic_positive_and_negative(self):
        fixture = self.report["secret_scan_fixture"]
        self.assertTrue(fixture["isolated_temp_directory"])
        self.assertTrue(fixture["positive_is_synthetic"])
        self.assertIn("cred-openai", fixture["positive"])
        self.assertEqual(fixture["negative"], [])


if __name__ == "__main__":
    unittest.main()
