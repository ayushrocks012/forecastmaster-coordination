"""Focused metadata and guarded-API tests; no company or DAX-engine execution."""
import ast
from contextlib import redirect_stdout
from copy import deepcopy
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


p = load("r176_project", HERE / "prepare_project.py")
model = p.MODEL
builder = load("r176_builder", HERE / "build_cell.py")
cell = load("r176_cell", HERE / "UPDATE EXISTING TEST TO R17.6.py")
mock = load("r176_mock", HERE.parent / "report-native-onelake-r17.1/measure-repair-r02/tests/check_repair.py")
mock.repair = cell


def database():
    return {"name": "Synthetic", "compatibilityLevel": 1604, "model": {
        "culture": "en-GB", "roles": [{"name": "KeepRole", "modelPermission": "read"}],
        "expressions": [{"name": "KeepSource", "expression": "SYNTHETIC_PRIVATE"}],
        "relationships": [{"name": "KeepRelationship", "fromTable": "A", "toTable": "B"}],
        "tables": [{"name": "fm_native_measures", "measures": list(model.baseline().values())},
                   model.original_columns()]
                  + [{"name": "fm_native_stub" + str(i)} for i in range(20)]
                  + [{"name": "fm_review_facts", "partitions": [{"mode": "directLake", "source": {
                      "type": "entity", "expressionSource": "KeepSource", "entityName": "KeepFact"}}]}]}}


class Client(mock.Client):
    def __init__(self):
        with patch.object(mock, "database", database):
            super().__init__()
        self.line_arrays, self.mapping_after_write = False, False

    def post(self, path, json=None):
        result = super().post(path, json=json)
        if path.endswith("/updateDefinition"):
            if self.line_arrays:
                for table in self.db["model"]["tables"]:
                    for measure in table.get("measures", []):
                        measure["expression"] = measure["expression"].split("\n")
                        if "formatStringDefinition" in measure:
                            fmt = measure["formatStringDefinition"]
                            fmt["expression"] = fmt["expression"].split("\n")
                    for partition in table.get("partitions", []):
                        source = partition.get("source", {})
                        if "expression" in source:
                            source["expression"] = source["expression"].split("\n")
            if self.mapping_after_write:
                self.connections[0]["id"] = "CHANGED"
        return result


class Tests(unittest.TestCase):
    def setUp(self):
        self.page, visuals = p.make_page()
        self.vs = {v["name"]: v for v in visuals}

    def run_cell(self, client=None, fs=None):
        client, fs = client or Client(), fs or mock.FileSystem()
        with redirect_stdout(io.StringIO()), patch.object(cell.time, "sleep", lambda _: None):
            result = cell.run(client, fs)
        return result, client, fs

    def test_geometry_and_native_visuals_no_overlapping_chrome(self):
        self.assertEqual(self.page["height"], 1504)
        visuals = list(self.vs.values())
        for i, visual in enumerate(visuals):
            self.assertIn(visual["visual"]["visualType"], {"slicer", "textbox", "cardVisual", "tableEx", "pivotTable", "lineChart"})
            a = visual["position"]
            self.assertLessEqual(a["x"] + a["width"], self.page["width"])
            self.assertLessEqual(a["y"] + a["height"], self.page["height"])
            for b in [v["position"] for v in visuals[i+1:]]:
                self.assertFalse(a["x"] < b["x"]+b["width"] and b["x"] < a["x"]+a["width"]
                                 and a["y"] < b["y"]+b["height"] and b["y"] < a["y"]+a["height"])
        self.assertEqual(self.vs["affiliate"]["position"]["y"] - sum(self.vs["source_status"]["position"][k] for k in ("y", "height")), 16)

    def test_distinct_month_slicers_labels_dates_and_invalid_order_guard(self):
        self.assertNotIn("review_months", self.vs)
        for side in ("start", "end"):
            visual = self.vs[side + "_month"]["visual"]
            field = visual["query"]["queryState"]["Values"]["projections"][0]
            self.assertEqual(field["queryRef"], "fm_native_" + side + "_month.MonthLabel")
            self.assertEqual(visual["objects"]["data"][0]["properties"]["mode"], p.lit("Dropdown"))
            self.assertEqual(visual["objects"]["selection"][0]["properties"]["singleSelect"], p.lit(True))
        for table in model.month_tables():
            self.assertIn("'fm_review_months'", table["partitions"][0]["source"]["expression"])
            self.assertEqual(table["columns"][1]["sortByColumn"], "Month")
            self.assertNotIn("fm_review_facts", json.dumps(table))
        self.assertIn("_start<=_end", model.replacements()["N Period Available"])
        chart = model.replacements()["N Chart Monthly"]
        self.assertIn("MIN('fm_native_start_month'[Month])<=MAX('fm_native_end_month'[Month])", chart)
        self.assertNotIn("fm_review_months", chart)

    def test_separate_section_measure_and_non_pruning_section_interaction(self):
        for name, prop in (("section", "Section"), ("metric", "MetricLabel")):
            fields = self.vs[name]["visual"]["query"]["queryState"]["Values"]["projections"]
            self.assertEqual([f["queryRef"] for f in fields], ["fm_native_metric." + prop])
        self.assertIn({"source": "metric", "target": "section", "type": "NoFilter"}, self.page["visualInteractions"])
        for name in ("N Headline Cell", "N Summary Cell", "N Measure Caption"):
            self.assertTrue(model.replacements()[name].startswith("IF(HASONEVALUE('fm_native_metric'[RowID])"))
        for name in ("N Headline Cell", "N Summary Cell"):
            self.assertIn(",IF([N Source OK]=1", model.replacements()[name])
            # The early availability guard is metadata only. No amount scan is
            # added to a visual filter or to this guard's source dependencies.
            self.assertNotIn("fm_review_facts", model.baseline()["N Source OK"]["expression"])

    def test_independent_single_graph_and_multiple_table_controls_beside_headings(self):
        for control, title, single in (("chart_trend", "headline_title", True), ("trend", "executive_title", False)):
            visual = self.vs[control]
            self.assertEqual(visual["visual"]["objects"]["selection"][0]["properties"]["singleSelect"], p.lit(single))
            self.assertGreater(visual["position"]["x"], self.vs[title]["position"]["x"])
            self.assertLessEqual(abs(visual["position"]["y"] - self.vs[title]["position"]["y"]), 20)
        for source, target in (("trend", "headline"), ("trend", "native_chart"), ("chart_trend", "executive_summary")):
            self.assertIn({"source": source, "target": target, "type": "NoFilter"}, self.page["visualInteractions"])
        chart = model.replacements()["N Chart Monthly"]
        self.assertIn("_kind=SELECTEDVALUE('fm_native_chart_trend'[Window],12)", chart)
        self.assertIn("_w IN VALUES('fm_native_trend'[Window])", model.replacements()["N Summary Cell"])

    def test_summary_query_shape_no_value_filter_or_repeated_formatting_benchmark(self):
        for name in ("headline", "executive_summary"):
            self.assertNotIn("filterConfig", self.vs[name])
        visual = self.vs["executive_summary"]["visual"]
        columns = visual["query"]["queryState"]["Columns"]["projections"]
        self.assertEqual([f["queryRef"] for f in columns], ["fm_native_periods.Label", "fm_native_columns.ColumnLabel"])
        self.assertEqual(len(visual["objects"]["values"]), 1)
        expansion = next(s for s in visual["expansionStates"] if s["roles"] == ["Columns"])
        self.assertEqual(len(expansion["root"]["children"]), 35)
        self.assertTrue(all(node["isToggled"] and "children" not in node for node in expansion["root"]["children"]))
        self.assertEqual(len(expansion["levels"]), 1)
        self.assertFalse(expansion["levels"][0]["isCollapsed"])
        rows = next(s for s in visual["expansionStates"] if s["roles"] == ["Rows"])
        self.assertTrue(rows["levels"][0]["isCollapsed"])

    def test_confirmed_native_chart_styles_preserved(self):
        _, old = p.OLD.make_page()
        original = next(v for v in old if v["name"] == "native_chart")["visual"]
        chart = self.vs["native_chart"]["visual"]
        for name in ("lineStyles", "dataPoint", "zoom", "categoryAxis", "legend"):
            self.assertEqual(chart["objects"][name], original["objects"][name])

    def test_all_arithmetic_formats_source_security_and_other_measures_preserved(self):
        before = database()
        after, changes = model.patch_database(before)
        self.assertEqual(len(changes), 9)
        self.assertEqual(sum(t["name"].startswith("fm_native_") for t in after["model"]["tables"]), 24)
        self.assertEqual(before, database())
        current = {m["name"]: m for m in after["model"]["tables"][0]["measures"]}
        for name, measure in model.baseline().items():
            if name not in model.replacements():
                self.assertEqual(current[name], measure)
            self.assertEqual(current[name].get("formatStringDefinition"), measure.get("formatStringDefinition"))
        for name in ("N Headline Cell", "N Measure Caption"):
            self.assertIn(model.baseline()[name]["expression"], current[name]["expression"])
        self.assertIn(model.baseline()["N Summary Cell"]["expression"].replace("[Comparison]", "[ColumnLabel]"), current["N Summary Cell"]["expression"])
        self.assertEqual(after["model"]["roles"], before["model"]["roles"])
        self.assertEqual(after["model"]["expressions"], before["model"]["expressions"])
        self.assertEqual(after["model"]["tables"][-3], before["model"]["tables"][-1])
        self.assertEqual(model.patch_database(after), (after, []))

    def test_static_comparison_helper_matches_onelake_installer(self):
        # Explicitly verify we do not derive the company's expected expression
        # from an accidentally different synthetic definition.
        om = load("r176_onelake", HERE.parent / "report-native-onelake-r17.1/onelake_model.py")
        rows = [{"ColumnKey": "plan", "Comparison": "Total Plan", "ValueLabel": " ", "Window": 0, "Sort": 0}]
        for window in (6, 12, 24):
            rows += [{"ColumnKey": str(window) + ":" + kind, "Comparison": str(window) + "M variance",
                      "ValueLabel": label, "Window": window, "Sort": window*10+i}
                     for i, (kind, label) in enumerate((("abs", "Absolute"), ("pct", "%")))]
        self.assertEqual(model.column_patch()[0], om.datatable(rows))

    def test_self_contained_cell_python310_and_private_backup_one_write(self):
        source = (HERE / "UPDATE EXISTING TEST TO R17.6.py").read_text()
        self.assertEqual(source, builder.build())
        ast.parse(source, feature_version=(3, 10))
        result, client, fs = self.run_cell()
        self.assertEqual(result["Stage"], "TEST_R176_UPDATED")
        self.assertTrue(result["TESTRefreshRequiredForNewHelpers"])
        self.assertEqual(len(mock.writes(client)), 1)
        self.assertEqual(mock.writes(client)[0][1]["options"], {"allowPurgeData": False})
        self.assertTrue(result["CloudConnectionPreserved"])
        self.assertFalse(result["SourceAmountsQueried"] or result["RefreshRequested"] or result["ReportPublished"])
        self.assertTrue(any(key.endswith("definition-before.json") for key in fs.files))
        self.assertFalse(any(cell.ORIGINAL_MODEL in path for _, path, _ in client.calls))

    def test_identical_dax_line_arrays_accept_no_other_differences(self):
        client = Client(); client.line_arrays = True
        result, _, _ = self.run_cell(client)
        self.assertEqual(result["Stage"], "TEST_R176_UPDATED")
        self.assertEqual(result["DifferenceSummary"]["Unexplained"], 0)
        self.assertEqual(result["DifferenceSummary"]["Counts"]["IDENTICAL_CALCULATED_HELPER_LINE_REPRESENTATION"], 3)

    def test_helper_line_normalization_never_ignores_source_or_changed_dax(self):
        db, _ = cell.patch_database(database())
        a = cell.unpack(mock.definition(db))[0]
        for mode in ("changed_helper_text", "source_text_representation", "helper_property"):
            b = deepcopy(a)
            payload = b["parts"][0]["payload"]
            tables = {t["name"]: t for t in payload["model"]["tables"]}
            if mode == "changed_helper_text":
                tables["fm_native_start_month"]["partitions"][0]["source"]["expression"] = ["WRONG DAX"]
            elif mode == "source_text_representation":
                payload["model"]["expressions"][0]["expression"] = ["SYNTHETIC_PRIVATE"]
            else:
                tables["fm_native_start_month"]["columns"][0]["dataType"] = "string"
            self.assertGreater(cell.compare_with_calculated(a, b)["Unexplained"], 0)

    def test_projection_aliases_and_saved_file_date_formats_remain_valid(self):
        for visual in self.vs.values():
            aliases = [f["nativeQueryRef"] for role in visual["visual"].get("query", {}).get("queryState", {}).values()
                       for f in role.get("projections", [])]
            self.assertEqual(len(aliases), len(set(aliases)))
        dates = [f["format"] for f in self.vs["matching_files"]["visual"]["query"]["queryState"]["Values"]["projections"] if "format" in f]
        self.assertEqual(dates, ["MMM yyyy", "MMM yyyy"])

    def test_prewrite_guard_refusals_and_large_unicode_backup(self):
        modes = ("identity", "unknown_expression", "old_r174", "unknown_format", "wrong_count",
                 "unknown_columns", "unknown_month", "missing_cloud", "concurrent", "connection_change",
                 "truncated", "copy_false", "put_false")
        for mode in modes:
            with self.subTest(mode=mode):
                client, fs = Client(), mock.FileSystem()
                if mode == "identity": client.identity["id"] = cell.ORIGINAL_MODEL
                elif mode == "unknown_expression": client.db["model"]["tables"][0]["measures"][0]["expression"] = "UNKNOWN"
                elif mode == "old_r174":
                    for measure in client.db["model"]["tables"][0]["measures"]:
                        if measure["name"] == "N Chart Monthly": measure["expression"] = model.OLD.baseline()[measure["name"]]["expression"]
                elif mode == "unknown_format":
                    measure = next(m for m in client.db["model"]["tables"][0]["measures"] if "formatStringDefinition" in m)
                    measure["formatStringDefinition"]["expression"] = '"OLD"'
                elif mode == "wrong_count": client.db["model"]["tables"].pop(3)
                elif mode == "unknown_columns": client.db["model"]["tables"][1]["partitions"][0]["source"]["expression"] = "UNKNOWN"
                elif mode == "unknown_month":
                    client.db, _ = cell.patch_database(client.db)
                    client.db["model"]["tables"][-1]["description"] = "UNKNOWN"
                elif mode == "missing_cloud": client.connections = []
                elif mode in {"concurrent", "connection_change"}: setattr(client, mode, True)
                else:
                    setattr(fs, mode, True)
                    if mode == "truncated": client.db["model"]["expressions"][0]["expression"] = "SYNTHETIC é"*20000
                with self.assertRaises((ValueError, RuntimeError)):
                    self.run_cell(client, fs)
                self.assertFalse(mock.writes(client))

    def test_no_retry_on_rejection_unexplained_readback_or_mapping_change(self):
        for mode in ("bad_readback", "mapping_after_write"):
            client = Client(); setattr(client, mode, True)
            result, client, fs = self.run_cell(client)
            self.assertEqual(result["Stage"], "TEST_R176_READBACK_NEEDS_REVIEW")
            self.assertEqual(len(mock.writes(client)), 1)
            self.assertFalse(any(key.endswith("success.json") for key in fs.files))
        client = Client(); client.reject = True
        with self.assertRaises(RuntimeError): self.run_cell(client)
        self.assertEqual(len(mock.writes(client)), 1)
        client = Client(); client.db, _ = cell.patch_database(client.db)
        result, client, _ = self.run_cell(client)
        self.assertEqual(result["Stage"], "TEST_R176_ALREADY_INSTALLED")
        self.assertFalse(mock.writes(client))

    def test_project_binding_sample_preservation_and_two_text_extensions_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            test, sample = Path(tmp) / "TEST", Path(tmp) / "SAMPLE"
            p.create(HERE.parent / "report-native-only-r17.5/candidate/ForecastMaster Native Only R17.5 TEST.zip", test)
            p.sample_from_frozen(test, sample)
            self.assertFalse(list(test.rglob("model.bim")))
            observed = json.loads(next(sample.glob("*.SemanticModel/model.bim")).read_text())
            with ZipFile(HERE.parent / "report-native-only-r17.5/candidate/ForecastMaster Native Only R17.5 SAMPLE.zip") as archive:
                original = json.loads(archive.read(next(n for n in archive.namelist() if n.endswith("/model.bim"))))
            self.assertEqual(observed, model.patch_database(original)[0])
            extension = json.loads(next(test.rglob("reportExtensions.json")).read_text())
            measures = extension["entities"][0]["measures"]
            self.assertEqual({m["name"] for m in measures}, {"N R175 Line Style", "N R175 Series Color"})
            self.assertTrue(all(m["dataType"] == "Text" for m in measures))
            self.assertFalse(list(test.rglob("*.pbiviz")) + list(test.rglob("*.js")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
