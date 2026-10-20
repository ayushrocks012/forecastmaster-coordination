"""Consume immutable SharePoint request files with OneLake receipts and one writer.

The exclusive infinite Blob lease is a run-coordination lock. A killed session
needs deliberate lease recovery after checking that no writer is still running.
No request file or source workbook is moved, edited, or deleted.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable
from datetime import UTC, datetime
from email.utils import format_datetime
from typing import Any
from urllib.parse import quote
from uuid import UUID, uuid4

import requests

REQUEST_NAME = re.compile(
    r"refresh-([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})\.json\Z"
)


def queue_utc() -> str:
    return datetime.now(UTC).isoformat()


class WorkerRefreshError(RuntimeError):
    """The request has a retained failure receipt; it is never a green data refresh."""


class OneLakeQueueStore:
    def __init__(
        self,
        workspace: str,
        lakehouse: str,
        get_token: Callable[[str], str],
        *,
        http: Any = requests,
    ):
        workspace, lakehouse = str(UUID(workspace)), str(UUID(lakehouse))
        self.base = f"https://onelake.blob.fabric.microsoft.com/{workspace}/{lakehouse}/Files/ForecastMasterRefreshState/"
        self.get_token, self.http = get_token, http
        self.lease_id = ""

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": "Bearer " + self.get_token("storage"),
            "x-ms-version": "2021-06-08",
            "x-ms-date": format_datetime(datetime.now(UTC), usegmt=True),
        }

    def _url(self, name: str) -> str:
        if (
            not re.fullmatch(r"[a-zA-Z0-9_.-]+(?:/[a-zA-Z0-9_.-]+)*", name)
            or ".." in name
        ):
            raise ValueError("Invalid worker-state filename")
        return self.base + quote(name, safe="/")

    def read(self, name: str) -> dict[str, Any] | None:
        result = self.http.get(
            self._url(name), headers=self._headers(), timeout=45, allow_redirects=False
        )
        if result.status_code == 404:
            return None
        if result.status_code != 200:
            raise RuntimeError(
                f"Cannot read worker state {name} (HTTP {result.status_code})."
            )
        content = result.json()
        if not isinstance(content, dict):
            raise TypeError("Invalid worker state " + name)
        return content

    def write(self, name: str, content: dict[str, Any]) -> None:
        result = self.http.put(
            self._url(name),
            headers={
                **self._headers(),
                "x-ms-blob-type": "BlockBlob",
                "Content-Type": "application/json",
            },
            data=json.dumps(
                content, ensure_ascii=False, allow_nan=False, indent=2
            ).encode("utf-8"),
            timeout=45,
            allow_redirects=False,
        )
        if result.status_code != 201:
            raise RuntimeError(
                f"Cannot retain worker receipt {name} (HTTP {result.status_code})."
            )

    def acquire(self) -> bool:
        result = self.http.put(
            self._url("worker.lock"),
            headers={
                **self._headers(),
                "x-ms-blob-type": "BlockBlob",
                "If-None-Match": "*",
            },
            data=b"",
            timeout=45,
            allow_redirects=False,
        )
        if result.status_code not in {201, 409, 412}:
            raise RuntimeError(
                f"Cannot initialize writer lock (HTTP {result.status_code})."
            )
        proposed = str(uuid4())
        leased = self.http.put(
            self._url("worker.lock"),
            params={"comp": "lease"},
            headers={
                **self._headers(),
                "x-ms-lease-action": "acquire",
                "x-ms-lease-duration": "-1",
                "x-ms-proposed-lease-id": proposed,
            },
            timeout=45,
            allow_redirects=False,
        )
        if (
            leased.status_code == 409
            and leased.headers.get("x-ms-error-code") == "LeaseAlreadyPresent"
        ):
            return False
        if leased.status_code != 201 or leased.headers.get("x-ms-lease-id") != proposed:
            raise RuntimeError(
                f"Exclusive writer lock could not be verified (HTTP {leased.status_code}). No refresh started."
            )
        self.lease_id = proposed
        return True

    def release(self) -> None:
        if not self.lease_id:
            return
        result = self.http.put(
            self._url("worker.lock"),
            params={"comp": "lease"},
            headers={
                **self._headers(),
                "x-ms-lease-action": "release",
                "x-ms-lease-id": self.lease_id,
            },
            timeout=45,
            allow_redirects=False,
        )
        if result.status_code != 200:
            raise RuntimeError(
                f"Writer lock release failed (HTTP {result.status_code}); check the worker job before recovery."
            )
        self.lease_id = ""


class RequestWorker:
    def __init__(self, fs: Any, store: Any, request_folder: str, state_folder: str):
        self.fs, self.store = fs, store
        self.request_folder, self.state_folder = (
            request_folder.rstrip("/"),
            state_folder.rstrip("/"),
        )

    def _ledger(self) -> dict[str, Any]:
        ledger = self.store.read("requests.json")
        if ledger is None:
            return {"SchemaVersion": 1, "Requests": {}}
        if not isinstance(ledger, dict):
            raise TypeError("Worker request index must be an object.")
        if ledger.get("SchemaVersion") != 1 or not isinstance(
            ledger.get("Requests"), dict
        ):
            raise ValueError(
                "Worker request index is invalid. Retained batch receipts remain available."
            )
        if any(
            not isinstance(v, dict)
            or v.get("Status") not in {"SUCCESS", "FAILED", "REJECTED"}
            for v in ledger["Requests"].values()
        ):
            raise ValueError("Worker request index contains an invalid result.")
        return ledger

    def pending(self) -> list[str]:
        seen = self._ledger()["Requests"]
        names = []
        for item in self.fs.ls(self.request_folder):
            match = REQUEST_NAME.fullmatch(item.name)
            if item.isFile and match and str(UUID(match[1])) not in seen:
                names.append(item.name)
        return sorted(names)

    def run(
        self, refresh: Callable[[], tuple[Any, dict[str, Any]]]
    ) -> tuple[Any, dict[str, Any]]:
        if not self.pending():
            return None, {
                "Status": "IDLE",
                "Message": "No new refresh requests. No source discovery or model refresh ran.",
            }
        if not self.fs.mkdirs(self.state_folder) or not self.fs.mkdirs(
            self.state_folder + "/batches"
        ):
            raise RuntimeError("Cannot prepare the native lakehouse receipt folders.")
        if not self.store.acquire():
            return None, {
                "Status": "BUSY",
                "Message": "Another worker owns the writer lock. Requests remain queued.",
            }
        try:
            ledger = self._ledger()
            names = self.pending()
            if not names:
                return None, {
                    "Status": "IDLE",
                    "Message": "Another worker already handled these requests.",
                }
            batch_id, started = str(uuid4()), queue_utc()
            accepted: list[str] = []
            records: dict[str, Any] = {}
            for name in names:
                match = REQUEST_NAME.fullmatch(name)
                if match is None:
                    raise ValueError("Request filename changed during discovery.")
                identity = str(UUID(match[1]))
                text = self.fs.head(self.request_folder + "/" + name, 65537)
                record: dict[str, Any] = {
                    "RequestFile": name,
                    "ContentSHA256": hashlib.sha256(text.encode()).hexdigest(),
                    "BatchID": batch_id,
                }
                try:
                    if len(text.encode()) > 65536:
                        raise ValueError("Request exceeds the 64 KiB size limit.")
                    body = json.loads(text)
                    if (
                        not isinstance(body, dict)
                        or set(body) != {"SchemaVersion", "Action", "Scope"}
                        or type(body.get("SchemaVersion")) is not int
                        or body
                        != {
                            "SchemaVersion": 1,
                            "Action": "REFRESH_DEMAND",
                            "Scope": "ALL",
                        }
                    ):
                        raise ValueError(
                            "Expected SchemaVersion 1, Action REFRESH_DEMAND, Scope ALL."
                        )
                    accepted.append(identity)
                    record["Status"] = "QUEUED"
                except (ValueError, TypeError) as exc:
                    record.update(Status="REJECTED", Error=str(exc))
                records[identity] = record
            engine: Any = None
            summary: dict[str, Any] = {"Status": "NO_VALID_REQUESTS"}
            if accepted:
                try:
                    engine, summary = refresh()
                except Exception as exc:  # noqa: BLE001 -- preserve outcome, then fail the scheduled job
                    summary = {"Status": "FAILED", "StageErrors": [str(exc)]}
                success = (
                    summary.get("Status") == "SUCCESS"
                    and not summary.get("StageErrors")
                    and summary.get("ModelRefresh", {}).get("Status")
                    in {"COMPLETED", "UNCHANGED"}
                    and not summary.get("FileResults", {}).get("FAILED", 0)
                )
                for identity in accepted:
                    records[identity]["Status"] = "SUCCESS" if success else "FAILED"
            ended = queue_utc()
            for record in records.values():
                record.update(StartedAtUtc=started, FinishedAtUtc=ended)
            result = {
                "SchemaVersion": 1,
                "BatchID": batch_id,
                "StartedAtUtc": started,
                "FinishedAtUtc": ended,
                "Status": "SUCCESS"
                if records and all(r["Status"] == "SUCCESS" for r in records.values())
                else "FAILED",
                "Requests": records,
                "Refresh": summary,
            }
            # A durable batch receipt precedes the compact processed-request index.
            self.store.write("batches/" + batch_id + ".json", result)
            ledger["Requests"].update(records)
            self.store.write("requests.json", ledger)
            self.store.write("latest.json", result)
            print(json.dumps(result, indent=2), flush=True)
            if result["Status"] != "SUCCESS":
                raise WorkerRefreshError(
                    "Refresh request failed or was rejected. Read Files/ForecastMasterRefreshState/latest.json; a new button click submits a retry."
                )
            return engine, result
        finally:
            self.store.release()
