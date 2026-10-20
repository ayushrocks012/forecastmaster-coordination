"""Refresh the existing semantic model after successful reporting commits; never publish a model."""

from __future__ import annotations

import re
import time
from collections.abc import Callable
from typing import Any
from urllib.parse import urlparse

import requests


def refresh_model(
    config: dict[str, Any],
    get_token: Callable[[str], str],
    *,
    http: Any = requests,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> dict[str, str]:
    if not config.get("REFRESH_SEMANTIC_MODEL", True):
        return {
            "Status": "MANUAL",
            "Message": "Refresh ForecastMaster Demand Model, then refresh Power BI Desktop.",
        }
    workspace, dataset = config["WORKSPACE_ID"], config["SEMANTIC_MODEL_ID"]
    if any(not re.fullmatch(r"[0-9a-fA-F-]{36}", x) for x in (workspace, dataset)):
        raise ValueError("Workspace and semantic-model IDs must be UUIDs")
    base = f"https://api.powerbi.com/v1.0/myorg/groups/{workspace}/datasets/{dataset}/refreshes"
    headers = {
        "Authorization": "Bearer " + get_token("pbi"),
        "Content-Type": "application/json",
    }
    response = http.post(
        base,
        headers=headers,
        json={"type": "automatic", "commitMode": "transactional", "retryCount": 1},
        timeout=45,
    )
    if response.status_code not in {200, 202}:
        raise RuntimeError(
            f"Semantic-model refresh not accepted (HTTP {response.status_code}): {response.text[:1200]}. Data tables are retained; refresh the existing model manually."
        )
    location = response.headers.get("Location", "")
    request_id = response.headers.get("x-ms-request-id", "")
    if not location and request_id:
        location = base + "/" + request_id
    parsed = urlparse(location)
    if (
        parsed.scheme != "https"
        or parsed.netloc != "api.powerbi.com"
        or not location.startswith(base + "/")
    ):
        return {
            "Status": "ACCEPTED_UNCONFIRMED",
            "Message": "Refresh was accepted; check model refresh history before refreshing the report.",
        }
    deadline = clock() + config.get("MODEL_REFRESH_TIMEOUT_SECONDS", 180)
    while clock() < deadline:
        state = http.get(location, headers=headers, timeout=45)
        if state.status_code not in {200, 202}:
            raise RuntimeError(
                f"Cannot confirm semantic-model refresh (HTTP {state.status_code}): {state.text[:1000]}"
            )
        status = state.json().get("status", "Unknown")
        if status == "Completed":
            return {"Status": "COMPLETED", "RequestID": request_id}
        if status in {"Failed", "Cancelled", "Disabled", "TimedOut"}:
            raise RuntimeError(
                "Semantic-model refresh ended with " + status + ": " + state.text[:1200]
            )
        sleep(2)
    return {
        "Status": "PENDING",
        "RequestID": request_id,
        "Message": "Accepted refresh is still running. Check model refresh history; rerunning ingestion is unnecessary.",
    }
