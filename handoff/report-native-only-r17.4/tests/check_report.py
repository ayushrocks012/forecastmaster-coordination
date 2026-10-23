"""Regressions for the native controls, drill hierarchy and frozen packages."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import prepare_project as p


class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.project = Path(cls.tmp.name) / "test"
        cls.receipt = p.create(HERE.parent / "report-native-only-r17.3/candidate/ForecastMaster Native Only R17.3 TEST.zip", cls.project)
        cls.report = next(cls.project.glob("*.Report"))
        cls.root = cls.report / "definition"
        cls.page = json.loads((cls.root / "pages/native_demand/page.json").read_text())
        cls.vs = {f.parent.name: json.loads(f.read_text()) for f in (cls.root / "pages/native_demand/visuals").glob("*/visual.json")}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_no_customs_buttons_or_bookmark_views(self):
        self.assertTrue(all(v["visual"]["visualType"] in p.BUILTINS for v in self.vs.values()))
        self.assertFalse(list(self.project.rglob("*.pbiviz*")))
        self.assertFalse(list(self.project.rglob("*.js")))
        self.assertFalse(any(v["visual"]["visualType"] == "actionButton" for v in self.vs.values()))
        self.assertEqual(list((self.root / "bookmarks").glob("*.bookmark.json")), [])
        self.assertEqual(len([v for v in self.vs.values() if v["visual"]["visualType"] == "pivotTable"]), 2)

    def test_native_multi_selection_remains_without_extra_buttons(self):
        for name in ("drivers", "tiers", "periods"):
            self.assertEqual(self.vs[name]["visual"]["objects"]["selection"][0]["properties"]["selectAllCheckboxEnabled"], p.lit(True))
        self.assertNotIn("month_readout", self.vs)

    def test_no_chart_axis_zoom_sliders(self):
        props = self.vs["native_chart"]["visual"]["objects"]["zoom"][0]["properties"]
        self.assertEqual(props["show"], p.lit(False))
        self.assertEqual(props["showOnValueAxis"], p.lit(False))
        self.assertEqual(self.vs["native_chart"]["visual"]["objects"]["categoryAxis"][0]["properties"]["axisType"], p.lit("Scalar"))

    def test_one_native_drill_hierarchy_keeps_sector_identity(self):
        v = self.vs["executive_summary"]["visual"]
        fields = [q["queryRef"] for q in v["query"]["queryState"]["Rows"]["projections"]]
        self.assertEqual(fields, ["fm_native_scope.GrowthDriver", "fm_native_scope.SectorLabel"])
        self.assertEqual(v["objects"]["rowHeaders"][0]["properties"]["showExpandCollapseButtons"], p.lit(True))
        header = v["visualContainerObjects"]["visualHeader"][0]["properties"]
        for name in ("showDrillUpButton", "showDrillToggleButton", "showDrillDownLevelButton", "showDrillDownExpandButton"):
            self.assertEqual(header[name], p.lit(True))
        self.assertFalse(v["drillFilterOtherVisuals"])
        rows = next(x for x in v["expansionStates"] if x["roles"] == ["Rows"])
        columns = next(x for x in v["expansionStates"] if x["roles"] == ["Columns"])
        self.assertTrue(rows["levels"][0]["isCollapsed"])
        self.assertEqual(len(columns["levels"]), 3)
        self.assertTrue(all(not x["isCollapsed"] and x["isPinned"] for x in columns["levels"]))

    def test_drill_does_not_change_the_chart_scope(self):
        self.assertTrue(all(x["type"] == "NoFilter" for x in self.page["visualInteractions"]))
        self.assertIn("executive_summary", {x["source"] for x in self.page["visualInteractions"]})

    def test_visual_dates_use_months_not_minutes(self):
        date_fields = [x for x in self.vs["matching_files"]["visual"]["query"]["queryState"]["Values"]["projections"] if "format" in x]
        self.assertEqual(len(date_fields), 2)
        self.assertTrue(all(x["format"] == "MMM yyyy" for x in date_fields))

    def test_calendar_ui_bounds_match_the_actual_predicate(self):
        v = self.vs["review_months"]["visual"]["objects"]
        data = v["data"][0]["properties"]
        condition = v["general"][0]["properties"]["filter"]["filter"]["Where"][0]["Condition"]["Between"]
        self.assertEqual(data["startDate"]["expr"], condition["LowerBound"])
        self.assertEqual(data["endDate"]["expr"], condition["UpperBound"])

    def test_headers_and_values_use_the_available_width(self):
        for name in ("headline", "executive_summary", "matching_files"):
            self.assertEqual(self.vs[name]["visual"]["objects"]["columnHeaders"][0]["properties"]["columnAdjustment"], p.lit("growToFit"))
        self.assertEqual(self.vs["source_status"]["visual"]["visualType"], "cardVisual")
        self.assertIn("Data", self.vs["source_status"]["visual"]["query"]["queryState"])

    def test_native_geometry_and_names(self):
        values = list(self.vs.values())
        for i, a in enumerate(values):
            r = a["position"]
            self.assertFalse(a.get("isHidden"))
            self.assertLessEqual(r["x"] + r["width"], self.page["width"])
            self.assertLessEqual(r["y"] + r["height"], self.page["height"])
            refs = [q["nativeQueryRef"] for role in a["visual"].get("query", {}).get("queryState", {}).values() for q in role.get("projections", [])]
            self.assertEqual(len(refs), len(set(refs)))
            for b in values[i+1:]:
                s = b["position"]
                self.assertFalse(r["x"] < s["x"]+s["width"] and s["x"] < r["x"]+r["width"] and r["y"] < s["y"]+s["height"] and s["y"] < r["y"]+r["height"], a["name"]+" / "+b["name"])
        self.assertLess(self.page["height"], 2024)

    def test_sample_is_local_fabricated_and_receives_the_same_repair(self):
        sample = Path(self.tmp.name) / "sample"
        result = p.create_sample(self.project, sample)
        self.assertFalse(result["FabricConnection"])
        report = next(sample.glob("*.Report"))
        binding = json.loads((report / "definition.pbir").read_text())
        self.assertIn("byPath", binding["datasetReference"])
        db = json.loads(next(sample.glob("*.SemanticModel/model.bim")).read_text())
        self.assertTrue(all(part["source"]["type"] == "calculated" for t in db["model"]["tables"] for part in t["partitions"]))
        self.assertEqual(p.MODEL.patch_database(db), (db, []))
        self.assertTrue(self.receipt["TESTBindingPreserved"])
        self.assertFalse(list(self.project.rglob("*.bim")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
