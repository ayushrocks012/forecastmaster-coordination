"""Native-only authoring regressions. These checks do not claim Desktop rendering."""
import importlib.util
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
from zipfile import ZipFile

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import prepare_project as p


class NativeOnlyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.project = Path(cls.temp.name) / "native"
        cls.source = HERE.parent / "report-native-r17.2/candidate/ForecastMaster Native Review R17.2 TEST.zip"
        cls.receipt = p.create(cls.source, cls.project)
        cls.report = cls.project / (p.NAME + ".Report")
        cls.root = cls.report / "definition"
        cls.page = json.loads((cls.root / "pages/native_demand/page.json").read_text())
        cls.visuals = {f.parent.name: json.loads(f.read_text()) for f in (cls.root / "pages/native_demand/visuals").glob("*/visual.json")}
        cls.bookmarks = {f.name.removesuffix(".bookmark.json"): json.loads(f.read_text())
                         for f in (cls.root / "bookmarks").glob("*.bookmark.json")}

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_zero_custom_visuals_including_hidden_pages_and_packages(self):
        self.assertFalse((self.report / "CustomVisuals").exists())
        self.assertFalse(list(self.project.rglob("*.pbiviz*")))
        self.assertEqual({v["visual"]["visualType"] for v in self.visuals.values()} - p.BUILTINS, set())
        self.assertEqual([x.name for x in (self.root / "pages").iterdir() if x.is_dir()], ["native_demand"])
        config = json.loads((self.root / "report.json").read_text())
        self.assertFalse([x for x in config["resourcePackages"] if x["type"] == "CustomVisual"])
        self.assertFalse(list(self.project.rglob("*.js")))

    def test_native_query_names_unique_across_all_roles(self):
        # Reproduce the reported fault using the ACTUAL frozen R17.2 headline.
        with ZipFile(self.source) as z:
            path = next(n for n in z.namelist() if n.endswith("native_demand/visuals/headline/visual.json"))
            old = json.loads(z.read(path))
        def refs(v):
            return [q["nativeQueryRef"] for r in v.get("visual", {}).get("query", {}).get("queryState", {}).values() for q in r.get("projections", [])]
        self.assertLess(len(set(refs(old))), len(refs(old)), "The old reported Label collision must be reproduced")
        for v in self.visuals.values():
            self.assertEqual(len(refs(v)), len(set(refs(v))), v["name"])

    def test_semantic_literals_have_numeric_type_suffixes(self):
        bad = []
        def walk(node, name):
            if isinstance(node, dict):
                raw = node.get("Literal", {}).get("Value", "")
                if re.fullmatch(r"-?\d+(?:\.\d+)?", raw):
                    bad.append((name, raw))
                for value in node.values():
                    walk(value, name)
            elif isinstance(node, list):
                for value in node:
                    walk(value, name)
        for name, v in self.visuals.items():
            walk(v, name)
        self.assertEqual(bad, [])
        self.assertEqual(p.lit(10)["expr"]["Literal"]["Value"], "10D")

    def test_native_control_chrome_has_reserved_space(self):
        for name, v in self.visuals.items():
            if v["visual"]["visualType"] != "slicer":
                continue
            obj, vco = v["visual"]["objects"], v["visual"]["visualContainerObjects"]
            self.assertEqual(obj["general"][0]["properties"]["responsive"], p.lit(False))
            self.assertEqual(obj["header"][0]["properties"]["show"], p.lit(True))
            self.assertIn("textSize", obj["items"][0]["properties"])
            self.assertNotIn("fontSize", obj["items"][0]["properties"])
            self.assertIn("padding", vco)
            padding = vco["padding"][0]["properties"]
            top = float(padding["top"]["expr"]["Literal"]["Value"][:-1])
            bottom = float(padding["bottom"]["expr"]["Literal"]["Value"][:-1])
            # Microsoft's native sizing floors, independent of our chosen 88/128.
            chrome = 84 if name == "review_months" else 60
            minimum = ((chrome + top + bottom + 7) // 8) * 8
            self.assertGreaterEqual(v["position"]["height"], minimum)

    def test_visible_visuals_do_not_overlap_and_stay_inside_canvas(self):
        visible = [v for v in self.visuals.values() if not v.get("isHidden")]
        for i, a in enumerate(visible):
            r = a["position"]
            self.assertLessEqual(r["x"] + r["width"], self.page["width"])
            self.assertLessEqual(r["y"] + r["height"], self.page["height"])
            for b in visible[i+1:]:
                s = b["position"]
                overlaps = r["x"] < s["x"]+s["width"] and s["x"] < r["x"]+r["width"] and r["y"] < s["y"]+s["height"] and s["y"] < r["y"]+r["height"]
                self.assertFalse(overlaps, a["name"] + " overlaps " + b["name"])

    def test_real_textboxes_have_native_paragraphs(self):
        for v in self.visuals.values():
            if v["visual"]["visualType"] == "textbox":
                self.assertTrue(v["visual"]["objects"]["general"][0]["properties"]["paragraphs"])

    def test_monthly_chart_is_straight_and_does_not_double_scale_numbers(self):
        v = self.visuals["native_chart"]["visual"]
        self.assertEqual(v["visualType"], "lineChart")
        self.assertEqual(v["objects"]["lineStyles"][0]["properties"]["lineChartType"], p.lit("linear"))
        self.assertEqual(v["objects"]["lineStyles"][0]["properties"]["showMarker"], p.lit(True))
        self.assertEqual(v["objects"]["valueAxis"][0]["properties"]["labelDisplayUnits"], p.lit(1))
        self.assertNotIn("format", v["query"]["queryState"]["Y"]["projections"][0], "Retain dynamic percentages, FX and k/m formats")
        self.assertIn("zoom", v["objects"])
        self.assertNotIn("zoomSlider", v["objects"])
        self.assertEqual(v["visualContainerObjects"]["subTitle"][0]["properties"]["show"], p.lit(False))

    def test_preview_scope_is_honest_and_keeps_amount_guards_in_model(self):
        filters = self.page["filterConfig"]["filters"]
        self.assertEqual(len(filters), 3)
        self.assertIn("Automatic ADS", json.dumps(filters))
        self.assertIn("Local", json.dumps(filters))
        self.assertNotIn("fx_controls", self.visuals)
        self.assertNotIn("file_mode", self.visuals)
        for name in ("headline", "summary_drivers", "summary_sectors", "summary_both"):
            self.assertNotIn("N Scenario Visible", json.dumps(self.visuals[name]))
        # Reuse the installed measures without modifying any amount expression.
        self.assertFalse(list(self.project.rglob("*.bim")))
        self.assertFalse(self.receipt["ModelChanged"])

    def test_metadata_table_is_not_an_accidental_source_override(self):
        table = self.visuals["matching_files"]["visual"]
        self.assertEqual(table["visualType"], "tableEx")
        self.assertNotIn("FileLabel", json.dumps(table))
        self.assertTrue(all(x["type"] == "NoFilter" for x in self.page["visualInteractions"] if x["source"] == "matching_files"))

    def test_bookmarks_do_not_reset_unrelated_filters(self):
        for b in self.bookmarks.values():
            self.assertTrue(set(b["options"]["targetVisualNames"]) <= self.visuals.keys())
            if b["name"].startswith("table_"):
                self.assertTrue(b["options"]["suppressData"])
            else:
                self.assertTrue(b["options"]["suppressDisplay"])

    def test_existing_test_binding_and_earlier_package_preserved(self):
        self.assertTrue(self.receipt["TESTBindingPreserved"])
        binding = (self.report / "definition.pbir").read_text()
        self.assertIn("31d00232-ac03-48fe-af39-f2e4bae82443", binding)
        self.assertNotIn("e7af2967-7725-4108-a170-9e490d4e35bb", binding)
        import hashlib
        self.assertEqual(hashlib.sha256(self.source.read_bytes()).hexdigest(), p.SOURCE_SHA256)

    def test_sample_has_only_fabricated_local_sources_and_the_same_native_layout(self):
        sample = Path(self.temp.name) / "sample"
        result = p.create_sample(self.project, sample)
        report = next(sample.glob("*.Report"))
        self.assertFalse(result["FabricConnection"])
        binding = json.loads((report / "definition.pbir").read_text())
        self.assertIn("byPath", binding["datasetReference"])
        self.assertNotIn("byConnection", binding["datasetReference"])
        database = json.loads(next(sample.glob("*.SemanticModel/model.bim")).read_text())
        for table in database["model"]["tables"]:
            for part in table["partitions"]:
                self.assertEqual(part["source"]["type"], "calculated")
        # All numeric definitions are the frozen R17.2 synthetic definitions.
        self.assertEqual(database["name"], "ForecastMasterNativeSyntheticR173")
        for name in self.visuals:
            if name == "edition":
                continue
            self.assertEqual((report / "definition/pages/native_demand/visuals" / name / "visual.json").read_bytes(),
                             (self.root / "pages/native_demand/visuals" / name / "visual.json").read_bytes())


if __name__ == "__main__":
    unittest.main(verbosity=2)
