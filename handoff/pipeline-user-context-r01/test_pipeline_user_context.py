"""Exercise the copy/paste cell against synthetic Fabric and OneLake responses."""

import base64
import copy
import json
import runpy
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

CELL = Path(__file__).with_name("SET HOURLY USER CONTEXT.txt")
CODE = CELL.read_text()
M = SimpleNamespace(**runpy.run_path(str(CELL)))
PIPELINE = "11111111-2222-4333-8444-555555555555"
CONNECTION = "22222222-3333-4444-8555-666666666666"
OPERATION = "33333333-4444-4555-8666-777777777777"


def encode(value):
    return base64.b64encode(json.dumps(value).encode()).decode()


def definition():
    return {"parts": [
        {"path": ".platform", "payloadType": "InlineBase64", "payload": encode({"metadata": "original"})},
        {"path": "pipeline-content.json", "payloadType": "InlineBase64", "payload": encode({
            "properties": {"description": "Retained pipeline", "activities": [
                {"name": M.METADATA_NAME, "type": "TridentFunction", "externalReferences": {"connection": CONNECTION},
                 "typeProperties": {"function": "checkDemandChangesR05", "other": "retained"}},
                {"name": M.GATE_NAME, "type": "IfCondition", "dependsOn": [
                    {"activity": M.METADATA_NAME, "dependencyConditions": ["Succeeded"]}],
                 "typeProperties": {"expression": {"value": "@bool(activity('Check_Demand_Metadata').output.output)", "type": "Expression"},
                    "ifFalseActivities": [], "ifTrueActivities": [
                        {"name": M.ACTIVITY_NAME, "type": "TridentNotebook", "dependsOn": [],
                         "policy": {"timeout": "0.01:00:00", "retry": 0, "secureInput": False, "secureOutput": False},
                         "externalReferences": {"connection": CONNECTION},
                         "typeProperties": {"workspaceId": M.WORKSPACE, "notebookId": M.NOTEBOOK,
                            "parameters": {
                                "FM_RUN_MODE": {"type": "string", "value": "HOURLY"},
                                "FM_METADATA_JSON": {"type": "string", "value": {"type": "Expression", "value": M.METADATA_EXPRESSION}},
                            }}}
                    ]}}
            ]}})},
    ]}


def target(value):
    return value["properties"]["activities"][1]["typeProperties"]["ifTrueActivities"][0]


class Response:
    def __init__(self, status=200, body=None, headers=None):
        self.status_code, self.body, self.headers = status, body, headers or {}
        self.text = json.dumps(body)

    def json(self):
        return copy.deepcopy(self.body)


class HTTP:
    def __init__(self):
        self.definition = definition()
        self.calls, self.backups = [], {}
        self.pages = [[{"id": PIPELINE, "type": "DataPipeline", "displayName": M.PIPELINE_NAME}]]
        self.backup_status = 201
        self.corrupt_backup = self.concurrent_edit = self.corrupt_readback = False
        self.update_status = 200
        self.read_count = 0
        self.worker_name = "ForecastMaster_Refresh"

    def replace_pipeline(self, value):
        self.definition["parts"][1]["payload"] = encode(value)

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, copy.deepcopy(kwargs)))
        if "onelake.blob.fabric.microsoft.com" in url:
            if method == "PUT":
                assert kwargs["headers"]["If-None-Match"] == "*"
                assert url not in self.backups
                self.backups[url] = json.loads(kwargs["data"])
                return Response(self.backup_status)
            if method == "GET":
                return Response(200, {} if self.corrupt_backup else self.backups[url])
        if url.endswith("/items/" + M.NOTEBOOK):
            return Response(200, {"id": M.NOTEBOOK, "displayName": self.worker_name})
        if url.endswith("/items"):
            page = int(kwargs["params"].get("continuationToken", "0"))
            body = {"value": self.pages[page]}
            if page + 1 < len(self.pages):
                body["continuationToken"] = str(page + 1)
            return Response(200, body)
        if url.endswith("/getDefinition"):
            self.read_count += 1
            if self.concurrent_edit and self.read_count == 2:
                value = M.content(self.definition)
                value["properties"]["description"] = "Another editor's change"
                self.replace_pipeline(value)
            return Response(200, {"definition": self.definition})
        if url.endswith("/updateDefinition"):
            assert self.backups, "Must back up before updating"
            if self.update_status == 200:
                self.definition = copy.deepcopy(kwargs["json"]["definition"])
                if self.corrupt_readback:
                    value = M.content(self.definition)
                    value["properties"]["activities"][0]["typeProperties"]["other"] = "changed unexpectedly"
                    self.replace_pipeline(value)
            return Response(self.update_status, {"message": "synthetic update status"})
        raise AssertionError((method, url))

    @property
    def updates(self):
        return [call for call in self.calls if call[1].endswith("/updateDefinition")]


def token(audience):
    assert audience in {"pbi", "storage"}
    return "synthetic-token"


def run(http):
    return M.update_hourly(http, token, sleep=lambda _: None)


def test_removes_only_target_reference_with_verified_backup_and_existing_ids(capsys):
    http = HTTP()
    original = copy.deepcopy(http.definition)
    assert run(http) == "UPDATED"
    wanted = M.content(original)
    target(wanted).pop("externalReferences")
    assert M.content(http.definition) == wanted
    assert http.definition["parts"][0] == original["parts"][0]
    backup = next(iter(http.backups.values()))
    assert backup["Definition"] == original and backup["PipelineID"] == PIPELINE
    assert len(http.updates) == 1
    assert len([call for call in http.calls if "/upgrades/" in call[1]]) == 2
    assert "UPDATED: ForecastMaster_Hourly" in capsys.readouterr().out
    for method, url, kwargs in http.calls:
        assert kwargs["allow_redirects"] is False
        assert "/schedules" not in url and "/jobs" not in url and "/roleAssignments" not in url
        assert method in {"GET", "POST", "PUT"}
        if method == "POST":
            assert url.endswith(("/getDefinition", "/updateDefinition"))


def test_already_set_makes_no_backup_or_update():
    http = HTTP()
    value = M.content(http.definition)
    target(value).pop("externalReferences")
    http.replace_pipeline(value)
    assert run(http) == "ALREADY SET"
    assert not http.backups and not http.updates


def test_discovers_unique_pipeline_across_pages():
    http = HTTP()
    http.pages.insert(0, [{"id": CONNECTION, "displayName": M.PIPELINE_NAME, "type": "Notebook"}])
    assert run(http) == "UPDATED"


@pytest.mark.parametrize("count", [0, 2])
def test_missing_or_duplicate_pipeline_is_rejected_before_write(count):
    http = HTTP()
    http.pages[0] *= count
    with pytest.raises(ValueError, match="exactly one ForecastMaster_Hourly"):
        run(http)
    assert not http.updates and not http.backups


def test_notebook_name_guard():
    http = HTTP()
    http.worker_name = "Other notebook"
    with pytest.raises(ValueError, match="identity differs"):
        run(http)
    assert not http.backups and not http.updates


@pytest.mark.parametrize("field", ["notebookId", "workspaceId"])
def test_wrong_worker_ids_fail_before_write(field):
    http = HTTP()
    value = M.content(http.definition)
    target(value)["typeProperties"][field] = CONNECTION
    http.replace_pipeline(value)
    with pytest.raises(ValueError, match="ID differs"):
        run(http)
    assert not http.updates and not http.backups


@pytest.mark.parametrize("name,value", [
    ("FM_RUN_MODE", {"type": "string", "value": "REQUESTS"}),
    ("FM_RUN_MODE", {"type": "int", "value": "HOURLY"}),
    ("FM_METADATA_JSON", {"type": "string", "value": "@activity('Check_Demand_Metadata').output"}),
    ("FM_METADATA_JSON", {"type": "string", "value": {"type": "Unknown", "value": M.METADATA_EXPRESSION}}),
])
def test_parameter_guard_preserves_misconfigured_pipeline(name, value):
    http = HTTP()
    pipeline = M.content(http.definition)
    target(pipeline)["typeProperties"]["parameters"][name] = value
    http.replace_pipeline(pipeline)
    with pytest.raises(ValueError):
        run(http)
    assert not http.updates and not http.backups


def test_hourly_case_and_plain_expression_are_preserved():
    http = HTTP()
    pipeline = M.content(http.definition)
    params = target(pipeline)["typeProperties"]["parameters"]
    params["FM_RUN_MODE"]["value"] = "Hourly"
    params["FM_METADATA_JSON"]["value"] = M.METADATA_EXPRESSION
    http.replace_pipeline(pipeline)
    assert run(http) == "UPDATED"
    assert target(M.content(http.definition))["typeProperties"]["parameters"] == params


def test_duplicate_activity_in_another_branch_fails_before_write():
    http = HTTP()
    pipeline = M.content(http.definition)
    pipeline["properties"]["activities"][1]["typeProperties"]["ifFalseActivities"] = [copy.deepcopy(target(pipeline))]
    http.replace_pipeline(pipeline)
    with pytest.raises(ValueError, match="duplicated"):
        run(http)
    assert not http.backups and not http.updates


@pytest.mark.parametrize("reference", [{}, {"connection": CONNECTION, "other": "retain"}, {"connection": "invalid"}])
def test_unknown_connection_shape_is_not_discarded(reference):
    http = HTTP()
    pipeline = M.content(http.definition)
    target(pipeline)["externalReferences"] = reference
    http.replace_pipeline(pipeline)
    with pytest.raises(ValueError):
        run(http)
    assert not http.updates and not http.backups


@pytest.mark.parametrize("failure", ["backup_status", "corrupt_backup", "concurrent_edit"])
def test_backup_or_concurrent_change_prevents_update(failure):
    http = HTTP()
    setattr(http, failure, 403 if failure == "backup_status" else True)
    with pytest.raises(RuntimeError):
        run(http)
    assert not http.updates


def test_readback_changes_cannot_be_reported_as_success(capsys):
    http = HTTP()
    http.corrupt_readback = True
    with pytest.raises(RuntimeError, match="readback differs"):
        run(http)
    assert len(http.updates) == 1 and http.backups
    assert "UPDATED:" not in capsys.readouterr().out


def test_update_failure_is_not_retried_or_followed_by_any_other_mutation():
    http = HTTP()
    http.update_status = 401
    with pytest.raises(RuntimeError, match="HTTP 401"):
        run(http)
    assert len(http.updates) == 1 and http.backups
    assert http.calls[-1][1].endswith("/updateDefinition")


def test_lro_reads_definition_result_and_honors_poll_interval():
    responses = iter([
        Response(202, headers={"x-ms-operation-id": OPERATION, "Retry-After": "30"}),
        Response(200, {"status": "Running"}, {"Retry-After": "5"}),
        Response(200, {"status": "Succeeded"}),
        Response(200, {"definition": definition()}),
    ])
    calls, sleeps = [], []
    def request(method, url, **kwargs):
        calls.append((method, url))
        return next(responses)
    api = M.Fabric(SimpleNamespace(request=request), token, sleeps.append)
    assert api.call("POST", "/workspaces/example/items/example/getDefinition") == {"definition": definition()}
    assert sleeps == [30, 5]
    assert [method for method, _ in calls] == ["POST", "GET", "GET", "GET"]
    assert calls[-1][1] == M.BASE + "/operations/" + OPERATION + "/result"


@pytest.mark.parametrize("state", ["Succeeded", "Failed", "Cancelled", "Unexpected"])
def test_update_lro_never_repeats_post_or_requests_missing_result(state):
    responses = iter([
        Response(202, headers={"x-ms-operation-id": OPERATION}),
        Response(200, {"status": state}),
    ])
    calls = []
    def request(method, url, **kwargs):
        calls.append((method, url))
        return next(responses)
    api = M.Fabric(SimpleNamespace(request=request), token, lambda _: None)
    if state == "Succeeded":
        assert api.call("POST", "/updateDefinition", result=False) is None
    else:
        with pytest.raises(RuntimeError):
            api.call("POST", "/updateDefinition", result=False)
    assert [method for method, _ in calls] == ["POST", "GET"]


class ExitNotebook(Exception):
    pass


@pytest.mark.parametrize("is_pipeline", [False, True])
def test_exact_copy_paste_file_executes_in_separate_notebook_and_exits(monkeypatch, is_pipeline):
    http = HTTP()
    def leave(value):
        raise ExitNotebook(value)
    monkeypatch.setitem(sys.modules, "requests", http)
    monkeypatch.setitem(sys.modules, "notebookutils", SimpleNamespace(
        credentials=SimpleNamespace(getToken=token), notebook=SimpleNamespace(exit=leave),
        runtime=SimpleNamespace(context={"isForPipeline": is_pipeline}),
    ))
    if is_pipeline:
        with pytest.raises(RuntimeError, match="interactively"):
            exec(compile(CODE, str(CELL), "exec"), {"__name__": "__main__"})
        assert not http.calls
    else:
        with pytest.raises(ExitNotebook, match="UPDATED: ForecastMaster_Hourly"):
            exec(compile(CODE, str(CELL), "exec"), {"__name__": "__main__"})
        assert len(http.updates) == 1
