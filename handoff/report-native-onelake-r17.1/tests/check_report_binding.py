"""Validate the separate TEST connection and preserve every business visual byte."""
from io import BytesIO
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import bind_test_report as binding


class ReportBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = binding.SOURCE.read_bytes()
        cls.instructions = (ROOT / "NEXT - REFRESH AND OPEN TEST.txt").read_text()
        cls.payload, cls.changed, cls.preserved = binding.build_package(cls.original, cls.instructions)

    def test_original_is_unchanged_and_output_is_reproducible(self):
        self.assertEqual(binding.sha256(self.original), binding.SOURCE_SHA256)
        self.assertEqual(binding.SOURCE.read_bytes(), self.original)
        self.assertEqual(binding.build_package(self.original, self.instructions)[0], self.payload)
        delivered = ROOT / "candidate" / (binding.PROJECT + ".zip")
        self.assertEqual(delivered.read_bytes(), self.payload)

    def test_only_test_model_is_bound_and_project_reference_resolves(self):
        with zipfile.ZipFile(BytesIO(self.payload)) as z:
            project = json.loads(z.read(binding.PROJECT + ".pbip"))
            report = project["artifacts"][0]["report"]["path"]
            pbir = json.loads(z.read(report + "/definition.pbir"))
            connection = pbir["datasetReference"]["byConnection"]["connectionString"]
            self.assertIn("semanticModelId=" + binding.TEST_ID, connection)
            self.assertIn('Initial Catalog="' + binding.TEST_MODEL + '"', connection)
            self.assertNotIn(binding.SOURCE_ID, connection)
            self.assertIn("Access Mode=readonly", connection)
            self.assertEqual(z.testzip(), None)

    def test_all_visuals_and_refresh_page_retain_original_bytes(self):
        with zipfile.ZipFile(BytesIO(self.original)) as old, zipfile.ZipFile(BytesIO(self.payload)) as new:
            changed = set(self.changed)
            checked = []
            for name in old.namelist():
                if not name.startswith(binding.SOURCE_PREFIX):
                    continue
                relative = name.removeprefix(binding.SOURCE_PREFIX)
                new_name = relative.replace(binding.OLD_PROJECT + ".Report/", binding.PROJECT + ".Report/", 1)
                if relative.endswith(".pbip"):
                    continue
                if new_name in changed:
                    continue
                self.assertEqual(new.read(new_name), old.read(name), new_name)
                checked.append(new_name)
            self.assertEqual(len(checked), 136)
            self.assertTrue(any("refreshdemand/" in n for n in checked))
            self.assertTrue(any("native_demand/" in n for n in checked))
            self.assertTrue(any("native_sop/" in n for n in checked))

    def test_old_installers_and_cached_models_are_excluded(self):
        with zipfile.ZipFile(BytesIO(self.payload)) as z:
            names = z.namelist()
            self.assertEqual(len(names), len(set(names)))
            self.assertEqual(set(n for n in names if "/" not in n), {binding.PROJECT + ".pbip", "OPEN FIRST.txt"})
            for name in names:
                self.assertFalse(name.endswith((".sql", ".py", ".pbix", ".pbit", ".abf", ".bim", ".tmdl")))
                self.assertNotIn("..", Path(name).parts)
            self.assertEqual(z.read("OPEN FIRST.txt").decode(), self.instructions)

    def test_changed_original_and_existing_different_output_are_refused(self):
        with self.assertRaises(ValueError):
            binding.build_package(self.original + b"changed", self.instructions)
        with TemporaryDirectory() as directory:
            target = Path(directory)
            (target / "candidate").mkdir()
            (target / "NEXT - REFRESH AND OPEN TEST.txt").write_text(self.instructions)
            output = target / "candidate" / (binding.PROJECT + ".zip")
            output.write_bytes(b"preserve existing")
            with patch.object(binding, "HERE", target), self.assertRaises(ValueError):
                binding.main()
            self.assertEqual(output.read_bytes(), b"preserve existing")


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ReportBindingTests)
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    (ROOT / "VALIDATION-REPORT-BINDING.json").write_text(json.dumps({
        "Tests": result.testsRun, "Passed": result.wasSuccessful(),
        "Evidence": "Local ZIP/project/binding checks only; no company calls or Desktop rendering.",
        "SourceZIPUnchanged": True, "UnchangedProjectPayloads": 136,
        "ChangedProjectPayloads": 2, "OriginalConnectionTargetReplacedOnlyInCopy": True,
        "GraphConclusion": "UNKNOWN; GitNexus reports Coordination is not registered.",
        "CompanyProcessing": "UNVERIFIED", "CompanyNativeRendering": "UNVERIFIED",
        "Publication": False}, indent=2) + "\n")
    raise SystemExit(not result.wasSuccessful())
