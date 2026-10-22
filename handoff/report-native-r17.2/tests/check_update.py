"""No network. Exercise the standalone TEST updater with synthetic metadata/APIs."""
import base64
from copy import deepcopy
import importlib.util
import io
import json
from pathlib import Path
import sys
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE))
import model
import build_cell

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

cell=load("update",HERE/"UPDATE EXISTING TEST TO R17.2.py")
mock=load("r02_test",HERE.parent/"report-native-onelake-r17.1/measure-repair-r02/tests/check_repair.py")
mock.repair=cell


def database():
    return {"name":"Synthetic","compatibilityLevel":1604,"model":{
        "culture":"en-GB","roles":[{"name":"KeepRole","modelPermission":"read"}],
        "expressions":[{"name":"KeepSource","kind":"m","expression":"PRIVATE"}],
        "tables":[{"name":"fm_native_measures","measures":list(model.original_measures().values())},
                  {"name":"fm_native_lines"}]+[{"name":"fm_native_stub"+str(i)} for i in range(18)]
        +[{"name":"fm_review_facts","partitions":[{"mode":"directLake","source":{"type":"entity","entityName":"fm_review_facts"}}]},
          {"name":"fm_review_measures","measures":[{"name":"KeepFMUI","expression":"42","displayFolder":"Keep"}]}]}}


class Client(mock.Client):
    def __init__(self):
        # The reusable mock constructor gets a module-level synthetic factory.
        with patch.object(mock,"database",database):super().__init__()


class Tests(unittest.TestCase):
    def run_cell(self,c=None,f=None):
        c=c or Client();f=f or mock.FileSystem()
        with redirect_stdout(io.StringIO()),patch.object(cell.time,"sleep",lambda _:None):result=cell.run(c,f)
        return result,c,f

    def test_cell_reproducible(self):
        self.assertEqual((HERE/"UPDATE EXISTING TEST TO R17.2.py").read_text(),build_cell.build())

    def test_exact_pure_preservation_and_idempotence(self):
        before=database();saved=deepcopy(before)
        after,changes=cell.patch_database(before)
        self.assertEqual(before,saved)
        original={t["name"]:t for t in before["model"]["tables"]}
        for table in after["model"]["tables"]:
            if table["name"] in original and table["name"]!="fm_native_measures":self.assertEqual(table,original[table["name"]])
        self.assertEqual(after["model"]["roles"],before["model"]["roles"])
        self.assertEqual(after["model"]["expressions"],before["model"]["expressions"])
        self.assertTrue(changes);self.assertEqual(cell.patch_database(after),(after,[]))

    def test_unknown_expression_refuses(self):
        db=database();db["model"]["tables"][0]["measures"][0]["expression"]="UNKNOWN"
        with self.assertRaises(ValueError):cell.patch_database(db)

    def test_success_one_update_only_test_mapping_preserved(self):
        result,c,f=self.run_cell()
        self.assertEqual(result["Stage"],"TEST_R172_UPDATED")
        self.assertEqual(len(mock.writes(c)),1)
        path,body=mock.writes(c)[0]
        self.assertEqual(path,cell.BASE+"/updateDefinition")
        self.assertEqual(body["options"],{"allowPurgeData":False})
        self.assertEqual(len([p for p in f.files if "definition-" in p]),2)
        self.assertTrue(result["CloudConnectionPreserved"])
        self.assertFalse(result["OriginalModelWriteRequested"])
        self.assertFalse(result["RefreshRequested"])
        self.assertFalse(any(cell.ORIGINAL_MODEL in p for _,p,_ in c.calls))
        c.calls=[];result,_,_=self.run_cell(c)
        self.assertEqual(result["Stage"],"TEST_R172_ALREADY_INSTALLED");self.assertFalse(mock.writes(c))

    def test_asynchronous_update(self):
        c=Client();c.asynchronous=True
        result,c,_=self.run_cell(c)
        self.assertEqual(result["Stage"],"TEST_R172_UPDATED");self.assertEqual(len(mock.writes(c)),1)

    def test_all_prewrite_guards(self):
        for mode in ("wrong_identity","bad_source_count","unknown_measure","missing_cloud","concurrent","connection_change","connection_failure","bad_backup","bad_copy","bad_put"):
            with self.subTest(mode=mode):
                c=Client();f=mock.FileSystem()
                if mode=="wrong_identity":c.identity["id"]=cell.ORIGINAL_MODEL
                elif mode=="bad_source_count":c.db["model"]["tables"].pop(1)
                elif mode=="unknown_measure":c.db["model"]["tables"][0]["measures"][0]["expression"]="changed"
                elif mode=="missing_cloud":c.connections=[]
                elif mode=="bad_backup":f.same_length_corruption=True
                elif mode=="bad_copy":f.copy_false=True
                elif mode=="bad_put":f.put_false=True
                else:setattr(c,mode,True)
                with self.assertRaises((ValueError,RuntimeError)):self.run_cell(c,f)
                self.assertFalse(mock.writes(c))

    def test_failed_update_not_retried(self):
        c=Client();c.reject=True
        with self.assertRaises(RuntimeError):self.run_cell(c)
        self.assertEqual(len(mock.writes(c)),1)

    def test_failed_readback_keeps_backup(self):
        c=Client();c.bad_readback=True;f=mock.FileSystem()
        with self.assertRaises(RuntimeError):self.run_cell(c,f)
        self.assertEqual(len(mock.writes(c)),1);self.assertTrue(f.files)


if __name__=="__main__":unittest.main(verbosity=2)
