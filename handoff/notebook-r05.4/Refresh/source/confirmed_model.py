"""Confirm a model refresh using its operation URL or fresh API history.

History fallback assumes this worker is the sole API refresh writer. It never
accepts a baseline row, an earlier start time, or multiple fresh API requests.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import urlparse
from uuid import UUID

import requests


def model_history_key(row: dict[str, Any]) -> str:
    return str(row.get("requestId") or row.get("id") or "")


def model_start_time(value: Any) -> datetime | None:
    try:
        result = datetime.fromisoformat(str(value))
        return result.astimezone(UTC) if result.tzinfo is not None else None
    except (ValueError, TypeError):
        return None


def refresh_confirmed_model(
    config: dict[str, Any],
    get_token: Callable[[str], str],
    *,
    http: Any = requests,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> dict[str, str]:
    if not config.get("REFRESH_SEMANTIC_MODEL", True):
        return {"Status": "MANUAL", "Message": "Semantic-model refresh is disabled."}
    workspace = str(UUID(config["WORKSPACE_ID"]))
    dataset = str(UUID(config["SEMANTIC_MODEL_ID"]))
    base = f"https://api.powerbi.com/v1.0/myorg/groups/{workspace}/datasets/{dataset}/refreshes"

    def headers() -> dict[str, str]:
        return {"Authorization": "Bearer " + get_token("pbi")}

    def history() -> tuple[list[dict[str, Any]], Any]:
        result = http.get(
            base,
            params={"$top": 60},
            headers=headers(),
            timeout=45,
            allow_redirects=False,
        )
        if result.status_code != 200:
            raise RuntimeError(
                f"Cannot read model refresh history (HTTP {result.status_code})."
            )
        rows = result.json().get("value")
        if not isinstance(rows, list) or any(not isinstance(r, dict) for r in rows):
            raise ValueError("Invalid model refresh history response.")
        return rows, result

    baseline, baseline_response = history()
    known = {model_history_key(row) for row in baseline}
    started = now().astimezone(UTC)
    server_date = baseline_response.headers.get("Date")
    if server_date:
        started = parsedate_to_datetime(server_date).astimezone(UTC)
    submitted = http.post(
        base,
        headers={**headers(), "Content-Type": "application/json"},
        json={"type": "automatic", "commitMode": "transactional", "retryCount": 1},
        timeout=45,
        allow_redirects=False,
    )
    if submitted.status_code not in {200, 202}:
        raise RuntimeError(
            f"Semantic-model refresh was rejected (HTTP {submitted.status_code}): {submitted.text[:1000]}"
        )
    # A service timestamp avoids depending on the notebook clock during fallback.
    if submitted.headers.get("Date"):
        started = parsedate_to_datetime(submitted.headers["Date"]).astimezone(UTC)
    location = submitted.headers.get("Location", "")
    operation = ""
    parsed = urlparse(location)
    if (
        parsed.scheme == "https"
        and parsed.netloc == "api.powerbi.com"
        and location.startswith(base + "/")
        and not parsed.query
        and not parsed.fragment
    ):
        tail = location[len(base) + 1 :]
        try:
            operation = str(UUID(tail))
        except ValueError:
            location = ""
    else:
        location = ""
    header_id = submitted.headers.get("x-ms-request-id", "")
    deadline = clock() + float(config.get("MODEL_REFRESH_TIMEOUT_SECONDS", 180))
    previous_candidate = ""
    terminal = {"Failed", "Cancelled", "Canceled", "Disabled", "TimedOut"}
    while clock() < deadline:
        if location:
            detail = http.get(
                location, headers=headers(), timeout=45, allow_redirects=False
            )
            if detail.status_code == 200:
                body = detail.json()
                identity = str(body.get("requestId") or operation)
                if identity != operation:
                    raise ValueError("Model refresh operation identity changed.")
                status = body.get("status", "Unknown")
                if status == "Completed":
                    return {
                        "Status": "COMPLETED",
                        "RequestID": operation,
                        "Confirmation": "OperationURL",
                    }
                if status in terminal:
                    raise RuntimeError(
                        "Semantic-model refresh ended with " + str(status)
                    )
            elif detail.status_code not in {202, 400, 404, 429, 500, 502, 503, 504}:
                raise RuntimeError(
                    f"Cannot confirm model refresh (HTTP {detail.status_code})."
                )
        rows, _ = history()
        correlated = [
            r
            for r in rows
            if model_history_key(r) not in known
            and model_history_key(r) in {operation, header_id} - {""}
        ]
        method = "RequestID"
        if not correlated:
            correlated = [
                r
                for r in rows
                if model_history_key(r)
                and model_history_key(r) not in known
                and r.get("refreshType") in {"ViaApi", "ViaEnhancedApi"}
                and (
                    model_start_time(r.get("startTime"))
                    or datetime.min.replace(tzinfo=UTC)
                )
                >= started
            ]
            method = "FreshAPIHistorySoleWriter"
        if len(correlated) > 1:
            return {
                "Status": "ACCEPTED_UNCONFIRMED",
                "Message": "Multiple fresh API refreshes found. Inspect model history; no request was marked successful.",
            }
        if len(correlated) == 1:
            row = correlated[0]
            identity = model_history_key(row)
            status = row.get("status", "Unknown")
            if status in terminal:
                raise RuntimeError("Semantic-model refresh ended with " + str(status))
            # Require a second observation for fallback correlation.
            if status == "Completed" and (
                method == "RequestID" or identity == previous_candidate
            ):
                return {
                    "Status": "COMPLETED",
                    "RequestID": identity,
                    "Confirmation": method,
                }
            previous_candidate = identity
        sleep(2)
    return {
        "Status": "PENDING",
        "RequestID": operation or header_id,
        "Message": "Model completion was not confirmed within the wait limit. Inspect refresh history.",
    }
