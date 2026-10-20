"""Synthetic qualification of publication, event processing and new-item setup."""

import ast
import copy
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace
from uuid import uuid4

import pytest
from azure.core import MatchConditions
from azure.core.exceptions import ResourceExistsError

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent / "notebook-r05.4"
sys.path.insert(0, str(PARENT / "Refresh/source"))
sys.path.insert(0, str(ROOT))
import native_consumer as consumer  # noqa: E402
import native_producer as producer  # noqa: E402
import install_native as installer  # noqa: E402
from request_worker import WorkerRefreshError  # noqa: E402


class NativeFS:
    def __init__(self):
        self.files, self.reads = {}, []

    def exists(self, path):
        return path in self.files

    def ls(self, path):
        prefix = path.rstrip("/") + "/"
        return [SimpleNamespace(name=name[len(prefix):], isFile=True)
                for name in self.files if name.startswith(prefix) and "/" not in name[len(prefix):]]

    def head(self, path, size):
        self.reads.append(path)
        return self.files[path].decode()[:size]

    def mkdirs(self, path):
        return True


class Store:
    def __init__(self):
        self.values, self.writes = {}, []
        self.busy = False
        self.acquired = self.released = 0

    def read(self, name):
        return copy.deepcopy(self.values.get(name))

    def write(self, name, value):
        self.writes.append(name)
        self.values[name] = copy.deepcopy(value)

    def acquire(self):
        self.acquired += 1
        return not self.busy

    def release(self):
        self.released += 1


class Files:
    def __init__(self, fs, root="Files"):
        self.fs, self.root = fs, root
        self.events, self.directories = [], set()
        self.fail_readback = None
        self.closed = False

    def close(self):
        self.closed = True

    def get_sub_directory_client(self, name):
        parent = self
        def create():
            if name in parent.directories:
                raise ResourceExistsError("exists")
            parent.directories.add(name)
        return SimpleNamespace(create_directory=create, close=lambda: None)

    def get_file_client(self, name):
        parent, path = self, self.root + "/" + name
        def upload(value, **kwargs):
            assert kwargs == {"overwrite": True, "match_condition": MatchConditions.IfMissing}
            assert path not in parent.fs.files
            parent.fs.files[path] = value
            parent.events.append(path)
        def readall():
            return b"different" if parent.fail_readback and parent.fail_readback in path else parent.fs.files[path]
        return SimpleNamespace(upload_data=upload,
            download_file=lambda: SimpleNamespace(readall=readall), close=lambda: None)


def publish(fs, files=None):
    return producer.submit_native_request(files or Files(fs))


def complete():
    return object(), {"Status": "SUCCESS", "StageErrors": [], "FileResults": {}, "ModelRefresh": {"Status": "COMPLETED"}}


def test_publisher_writes_immutable_body_before_verified_ready_marker():
    fs, files = NativeFS(), None
    files = Files(fs)
    result = publish(fs, files)
    assert result["Status"] == "QUEUED"
    assert files.events == [result["RequestFile"], result["ReadyReceipt"]]
    assert json.loads(fs.files[result["RequestFile"]]) == producer.NATIVE_COMMAND
    marker = json.loads(fs.files[result["ReadyReceipt"]])
    assert marker["ContentSHA256"] == hashlib.sha256(fs.files[result["RequestFile"]]).hexdigest()
    assert not result["ReadyReceipt"].startswith("Files/" + producer.NATIVE_REQUEST_PREFIX)


def test_existing_directories_and_multiple_clicks_are_supported():
    fs = NativeFS()
    files = Files(fs)
    first, second = publish(fs, files), publish(fs, files)
    assert first["RequestID"] != second["RequestID"]
    assert len(fs.files) == 4


def test_body_readback_failure_never_publishes_ready_receipt():
    fs = NativeFS()
    files = Files(fs)
    files.fail_readback = "native-requests/"
    with pytest.raises(RuntimeError, match="readback differs"):
        publish(fs, files)
    assert len(fs.files) == 1 and all("native-ready/" not in path for path in fs.files)


@pytest.mark.parametrize("subject", [
    "", "/Files/Demand/refresh-" + str(uuid4()) + ".json",
    consumer.NATIVE_SUBJECT_PREFIX + "../refresh-" + str(uuid4()) + ".json",
    consumer.NATIVE_SUBJECT_PREFIX + "refresh-invalid.json",
    consumer.NATIVE_SUBJECT_PREFIX + "nested/refresh-" + str(uuid4()) + ".json",
    consumer.NATIVE_SUBJECT_PREFIX + "refresh-" + str(uuid4()) + ".json/extra",
])
def test_non_request_event_subject_is_rejected_before_any_state_work(subject):
    with pytest.raises(ValueError):
        consumer.prepare_native_worker(NativeFS(), Store(), "Files", subject)


def test_early_filecreated_event_does_not_acknowledge_an_incomplete_upload():
    fs, store = NativeFS(), Store()
    name = "refresh-" + str(uuid4()) + ".json"
    subject = consumer.NATIVE_SUBJECT_PREFIX + name
    fs.files[subject.lstrip("/")] = b""
    with pytest.raises(RuntimeError, match="NATIVE_REQUEST_NOT_READY"):
        consumer.prepare_native_worker(fs, store, "Files", subject)
    assert not store.writes and store.acquired == 0


def test_ready_requests_coalesce_and_duplicate_events_do_not_repeat_refresh():
    fs, store = NativeFS(), Store()
    first, second = publish(fs), publish(fs)
    original = copy.deepcopy(fs.files)
    subject = "/" + first["RequestFile"]
    worker, existing = consumer.prepare_native_worker(fs, store, "Files", subject)
    assert existing is None
    calls = []
    def refresh():
        calls.append(True)
        return complete()
    _, result = consumer.run_native_request(worker, subject, refresh)
    assert result["Status"] == "SUCCESS" and len(result["Requests"]) == 2
    assert store.acquired == store.released == 1
    _, existing = consumer.prepare_native_worker(fs, store, "Files", "/" + second["RequestFile"])
    assert existing["Status"] == "ALREADY_PROCESSED"
    assert len(calls) == 1 and fs.files == original


def test_other_unready_requests_do_not_join_the_batch_or_become_rejected():
    fs, store = NativeFS(), Store()
    ready = publish(fs)
    incomplete = "refresh-" + str(uuid4()) + ".json"
    fs.files["Files/" + producer.NATIVE_REQUEST_PREFIX + incomplete] = b""
    subject = "/" + ready["RequestFile"]
    worker, _ = consumer.prepare_native_worker(fs, store, "Files", subject)
    _, result = consumer.run_native_request(worker, subject, complete)
    assert len(result["Requests"]) == 1 and len(store.values["requests.json"]["Requests"]) == 1


def test_busy_is_a_retryable_failure_with_no_acknowledgement():
    fs, store = NativeFS(), Store()
    item = publish(fs)
    subject = "/" + item["RequestFile"]
    worker, _ = consumer.prepare_native_worker(fs, store, "Files", subject)
    store.busy = True
    with pytest.raises(RuntimeError, match="NATIVE_WRITER_BUSY"):
        consumer.run_native_request(worker, subject, lambda: pytest.fail("Competing writer"))
    assert not store.writes
    store.busy = False
    assert consumer.run_native_request(worker, subject, complete)[1]["Status"] == "SUCCESS"


@pytest.mark.parametrize("model_status", ["FAILED", "PENDING"])
def test_failed_request_remains_failed_on_activity_retry(model_status):
    fs, store = NativeFS(), Store()
    item = publish(fs)
    subject = "/" + item["RequestFile"]
    worker, _ = consumer.prepare_native_worker(fs, store, "Files", subject)
    def failed():
        return None, {"Status": "SUCCESS", "ModelRefresh": {"Status": model_status}}
    with pytest.raises(WorkerRefreshError):
        consumer.run_native_request(worker, subject, failed)
    assert store.values["requests.json"]["Requests"][item["RequestID"]]["Status"] == "FAILED"
    with pytest.raises(WorkerRefreshError, match="terminal FAILED"):
        consumer.prepare_native_worker(fs, store, "Files", subject)


@pytest.mark.parametrize("mutation", ["hash", "identity", "schema", "body"])
def test_changed_or_malformed_ready_state_cannot_start_a_refresh(mutation):
    fs, store = NativeFS(), Store()
    item = publish(fs)
    marker = json.loads(fs.files[item["ReadyReceipt"]])
    if mutation == "hash":
        marker["ContentSHA256"] = "invalid"
    elif mutation == "identity":
        marker["RequestID"] = str(uuid4())
    elif mutation == "schema":
        marker["SchemaVersion"] = True
    else:
        fs.files[item["RequestFile"]] = b"changed"
    fs.files[item["ReadyReceipt"]] = json.dumps(marker).encode()
    with pytest.raises(ValueError):
        consumer.prepare_native_worker(fs, store, "Files", "/" + item["RequestFile"])
    assert not store.writes and not store.acquired


def test_another_worker_can_complete_between_preflight_and_run():
    fs, store = NativeFS(), Store()
    item = publish(fs)
    subject = "/" + item["RequestFile"]
    first, _ = consumer.prepare_native_worker(fs, store, "Files", subject)
    second, _ = consumer.prepare_native_worker(fs, store, "Files", subject)
    consumer.run_native_request(first, subject, complete)
    _, result = consumer.run_native_request(second, subject, lambda: pytest.fail("Already handled"))
    assert result["Status"] == "ALREADY_PROCESSED"


def test_parent_modules_and_calculation_configuration_are_unchanged_in_new_notebook():
    parent = json.loads((PARENT / "ForecastMaster_Refresh.ipynb").read_text())
    native = json.loads((ROOT / "ForecastMaster_Native_Adhoc.ipynb").read_text())
    for index in [2, 3, 5, 6, 7, 8, 9, 10, 11]:
        assert native["cells"][index] == parent["cells"][index]
    assert native["cells"][1]["metadata"]["tags"] == ["parameters"]
    assert 'FM_EVENT_SUBJECT = ""' in "".join(native["cells"][1]["source"])
    for index, cell in enumerate(native["cells"]):
        if cell["cell_type"] == "code":
            compile("".join(cell["source"]), "native-cell-" + str(index), "exec")


def test_existing_function_definitions_are_preserved_and_new_function_is_bound():
    old = (ROOT.parent / "functions-r05.2/function_app.py").read_text()
    new = (ROOT / "ForecastMaster-Actions-R06-native.txt").read_text()
    old_defs = {node.name: ast.dump(node) for node in ast.parse(old).body if isinstance(node, (ast.FunctionDef, ast.ClassDef))}
    new_defs = {node.name: ast.dump(node) for node in ast.parse(new).body if isinstance(node, (ast.FunctionDef, ast.ClassDef))}
    assert all(new_defs[name] == value for name, value in old_defs.items())
    assert "submitNativeRefreshR06" in new_defs
    assert new.count('udf.connection(argName="lakehouse", alias="ForecastMaster")') == 4


def test_exact_new_function_entry_returns_json_string_and_closes_connection():
    fs = NativeFS()
    files = Files(fs)
    code = ast.parse((ROOT / "ForecastMaster-Actions-R06-native.txt").read_text())
    entry = next(node for node in code.body if isinstance(node, ast.FunctionDef) and node.name == "submitNativeRefreshR06")
    def connection(**kwargs):
        assert kwargs == {"argName": "lakehouse", "alias": "ForecastMaster"}
        return lambda function: function
    scope = {**vars(producer), "udf": SimpleNamespace(connection=connection, function=lambda: lambda value: value),
             "fn": SimpleNamespace(FabricLakehouseClient=object)}
    exec(compile(ast.Module(body=[entry], type_ignores=[]), "native-function-entry", "exec"), scope)
    value = scope["submitNativeRefreshR06"](SimpleNamespace(connectToFiles=lambda: files))
    assert isinstance(value, str) and json.loads(value)["Status"] == "QUEUED" and files.closed


def test_native_processing_retains_the_existing_sharepoint_request_history():
    fs, store = NativeFS(), Store()
    previous = str(uuid4())
    record = {"Status": "SUCCESS", "BatchID": "old-batch", "RequestFile": "old-source.json"}
    store.values["requests.json"] = {"SchemaVersion": 1, "Requests": {previous: record}}
    item = publish(fs)
    subject = "/" + item["RequestFile"]
    worker, _ = consumer.prepare_native_worker(fs, store, "Files", subject)
    consumer.run_native_request(worker, subject, complete)
    assert store.values["requests.json"]["Requests"][previous] == record
    assert len(store.values["requests.json"]["Requests"]) == 2


def test_ready_but_invalid_command_is_rejected_without_running_ingestion():
    fs, store = NativeFS(), Store()
    item = publish(fs)
    fs.files[item["RequestFile"]] = b'{"SchemaVersion":1,"Action":"OTHER","Scope":"ALL"}'
    marker = json.loads(fs.files[item["ReadyReceipt"]])
    marker["ContentSHA256"] = hashlib.sha256(fs.files[item["RequestFile"]]).hexdigest()
    fs.files[item["ReadyReceipt"]] = json.dumps(marker).encode()
    subject = "/" + item["RequestFile"]
    worker, _ = consumer.prepare_native_worker(fs, store, "Files", subject)
    with pytest.raises(WorkerRefreshError):
        consumer.run_native_request(worker, subject, lambda: pytest.fail("Unrecognized command"))
    assert store.values["requests.json"]["Requests"][item["RequestID"]]["Status"] == "REJECTED"
    with pytest.raises(WorkerRefreshError, match="terminal REJECTED"):
        consumer.prepare_native_worker(fs, store, "Files", subject)


class Response:
    def __init__(self, status=200, body=None, headers=None):
        self.status_code, self.body, self.headers = status, body, headers or {}
        self.text = json.dumps(body)

    def json(self):
        return copy.deepcopy(self.body)


class HTTP:
    def __init__(self):
        parent = json.loads((PARENT / "ForecastMaster_Refresh.ipynb").read_text())
        parent["metadata"]["dependencies"] = {"lakehouse": {
            "default_lakehouse": installer.LAKEHOUSE,
            "default_lakehouse_workspace_id": installer.WORKSPACE,
        }}
        self.items = [{"id": installer.EXISTING_NOTEBOOK, "type": "Notebook", "displayName": "ForecastMaster_Refresh"}]
        self.definitions = {installer.EXISTING_NOTEBOOK: {"parts": [installer.definition_part("notebook-content.ipynb", parent)]}}
        self.calls = []
        self.create_failure = False

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, copy.deepcopy(kwargs)))
        tail = url.removeprefix(installer.BASE)
        if method == "GET" and tail.endswith("/items/" + installer.EXISTING_NOTEBOOK):
            return Response(200, self.items[0])
        if tail.endswith("/items"):
            if method == "GET":
                return Response(200, {"value": self.items})
            if method == "POST":
                if self.create_failure:
                    return Response(403, {"message": "Not authorized"})
                body = kwargs["json"]
                identity = str(uuid4())
                item = {"id": identity, "displayName": body["displayName"], "type": body["type"]}
                self.items.append(item)
                self.definitions[identity] = body["definition"]
                return Response(201, item)
        if "/getDefinition" in tail:
            identity = tail.split("/")[-2]
            return Response(200, {"definition": self.definitions[identity]})
        raise AssertionError((method, url))


def native_notebook():
    return json.loads((ROOT / "ForecastMaster_Native_Adhoc.ipynb").read_text())


def test_installer_creates_only_new_items_with_shared_lakehouse_and_no_explicit_connection():
    http = HTTP()
    original = copy.deepcopy(http.definitions[installer.EXISTING_NOTEBOOK])
    result = installer.install_native(http, lambda _: "synthetic-token", native_notebook(), sleep=lambda _: None)
    assert len(http.items) == 3 and http.definitions[installer.EXISTING_NOTEBOOK] == original
    pipeline = installer.decode_part(http.definitions[result["PipelineID"]], "pipeline-content.json")
    activity = pipeline["properties"]["activities"][0]
    assert "externalReferences" not in activity
    assert activity["typeProperties"]["notebookId"] == result["NotebookID"]
    assert set(pipeline["properties"]["parameters"]) == {"Subject", "Type", "Source"}
    for method, url, kwargs in http.calls:
        assert kwargs["allow_redirects"] is False
        assert "/updateDefinition" not in url and "/schedules" not in url and "/jobs" not in url
        assert method in {"GET", "POST"}


def test_repeated_setup_reuses_verified_native_items_without_overwriting():
    http = HTTP()
    first = installer.install_native(http, lambda _: "synthetic-token", native_notebook())
    second = installer.install_native(http, lambda _: "synthetic-token", native_notebook())
    assert first == second and len(http.items) == 3
    assert len([call for call in http.calls if call[0] == "POST" and call[1].endswith("/items")]) == 2


def test_existing_different_native_item_is_not_overwritten():
    http = HTTP()
    result = installer.install_native(http, lambda _: "synthetic-token", native_notebook())
    native = installer.decode_part(http.definitions[result["NotebookID"]], "notebook-content.ipynb")
    native["cells"][1]["source"] = ['FM_EVENT_SUBJECT = "modified"']
    http.definitions[result["NotebookID"]] = {"parts": [installer.definition_part("notebook-content.ipynb", native)]}
    before = len(http.items)
    with pytest.raises(ValueError, match="differs"):
        installer.install_native(http, lambda _: "synthetic-token", native_notebook())
    assert len(http.items) == before


def test_conflicting_item_type_or_duplicate_name_stops_before_creation():
    for items in (
        [{"id": str(uuid4()), "displayName": installer.PIPELINE_NAME, "type": "Notebook"}],
        [{"id": str(uuid4()), "displayName": installer.NOTEBOOK_NAME, "type": "Notebook"}] * 2,
    ):
        http = HTTP()
        http.items.extend(items)
        with pytest.raises(ValueError):
            installer.install_native(http, lambda _: "synthetic-token", native_notebook())
        assert all(not (method == "POST" and url.endswith("/items")) for method, url, _ in http.calls)


def test_unsupported_lakehouse_binding_and_creation_denial_do_not_mutate_existing_items():
    http = HTTP()
    http.create_failure = True
    with pytest.raises(RuntimeError, match="HTTP 403"):
        installer.install_native(http, lambda _: "synthetic-token", native_notebook())
    assert len(http.items) == 1
    parent = installer.decode_part(http.definitions[installer.EXISTING_NOTEBOOK], "notebook-content.ipynb")
    parent["metadata"] = {}
    http.definitions[installer.EXISTING_NOTEBOOK] = {"parts": [installer.definition_part("notebook-content.ipynb", parent)]}
    with pytest.raises(ValueError, match="Lakehouse metadata"):
        installer.install_native(http, lambda _: "synthetic-token", native_notebook())
    assert len(http.items) == 1


def test_lro_creation_reads_result_without_repeating_post():
    identity = str(uuid4())
    responses = iter([
        Response(202, headers={"x-ms-operation-id": identity, "Retry-After": "30"}),
        Response(200, {"status": "Running"}, {"Retry-After": "5"}),
        Response(200, {"status": "Succeeded"}), Response(200, {"id": identity}),
    ])
    calls, sleeps = [], []
    def request(method, url, **kwargs):
        calls.append((method, url))
        return next(responses)
    api = installer.API(SimpleNamespace(request=request), lambda _: "synthetic-token", sleeps.append)
    assert api.call("POST", "/workspaces/example/items") == {"id": identity}
    assert [method for method, _ in calls] == ["POST", "GET", "GET", "GET"] and sleeps == [30, 5]


class ExitNotebook(Exception):
    pass


def test_exact_generated_setup_cell_creates_verifies_and_exits(monkeypatch):
    http = HTTP()
    def leave(value):
        raise ExitNotebook(value)
    monkeypatch.setitem(sys.modules, "requests", http)
    monkeypatch.setitem(sys.modules, "notebookutils", SimpleNamespace(
        credentials=SimpleNamespace(getToken=lambda _: "synthetic-token"), notebook=SimpleNamespace(exit=leave),
    ))
    with pytest.raises(ExitNotebook, match="READY: native items"):
        exec(compile((ROOT / "SETUP NATIVE ADHOC R01.txt").read_text(), "exact-native-cell", "exec"), {})
    assert len(http.items) == 3


def test_exact_native_preflight_exits_before_reader_or_spark_on_duplicate(monkeypatch):
    fs, store = NativeFS(), Store()
    item = publish(fs)
    subject = "/" + item["RequestFile"]
    worker, _ = consumer.prepare_native_worker(fs, store, "Files", subject)
    consumer.run_native_request(worker, subject, complete)
    root = f"abfss://{installer.WORKSPACE}@onelake.dfs.fabric.microsoft.com/{installer.LAKEHOUSE}/Files"
    # The duplicate result comes from the shared ledger, without queue-file reads.
    def leave(value):
        raise ExitNotebook(value)
    monkeypatch.setitem(sys.modules, "notebookutils", SimpleNamespace(
        runtime=SimpleNamespace(context={"defaultLakehouseId": installer.LAKEHOUSE, "defaultLakehouseWorkspaceId": installer.WORKSPACE}),
        credentials=SimpleNamespace(getToken=lambda _: "synthetic-token"), notebook=SimpleNamespace(exit=leave), fs=fs,
    ))
    scope = {**vars(consumer), "WORKSPACE_ID": installer.WORKSPACE, "LAKEHOUSE_ID": installer.LAKEHOUSE,
             "FM_EVENT_SUBJECT": subject, "OneLakeQueueStore": lambda *args: store}
    reads = len(fs.reads)
    with pytest.raises(ExitNotebook, match="ALREADY_PROCESSED"):
        exec(compile((ROOT / "native_preflight.txt").read_text(), "native-preflight", "exec"), scope)
    assert scope["worker_files_root"] == root and len(fs.reads) == reads


def test_exact_native_execution_cell_keeps_full_demand_and_confirmed_model_binding(monkeypatch):
    fs, store = NativeFS(), Store()
    item = publish(fs)
    subject = "/" + item["RequestFile"]
    worker, _ = consumer.prepare_native_worker(fs, store, "Files", subject)
    native = native_notebook()
    scope = {**vars(consumer), "fm_mode": "REQUESTS", "request_worker": worker,
             "FM_EVENT_SUBJECT": subject, "display": lambda _: None}
    exec(compile("".join(native["cells"][2]["source"]), "native-config", "exec"), scope)
    spark = object()
    monkeypatch.setitem(sys.modules, "pyspark", SimpleNamespace())
    monkeypatch.setitem(sys.modules, "pyspark.sql", SimpleNamespace(
        SparkSession=SimpleNamespace(builder=SimpleNamespace(getOrCreate=lambda: spark))))
    def leave(value):
        raise ExitNotebook(value)
    scope["notebookutils"] = SimpleNamespace(notebook=SimpleNamespace(exit=leave))
    scope["refresh_confirmed_model"] = object()
    calls = []
    def refresh(got_spark, runtime, config, utils, rules):
        assert got_spark is spark and runtime["refresh_model"] is scope["refresh_confirmed_model"]
        assert config["SOURCE_ROOT"] == "Files/Demand" and config["REFRESH_MODE"] == "ALL"
        assert config["ALLOWED_PROFILES"] == ["Local", "Ext"]
        assert config["FORCE_MODEL_REFRESH"] is True and config["REFRESH_SEMANTIC_MODEL"] is True
        calls.append(config)
        _, result = complete()
        return SimpleNamespace(events=[], timings=[]), result
    scope["run_refresh"] = refresh
    with pytest.raises(ExitNotebook, match='"Status": "SUCCESS"'):
        exec(compile("".join(native["cells"][12]["source"]), "exact-native-execution", "exec"), scope)
    assert len(calls) == 1 and store.values["requests.json"]["Requests"][item["RequestID"]]["Status"] == "SUCCESS"
