"""Native-event adapter over the unchanged R05.4 request worker and writer lock."""

import hashlib
import json
from typing import Any
from uuid import UUID

from request_worker import REQUEST_NAME, RequestWorker, WorkerRefreshError

NATIVE_SUBJECT_PREFIX = "/Files/ForecastMasterRefreshState/native-requests/"


def native_request_name(subject: str) -> str:
    if not isinstance(subject, str) or not subject.startswith(NATIVE_SUBJECT_PREFIX):
        raise ValueError("Expected a native request event subject under " + NATIVE_SUBJECT_PREFIX)
    name = subject[len(NATIVE_SUBJECT_PREFIX):]
    match = REQUEST_NAME.fullmatch(name)
    if match is None:
        raise ValueError("Expected exactly refresh-<GUID>.json in the native request folder")
    return name


class NativeQueueFS:
    def __init__(self, fs: Any, files_root: str, acknowledged: set[str]):
        self.fs = fs
        self.request_folder = files_root + "/ForecastMasterRefreshState/native-requests"
        self.ready_folder = files_root + "/ForecastMasterRefreshState/native-ready"
        self.acknowledged = acknowledged

    def ready(self, name: str) -> bool:
        marker_path = self.ready_folder + "/" + name
        if not self.fs.exists(marker_path):
            return False
        marker = json.loads(self.fs.head(marker_path, 65537))
        match = REQUEST_NAME.fullmatch(name)
        if match is None:
            raise ValueError("Invalid native request filename")
        identity = str(UUID(match[1]))
        if (
            not isinstance(marker, dict)
            or set(marker) != {"SchemaVersion", "RequestID", "RequestFile", "ContentSHA256"}
            or type(marker.get("SchemaVersion")) is not int
            or marker["SchemaVersion"] != 1
            or marker.get("RequestID") != identity
            or marker.get("RequestFile") != name
        ):
            raise ValueError("Native readiness receipt is invalid for " + name)
        payload = self.fs.head(self.request_folder + "/" + name, 65537).encode()
        if len(payload) > 65536 or hashlib.sha256(payload).hexdigest() != marker.get("ContentSHA256"):
            raise ValueError("Native request differs from its readiness receipt: " + name)
        return True

    def ls(self, path: str) -> list[Any]:
        if path != self.request_folder:
            return self.fs.ls(path)
        values = []
        for item in self.fs.ls(path):
            match = REQUEST_NAME.fullmatch(item.name)
            if item.isFile and match:
                identity = str(UUID(match[1]))
                if identity in self.acknowledged or self.ready(item.name):
                    values.append(item)
        return values

    def head(self, path: str, size: int) -> str:
        return self.fs.head(path, size)

    def mkdirs(self, path: str) -> bool:
        return self.fs.mkdirs(path)


def native_terminal_result(worker: RequestWorker, name: str) -> dict[str, Any] | None:
    identity = str(UUID(REQUEST_NAME.fullmatch(name)[1]))
    record = worker._ledger()["Requests"].get(identity)
    if record is None:
        return None
    if record["Status"] != "SUCCESS":
        raise WorkerRefreshError(
            "Native request has a retained terminal " + record["Status"] + " receipt: " + identity
        )
    return {"Status": "ALREADY_PROCESSED", "Mode": "NATIVE_REQUESTS", "RequestID": identity, "Receipt": record}


def prepare_native_worker(fs: Any, store: Any, files_root: str, subject: str) -> tuple[Any, Any]:
    name = native_request_name(subject)
    adapter = NativeQueueFS(fs, files_root, set())
    worker = RequestWorker(adapter, store, adapter.request_folder, files_root + "/ForecastMasterRefreshState")
    terminal = native_terminal_result(worker, name)
    if terminal is not None:
        return worker, terminal
    adapter.acknowledged = set(worker._ledger()["Requests"])
    if not adapter.ready(name):
        # Do not acknowledge a FileCreated event emitted before upload finished.
        # The on-demand Notebook activity retries this transient condition.
        raise RuntimeError("NATIVE_REQUEST_NOT_READY: " + name + "; no request was acknowledged")
    return worker, None


def run_native_request(worker: RequestWorker, subject: str, refresh: Any) -> tuple[Any, dict[str, Any]]:
    name = native_request_name(subject)
    engine, result = worker.run(refresh)
    if result.get("Status") == "BUSY":
        raise RuntimeError("NATIVE_WRITER_BUSY: request remains queued for the activity retry")
    # Recheck the particular event's receipt even if another writer coalesced it.
    terminal = native_terminal_result(worker, name)
    if terminal is None:
        raise WorkerRefreshError("The event's native request has no successful receipt: " + name)
    if result.get("Status") == "IDLE":
        return None, terminal
    result.update(Mode="NATIVE_REQUESTS", EventSubject=subject)
    return engine, result
