"""Publish native requests and a separate readiness receipt; no refresh runs here."""

import hashlib
import json
from typing import Any
from uuid import uuid4

from azure.core import MatchConditions
from azure.core.exceptions import ResourceExistsError

NATIVE_REQUEST_PREFIX = "ForecastMasterRefreshState/native-requests/"
NATIVE_READY_PREFIX = "ForecastMasterRefreshState/native-ready/"
NATIVE_COMMAND = {"SchemaVersion": 1, "Action": "REFRESH_DEMAND", "Scope": "ALL"}


def submit_native_request(files: Any) -> dict[str, Any]:
    identity = str(uuid4())
    name = "refresh-" + identity + ".json"
    for directory in (NATIVE_REQUEST_PREFIX, NATIVE_READY_PREFIX):
        client = files.get_sub_directory_client(directory.rstrip("/"))
        try:
            client.create_directory()
        except ResourceExistsError:
            pass
        finally:
            client.close()
    payload = json.dumps(NATIVE_COMMAND, sort_keys=True).encode("utf-8")
    marker = {
        "SchemaVersion": 1, "RequestID": identity, "RequestFile": name,
        "ContentSHA256": hashlib.sha256(payload).hexdigest(),
    }
    # DataLake upload may expose a created file before its final flush. The
    # consumer admits only requests with this separate, verified ready receipt.
    for path, value in (
        (NATIVE_REQUEST_PREFIX + name, payload),
        (NATIVE_READY_PREFIX + name, json.dumps(marker, sort_keys=True).encode()),
    ):
        client = files.get_file_client(path)
        try:
            client.upload_data(value, overwrite=True, match_condition=MatchConditions.IfMissing)
            if client.download_file().readall() != value:
                raise RuntimeError("Native request readback differs: " + identity + " at " + path)
        finally:
            client.close()
    return {
        "SchemaVersion": 1, "CodeVersion": "R06-NATIVE-R01", "Status": "QUEUED",
        "RequestID": identity, "RequestFile": "Files/" + NATIVE_REQUEST_PREFIX + name,
        "ReadyReceipt": "Files/" + NATIVE_READY_PREFIX + name,
        "Message": "Request submitted. Queue acceptance is not refresh completion.",
    }
