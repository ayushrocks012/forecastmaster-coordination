"""Use actual installed SDK requests, with an in-memory service transport."""

import json
from io import BytesIO
from typing import Any
from urllib.parse import parse_qs, unquote, urlsplit
from uuid import UUID

import pytest
import requests
from azure.core import MatchConditions
from azure.core.exceptions import HttpResponseError, ResourceNotFoundError
from azure.core.pipeline.transport import HttpResponse, HttpTransport, RequestsTransport
from azure.core.utils import CaseInsensitiveDict
from azure.storage.filedatalake import DataLakeDirectoryClient
from requests.adapters import BaseAdapter

from test_function_check import app

STATE = "lakehouse-id/Files/ForecastMasterRefreshState/"
LATEST = STATE + "latest.json"
EXISTING_RECEIPT = b'{"SchemaVersion":1,"Status":"SUCCESS"}'


class Response(HttpResponse):
    def __init__(
        self, request: Any, status: int, body: bytes = b"", **headers: str
    ) -> None:
        super().__init__(request, None)
        self.status_code = status
        self.headers = CaseInsensitiveDict(
            {"Content-Type": "application/json", "Content-Length": str(len(body))}
        )
        self.headers.update(headers)
        self.content_type = self.headers["Content-Type"]
        self.payload = body

    def body(self) -> bytes:
        return self.payload

    def stream_download(self, pipeline: Any, **kwargs: Any) -> Any:
        class Stream:
            def __init__(self, response: Response) -> None:
                self.payload = response.payload
                self.content_length = len(response.payload)
                self.response = response

            def __iter__(self) -> Any:
                return iter([self.payload])

        return Stream(self)


class NativeTransport(HttpTransport):
    def __init__(self) -> None:
        self.contents = {LATEST: EXISTING_RECEIPT}
        self.appended: dict[str, bytes] = {}
        self.etags: dict[str, str] = {}
        self.held: dict[str, str] = {}
        self.requests: list[Any] = []

    def open(self) -> None:
        pass

    def close(self) -> None:
        pass

    def __enter__(self) -> Any:
        return self

    def __exit__(self, *args: object) -> None:
        pass

    def error(self, request: Any, status: int, code: str) -> Response:
        body = json.dumps({"error": {"code": code, "message": code}}).encode()
        return Response(request, status, body, **{"x-ms-error-code": code})

    def send(self, request: Any, **kwargs: Any) -> Response:
        self.requests.append(request)
        url = urlsplit(request.url)
        path = unquote(url.path).split("/", 2)[2]
        assert path.startswith(STATE)
        assert "worker.lock" not in path
        query = parse_qs(url.query)
        if request.method == "GET":
            if path not in self.contents:
                return self.error(request, 404, "PathNotFound")
            payload = self.contents[path]
            return Response(
                request,
                206,
                payload,
                **{
                    "Content-Range": f"bytes 0-{len(payload) - 1}/{len(payload)}",
                    "ETag": self.etags.get(path, '"existing"'),
                },
            )
        if request.method == "PUT" and query.get("resource") == ["file"]:
            assert request.headers.get("If-None-Match") == "*"
            if path in self.contents:
                return self.error(request, 412, "ConditionNotMet")
            self.contents[path] = b""
            self.etags[path] = '"created"'
            return Response(request, 201, ETag=self.etags[path])
        if request.method == "PATCH":
            if path not in self.contents:
                return self.error(request, 404, "PathNotFound")
            if query.get("action") == ["append"]:
                assert query["position"] == ["0"]
                self.appended[path] = bytes(request.body)
                return Response(request, 202)
            assert query.get("action") == ["flush"]
            assert request.headers.get("If-Match") == self.etags[path]
            assert request.headers.get("If-None-Match") is None
            assert query["position"] == [str(len(self.appended[path]))]
            self.contents[path] = self.appended[path]
            self.etags[path] = '"committed"'
            return Response(request, 200, ETag=self.etags[path])
        assert request.method == "PUT" and query.get("comp") == ["lease"]
        assert path in self.contents
        action = request.headers["x-ms-lease-action"]
        if action == "acquire":
            assert request.headers["x-ms-lease-duration"] == "60"
            if path in self.held:
                return self.error(request, 409, "LeaseAlreadyPresent")
            identity = request.headers["x-ms-proposed-lease-id"]
            UUID(identity)
            self.held[path] = identity
            return Response(request, 201, **{"x-ms-lease-id": identity})
        assert request.headers["x-ms-lease-id"] == self.held[path]
        identity = self.held[path]
        if action == "release":
            del self.held[path]
        else:
            assert action == "renew"
        return Response(request, 200, **{"x-ms-lease-id": identity})


class LoopbackAdapter(BaseAdapter):
    """Run the real requests.Session.request validation without a network."""

    def __init__(self, service: NativeTransport):
        super().__init__()
        self.service = service

    def close(self) -> None:
        pass

    def send(
        self,
        request: Any,
        stream: bool = False,
        timeout: Any = None,
        verify: Any = True,
        cert: Any = None,
        proxies: Any = None,
    ) -> requests.Response:
        simulated = self.service.send(request)
        response = requests.Response()
        response.status_code = simulated.status_code
        response.headers = requests.structures.CaseInsensitiveDict(simulated.headers)
        response._content = simulated.payload
        response.raw = BytesIO(simulated.payload)
        response.request = request
        response.url = request.url
        return response


def client(transport: NativeTransport) -> DataLakeDirectoryClient:
    session = requests.Session()
    session.trust_env = False
    session.mount("https://", LoopbackAdapter(transport))
    return DataLakeDirectoryClient(
        account_url="https://onelake.dfs.fabric.microsoft.com",
        file_system_name="synthetic-workspace",
        directory_name="lakehouse-id/Files",
        transport=RequestsTransport(session=session, session_owner=True),
        retry_total=0,
    )


def test_original_nonoverwrite_upload_reproduces_missing_path() -> None:
    transport = NativeTransport()
    with (
        client(transport) as root,
        root.get_file_client("ForecastMasterRefreshState/probe-missing.json") as probe,
        pytest.raises(ResourceNotFoundError) as failure,
    ):
        probe.upload_data(b"{}", overwrite=False)
    assert failure.value.error_code == "PathNotFound"
    assert [request.method for request in transport.requests] == ["PATCH"]


def test_previous_etag_argument_reproduces_the_exact_requests_type_error() -> None:
    transport = NativeTransport()
    with (
        client(transport) as root,
        root.get_file_client("ForecastMasterRefreshState/probe-etag.json") as probe,
        pytest.raises(TypeError, match="unexpected keyword argument 'etag'"),
    ):
        probe.upload_data(
            b"{}", overwrite=True, etag="*", match_condition=MatchConditions.IfMissing
        )
    assert transport.requests == []


def test_real_sdk_probe_creates_before_upload_then_leases_and_releases() -> None:
    transport = NativeTransport()
    with client(transport) as root:
        result = app.verifyNativeState(root)
    assert result["CodeVersion"] == "R05.2"
    assert result["Status"] == "NATIVE_STATE_READY"
    assert [request.method for request in transport.requests] == [
        "GET",
        "PUT",
        "PATCH",
        "PATCH",
        "GET",
        "PUT",
        "PUT",
        "PUT",
        "PUT",
    ]
    assert transport.contents[LATEST] == EXISTING_RECEIPT
    assert len(transport.contents) == 2 and transport.held == {}
    probe = next(path for path in transport.contents if path != LATEST)
    assert json.loads(transport.contents[probe])["Purpose"]


def test_create_condition_preserves_an_existing_probe(monkeypatch: Any) -> None:
    identity = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
    monkeypatch.setattr(app, "uuid4", lambda: identity)
    transport = NativeTransport()
    old = STATE + "probe-" + str(identity) + ".json"
    transport.contents[old] = b"existing information"
    with client(transport) as root, pytest.raises(HttpResponseError):
        app.verifyNativeState(root)
    assert transport.contents[old] == b"existing information"
    assert [request.method for request in transport.requests] == ["GET", "PUT"]
