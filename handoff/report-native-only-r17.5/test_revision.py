"""Focused native report contracts and mocked TEST update guards; no company API."""
import base64
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
    spec = importlib.util.spec_from_file_location(name,path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


p = load("r175_report",HERE / "prepare_project.py")
model = load("r175_model_test",HERE / "model.py")
builder = load("r175_builder",HERE / "build_cell.py")
cell = load("r175_cell",HERE / "UPDATE EXISTING TEST TO R17.5.py")
mock = load("r175_mock",HERE.parent / "report-native-onelake-r17.1/measure-repair-r02/tests/check_repair.py")
mock.repair = cell


def database():
    return {"name":"Synthetic", "compatibilityLevel":1604,"model":{
        "culture":"en-GB","roles":[{"name":"KeepRole","modelPermission":"read"}],
        "expressions":[{"name":"KeepSource","expression":"SYNTHETIC_PRIVATE"}],
        "relationships":[{"name":"KeepRelationship","fromTable":"A","toTable":"B"}],
        "tables":[{"name":"fm_native_measures","measures":list(model.baseline().values())}]
                 +[{"name":"fm_native_stub"+str(i)} for i in range(21)]
                 +[{"name":"fm_review_facts","partitions":[{"mode":"directLake","source":{
                     "type":"entity","expressionSource":"KeepSource","entityName":"KeepFact"}}]}]}}


class Client(mock.Client):
    def __init__(self):
        with patch.object(mock,"database",database):
            super().__init__()
        self.line_arrays, self.mapping_after_write = False, False

    def post(self,path,json=None):
        result = super().post(path,json=json)
        if path.endswith("/updateDefinition"):
            if self.line_arrays:
                for table in self.db["model"]["tables"]:
                    for measure in table.get("measures",[]):
                        measure["expression"] = measure["expression"].split("\n")
                        if "formatStringDefinition" in measure:
                            fmt = measure["formatStringDefinition"]
                            fmt["expression"] = fmt["expression"].split("\n")
            if self.mapping_after_write:
                self.connections[0]["id"] = "CHANGED"
        return result


class Tests(unittest.TestCase):
    def setUp(self):
        self.page, vs = p.make_page()
        self.vs = {v["name"]:v for v in vs}

    def run_cell(self,c=None,fs=None):
        c,fs = c or Client(),fs or mock.FileSystem()
        with redirect_stdout(io.StringIO()), patch.object(cell.time,"sleep",lambda _:None):
            result = cell.run(c,fs)
        return result,c,fs

    def test_compact_no_overlap_and_native_only(self):
        self.assertEqual(self.page["height"],1286)
        self.assertLess(self.page["height"],1860*0.7)
        vs = list(self.vs.values())
        for i,v in enumerate(vs):
            self.assertIn(v["visual"]["visualType"],p.OLD.BUILTINS)
            a = v["position"]
            self.assertLessEqual(a["x"]+a["width"],self.page["width"])
            self.assertLessEqual(a["y"]+a["height"],self.page["height"])
            for b in [other["position"] for other in vs[i+1:]]:
                self.assertFalse(a["x"]<b["x"]+b["width"] and b["x"]<a["x"]+a["width"]
                                 and a["y"]<b["y"]+b["height"] and b["y"]<a["y"]+a["height"])

    def test_month_dropdown_has_month_format_date_literals_and_window_contract(self):
        visual = self.vs["review_months"]["visual"]
        self.assertEqual(visual["objects"]["data"][0]["properties"]["mode"],p.lit("Dropdown"))
        self.assertEqual(visual["query"]["queryState"]["Values"]["projections"][0]["format"],"MMM yyyy")
        values = visual["objects"]["general"][0]["properties"]["filter"]["filter"]["Where"][0]["Condition"]["In"]["Values"]
        self.assertEqual(values,[[{"Literal":{"Value":"datetime'2025-01-01T00:00:00'"}}],
                                 [{"Literal":{"Value":"datetime'2027-12-01T00:00:00'"}}]])
        self.assertIn("first and last",visual["objects"]["header"][0]["properties"]["text"]["expr"]["Literal"]["Value"])

    def test_section_measure_one_native_hierarchy_retains_all_six_model_options(self):
        self.assertNotIn("section",self.vs)
        visual = self.vs["metric"]["visual"]
        fields = visual["query"]["queryState"]["Values"]["projections"]
        self.assertEqual([f["queryRef"] for f in fields],["fm_native_metric.Section","fm_native_metric.MetricLabel"])
        self.assertTrue(visual["objects"]["selection"][0]["properties"]["singleSelect"])
        self.assertNotIn("syncGroup",visual)

    def test_variance_columns_are_active_and_explicitly_expanded(self):
        visual = self.vs["executive_summary"]["visual"]
        fields = visual["query"]["queryState"]["Columns"]["projections"]
        self.assertTrue(all(f["active"] for f in fields))
        self.assertEqual([f["queryRef"] for f in fields],
                         ["fm_native_periods.Label","fm_native_columns.Comparison","fm_native_columns.ValueLabel"])
        columns = next(s for s in visual["expansionStates"] if s["roles"]==["Columns"])
        self.assertEqual(len(columns["levels"]),2)
        self.assertTrue(all(not level["isCollapsed"] and level["isPinned"] for level in columns["levels"]))
        self.assertTrue(all(node["isToggled"] and len(node["children"])==4 for node in columns["root"]["children"]))
        self.assertEqual(visual["query"]["queryState"]["Values"]["projections"][0]["queryRef"],"fm_native_measures.N Summary Cell")

    def test_chart_style_bindings_and_no_markers_or_sliders(self):
        visual = self.vs["native_chart"]["visual"]
        styles = visual["objects"]["lineStyles"]
        self.assertEqual(styles[0]["properties"]["showMarker"],p.lit(False))
        self.assertEqual(styles[1]["selector"]["data"],[{"roles":["Series"]}])
        self.assertEqual(styles[1]["properties"]["lineStyle"],p.style_measure("N R175 Line Style"))
        zoom = visual["objects"]["zoom"][0]["properties"]
        self.assertEqual((zoom["show"],zoom["showOnValueAxis"]),(p.lit(False),p.lit(False)))
        self.assertEqual(visual["query"]["queryState"]["Y"]["projections"][0]["queryRef"],"fm_native_measures.N Chart Amount")

    def test_extensions_only_formatting_text_and_metadata_selection_guards(self):
        measures = p.extensions()["entities"][0]["measures"]
        self.assertEqual(len(measures),5)
        self.assertEqual(sum(m["dataType"]=="Text" for m in measures),4)
        self.assertEqual(next(m for m in measures if m["dataType"]=="Integer")["expression"],
                         "IF(HASONEVALUE('fm_native_metric'[RowID]),1,0)")
        for name in ("headline","native_chart","executive_summary"):
            guard=self.vs[name]["filterConfig"]["filters"][-1]
            self.assertEqual(guard["filter"]["From"][0]["Schema"],"extension")
        self.assertIn('"dashed"',p.FORMATTING["N R175 Line Style"])
        self.assertIn('"dotted"',p.FORMATTING["N R175 Line Style"])
        self.assertNotIn("LineKind",p.FORMATTING["N R175 Series Color"])
        self.assertIn("fm_native_columns'[Window]",p.FORMATTING["N R175 Summary Color"])

    def test_multiselect_native_drill_and_source_table_retained(self):
        self.assertIn("matching_files",self.vs)
        for name in ("drivers","tiers","periods","trend"):
            self.assertEqual(self.vs[name]["visual"]["objects"]["selection"][0]["properties"]["singleSelect"],p.lit(False))
        rows = next(s for s in self.vs["executive_summary"]["visual"]["expansionStates"] if s["roles"]==["Rows"])
        self.assertTrue(rows["levels"][0]["isCollapsed"])
        self.assertTrue(all(i["type"]=="NoFilter" for i in self.page["visualInteractions"]))

    def test_model_only_two_expressions_and_all_formats_source_security_unchanged(self):
        before = database()
        after,changed = model.patch_database(before)
        self.assertEqual(set(changed),{"N Chart Monthly","N Line Visible"})
        self.assertEqual(before,database())
        restored = deepcopy(after)
        by = {m["name"]:m for m in before["model"]["tables"][0]["measures"]}
        for m in restored["model"]["tables"][0]["measures"]:
            if m["name"] in changed: m["expression"]=by[m["name"]]["expression"]
        self.assertEqual(restored,before)
        self.assertEqual(model.patch_database(after),(after,[]))

    def test_chart_window_boundary_and_shared_view_membership_contract(self):
        edits=model.replacements()
        chart=edits["N Chart Monthly"]
        self.assertIn('_kind=1&&(_month>_cut||_type="demand"&&_month=_cut)',chart)
        for expression in edits.values():
            self.assertIn("_kind=SELECTEDVALUE('fm_native_chart_trend'[Window],12)",expression)
            self.assertNotIn("_kind IN VALUES('fm_native_trend'[Window])",expression)
            self.assertIn("CONTAINS(VALUES('fm_native_lines'[ViewType])",expression)
        # All value aggregation/fit lines are byte-preserved; only admission,
        # per-visual trend choice and the last-actual connecting point differ.
        old=model.baseline()["N Chart Monthly"]["expression"]
        for line in old.splitlines():
            if line.startswith(("VAR _base=","VAR _cut="," CALCULATE([N Trend Monthly]")):
                self.assertIn(line,chart)

    def test_cell_reproducible_and_one_write_no_refresh_publication(self):
        source=(HERE/"UPDATE EXISTING TEST TO R17.5.py").read_text()
        self.assertEqual(source,builder.build())
        compile(source,"r175_cell","exec")
        result,c,fs=self.run_cell()
        self.assertEqual(result["Stage"],"TEST_R175_UPDATED")
        self.assertEqual(len(mock.writes(c)),1)
        self.assertEqual(mock.writes(c)[0][1]["options"],{"allowPurgeData":False})
        self.assertTrue(result["CloudConnectionPreserved"])
        self.assertFalse(result["SourceAmountsQueried"] or result["RefreshRequested"] or result["ReportPublished"])
        self.assertTrue(any("definition-before.json" in key for key in fs.files))
        self.assertFalse(any(cell.ORIGINAL_MODEL in path for _,path,_ in c.calls))

    def test_receiving_dax_line_array_representation_is_accepted_without_ignoring_changes(self):
        c=Client();c.line_arrays=True
        result,c,_=self.run_cell(c)
        self.assertEqual(result["Stage"],"TEST_R175_UPDATED")
        self.assertEqual(result["DifferenceSummary"]["Unexplained"],0)
        self.assertEqual(result["DifferenceSummary"]["Counts"]["IDENTICAL_DAX_LINE_REPRESENTATION"],69)

    def test_prewrite_guards_and_backup_failures_stop_before_update(self):
        for mode in ("identity","unknown_expression","unknown_format","wrong_count","missing_cloud", "concurrent", "connection_change","truncated","copy_false","put_false"):
            with self.subTest(mode=mode):
                c,fs=Client(),mock.FileSystem()
                if mode=="identity":c.identity["id"]=cell.ORIGINAL_MODEL
                elif mode=="unknown_expression":c.db["model"]["tables"][0]["measures"][0]["expression"]="UNKNOWN"
                elif mode=="unknown_format":
                    m=next(m for m in c.db["model"]["tables"][0]["measures"] if "formatStringDefinition" in m)
                    m["formatStringDefinition"]["expression"]='"OLD FORMAT"'
                elif mode=="wrong_count":c.db["model"]["tables"].pop(1)
                elif mode=="missing_cloud":c.connections=[]
                elif mode in {"concurrent","connection_change"}:setattr(c,mode,True)
                else:
                    setattr(fs,mode,True)
                    if mode=="truncated":c.db["model"]["expressions"][0]["expression"]="SYNTHETIC é"*20000
                with self.assertRaises((ValueError,RuntimeError)):
                    self.run_cell(c,fs)
                self.assertFalse(mock.writes(c))

    def test_postwrite_unexplained_or_mapping_change_needs_review_no_retry(self):
        for kind in ("bad_readback","mapping_after_write"):
            c=Client();setattr(c,kind,True)
            result,c,fs=self.run_cell(c)
            self.assertEqual(result["Stage"],"TEST_R175_READBACK_NEEDS_REVIEW")
            self.assertEqual(len(mock.writes(c)),1)
            self.assertFalse(any(key.endswith("success.json") for key in fs.files))

    def test_rejected_request_not_retried_and_installed_run_no_write(self):
        c=Client();c.reject=True
        with self.assertRaises(RuntimeError):self.run_cell(c)
        self.assertEqual(len(mock.writes(c)),1)
        c=Client();c.db,_=cell.patch_database(c.db)
        result,c,_=self.run_cell(c)
        self.assertEqual(result["Stage"],"TEST_R175_ALREADY_INSTALLED")
        self.assertFalse(mock.writes(c))

    def test_project_binding_and_fabricated_sample_numeric_model_preservation(self):
        with tempfile.TemporaryDirectory() as tmp:
            test,sample=Path(tmp)/"TEST",Path(tmp)/"SAMPLE"
            p.create(HERE.parent/"report-native-only-r17.4/candidate/ForecastMaster Native Only R17.4 TEST.zip",test)
            p.sample_from_frozen(test,sample)
            self.assertFalse(list(test.rglob("model.bim")))
            with ZipFile(HERE.parent/"report-native-only-r17.4/candidate/ForecastMaster Native Only R17.4 SAMPLE.zip") as z:
                original=json.loads(z.read(next(n for n in z.namelist() if n.endswith('/model.bim'))))
            observed=json.loads(next(sample.glob("*.SemanticModel/model.bim")).read_text())
            self.assertEqual(observed,model.patch_database(original)[0])
            self.assertFalse(list(test.rglob("*.pbiviz"))+list(test.rglob("*.js")))


if __name__=="__main__":
    unittest.main(verbosity=2)
