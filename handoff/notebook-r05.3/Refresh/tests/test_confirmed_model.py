from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "source"))
from confirmed_model import refresh_confirmed_model

NOW = datetime(2026, 10, 19, 12, 0, tzinfo=UTC)
CONFIG = {
    "WORKSPACE_ID": str(uuid4()),
    "SEMANTIC_MODEL_ID": str(uuid4()),
    "MODEL_REFRESH_TIMEOUT_SECONDS": 8,
}
OLD, NEW, OTHER = str(uuid4()), str(uuid4()), str(uuid4())


def row(
    identity, status="Completed", start="2026-10-19T12:00:01Z", kind="ViaEnhancedApi"
):
    return {
        "requestId": identity,
        "status": status,
        "startTime": start,
        "refreshType": kind,
    }


class Response:
    def __init__(self, code=200, body=None, headers=None):
        self.status_code, self.body, self.headers = code, body or {}, headers or {}
        self.text = str(self.body)

    def json(self):
        return self.body


class Http:
    def __init__(self, histories, headers=None, detail=None, post_status=202):
        self.histories = list(histories)
        self.last = self.histories[-1]
        self.headers, self.detail, self.post_status = headers or {}, detail, post_status
        self.posts, self.urls = [], []

    def post(self, url, **kwargs):
        self.posts.append(kwargs)
        headers = self.headers.copy()
        if headers.get("Location") == "SELF":
            headers["Location"] = url + "/" + NEW
        return Response(self.post_status, headers=headers)

    def get(self, url, **kwargs):
        self.urls.append(url)
        if url.endswith("/" + NEW):
            return self.detail or Response(body={"status": "Completed"})
        if self.histories:
            self.last = self.histories.pop(0)
        return Response(body={"value": self.last})


def call(http):
    ticks = [0.0]

    def sleep(seconds):
        ticks[0] += seconds

    return refresh_confirmed_model(
        CONFIG,
        lambda audience: "test",
        http=http,
        now=lambda: NOW,
        clock=lambda: ticks[0],
        sleep=sleep,
    )


def test_missing_headers_confirm_new_api_refresh_and_never_use_old_completed_row():
    old = row(OLD, start="2026-10-19T11:00:00Z")
    http = Http(
        [[old], [old], [row(NEW, "Unknown"), old], [row(NEW), old], [row(NEW), old]]
    )
    result = call(http)
    assert result["Status"] == "COMPLETED"
    assert result["RequestID"] == NEW
    assert result["Confirmation"] == "FreshAPIHistorySoleWriter"
    assert len(http.posts) == 1
    assert "notifyOption" not in http.posts[0]["json"]


def test_stale_completed_history_cannot_clear_pending_refresh():
    result = call(Http([[row(OLD, start="2026-10-19T11:00:00Z")]]))
    assert result["Status"] == "PENDING"


def test_unseen_old_entry_and_on_demand_refresh_are_not_a_match():
    result = call(
        Http(
            [[], [row(NEW, start="2026-10-19T11:00:00Z"), row(OTHER, kind="OnDemand")]]
        )
    )
    assert result["Status"] == "PENDING"


def test_multiple_new_api_refreshes_remain_unconfirmed():
    assert call(Http([[], [row(NEW), row(OTHER)]]))["Status"] == "ACCEPTED_UNCONFIRMED"


def test_exact_operation_location_confirms_direct_result():
    result = call(Http([[]], headers={"Location": "SELF"}))
    assert result == {
        "Status": "COMPLETED",
        "RequestID": NEW,
        "Confirmation": "OperationURL",
    }


def test_unknown_location_does_not_receive_authorization_header():
    http = Http(
        [[], [row(NEW)], [row(NEW)]],
        headers={"Location": "https://example.invalid/other"},
    )
    assert call(http)["Status"] == "COMPLETED"
    assert all(url.startswith("https://api.powerbi.com/") for url in http.urls)


def test_request_id_match_beats_unrelated_api_history():
    result = call(Http([[], [row(NEW), row(OTHER)]], headers={"x-ms-request-id": NEW}))
    assert result["RequestID"] == NEW
    assert result["Confirmation"] == "RequestID"


def test_api_refusal_and_actual_failure_are_not_completion():
    with pytest.raises(RuntimeError, match="rejected"):
        call(Http([[]], post_status=403))
    with pytest.raises(RuntimeError, match="Failed"):
        call(Http([[], [row(NEW, "Failed")]]))


def test_server_date_is_used_when_notebook_clock_is_ahead():
    http = Http(
        [[], [row(NEW)], [row(NEW)]], headers={"Date": "Mon, 19 Oct 2026 12:00:00 GMT"}
    )
    result = refresh_confirmed_model(
        CONFIG,
        lambda audience: "test",
        http=http,
        now=lambda: datetime(2030, 1, 1, tzinfo=UTC),
        sleep=lambda seconds: None,
    )
    assert result["Status"] == "COMPLETED"
