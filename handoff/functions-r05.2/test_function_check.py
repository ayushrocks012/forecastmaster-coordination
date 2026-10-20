"""Capability-check tests: paging, admission, missing metadata and failures."""

import importlib.util
import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

spec = importlib.util.spec_from_file_location(
    "function_app", Path(__file__).with_name("function_app.py")
)
assert spec and spec.loader
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)

NAME = "UK_Core Oral_Bridge_Oct 26_EF-Sep 26_IMS-Aug 26_V21 scenario.xlsm"
ROOT = "lakehouse-id/Files/Demand"


def row(name: str = NAME, **kwargs: Any) -> Any:
    return SimpleNamespace(
        **{
            "name": ROOT + "/2026/October/" + name,
            "is_directory": False,
            "content_length": 0,
            "last_modified": datetime(2026, 10, 19, tzinfo=UTC),
            "etag": '"version-1"',
            **kwargs,
        }
    )


class Directory:
    path_name = ROOT

    def __init__(self, pages: list[list[Any]], error: bool = False):
        self.pages, self.error = pages, error
        self.visited_pages = 0
        self.children: dict[str, Directory] = {}
        self.closed = False

    def get_paths(self, **kwargs: Any) -> Any:
        assert kwargs["recursive"] is False
        for page in self.pages:
            self.visited_pages += 1
            yield from page
        if self.error:
            raise OSError("Provider failed after first page")

    def get_sub_directory_client(self, relative: str) -> Any:
        child = self.children.get(relative, Directory([]))
        child.path_name = ROOT + "/" + relative
        return child

    def close(self) -> None:
        self.closed = True


def test_follows_all_pages_and_never_downloads_contents() -> None:
    other = row(content_length=53)
    other.name = ROOT + "/another/" + NAME
    directory = Directory([[row()], [other]])
    result = app.inspectMetadata(directory)
    assert directory.visited_pages == 2
    assert result["MatchingBridgeFiles"] == 2
    assert result["Status"] == "METADATA_VISIBLE"
    assert result["Files"][0]["Bytes"] == 0
    assert result["WorkbookContentsRead"] is False


@pytest.mark.parametrize(
    "name", ["~$" + NAME, "refresh-example.json", "not-a-bridge.xlsm", NAME + ".bak"]
)
def test_rejects_non_bridge_names(name: str) -> None:
    assert app.inspectMetadata(Directory([[row(name)]]))["MatchingBridgeFiles"] == 0


def test_skips_directories() -> None:
    assert (
        app.inspectMetadata(Directory([[row(is_directory=True)]]))[
            "MatchingBridgeFiles"
        ]
        == 0
    )


@pytest.mark.parametrize(
    "missing", [{"etag": None}, {"last_modified": None}, {"content_length": None}]
)
def test_missing_metadata_is_explicit(missing: dict[str, Any]) -> None:
    result = app.inspectMetadata(Directory([[row(**missing)]]))
    assert result["Status"] == "METADATA_INCOMPLETE"
    assert len(result["MissingMetadataPaths"]) == 1


def test_partial_listing_raises_instead_of_reporting_complete() -> None:
    with pytest.raises(OSError, match="Provider failed"):
        app.inspectMetadata(Directory([[row()]], error=True))


def test_case_collisions_fail() -> None:
    with pytest.raises(ValueError, match="Duplicate file identity"):
        app.inspectMetadata(Directory([[row(), row(NAME.upper())]]))


def test_outside_path_fails() -> None:
    other = row()
    other.name = "other/Files/Demand/" + NAME
    with pytest.raises(ValueError, match="outside"):
        app.inspectMetadata(Directory([[other]]))


def test_sdk_naive_datetime_represents_service_utc() -> None:
    result = app.inspectMetadata(
        Directory([[row(last_modified=datetime(2026, 10, 19))]])
    )
    assert result["Files"][0]["ModifiedAtUtc"] == "2026-10-19T00:00:00+00:00"


@pytest.mark.parametrize(
    "modified",
    [
        "Mon, 19 Oct 2026 12:00:00 GMT",
        "2026-10-19T12:00:00Z",
        "2026-10-19T13:00:00+01:00",
    ],
)
def test_sdk_string_timestamps_are_normalized(modified: str) -> None:
    result = app.inspectMetadata(Directory([[row(last_modified=modified)]]))
    assert result["Files"][0]["ModifiedAtUtc"] == "2026-10-19T12:00:00+00:00"


@pytest.mark.parametrize("modified", ["2026-10-19T12:00:00", "nonsense"])
def test_naive_or_invalid_sdk_string_timestamp_fails(modified: str) -> None:
    with pytest.raises(ValueError):
        app.inspectMetadata(Directory([[row(last_modified=modified)]]))


def test_empty_listing_is_not_mistaken_for_verified_access() -> None:
    result = app.inspectMetadata(Directory([]))
    assert result["Status"] == "METADATA_INCOMPLETE"


def test_deployed_sdk_registers_connection_and_function() -> None:
    assert app.udf is not None
    assert hasattr(app, "checkDemandAccessR04")


def test_elapsed_budget_fails_incomplete_listing(monkeypatch: Any) -> None:
    ticks = iter([0, 71])
    monkeypatch.setattr(app.time, "monotonic", lambda: next(ticks))
    with pytest.raises(RuntimeError, match="incomplete"):
        app.inspectMetadata(Directory([[row()]]))


def test_real_sdk_directory_and_path_properties(monkeypatch: Any) -> None:
    """Use the real client shape; only the service listing is substituted."""
    from azure.storage.filedatalake import DataLakeDirectoryClient, PathProperties

    files = DataLakeDirectoryClient(
        account_url="https://onelake.dfs.fabric.microsoft.com",
        file_system_name="synthetic-workspace",
        directory_name="lakehouse-id/Files",
    )
    demand = files.get_sub_directory_client("Demand")
    try:
        assert not hasattr(demand, "directory_name")
        assert demand.path_name == ROOT
        item = PathProperties(**vars(row()))
        monkeypatch.setattr(demand, "get_paths", lambda **kwargs: iter([item]))
        result = app.inspectMetadata(demand)
        assert result["Status"] == "METADATA_VISIBLE"
        assert result["MatchingBridgeFiles"] == 1
        assert result["Files"][0] == {
            "Path": "2026/October/" + NAME,
            "Bytes": 0,
            "ModifiedAtUtc": "2026-10-19T00:00:00+00:00",
            "ETag": '"version-1"',
        }
    finally:
        demand.close()
        files.close()


def test_real_sdk_paging_via_local_http_transport() -> None:
    """Run the real SDK listing and deserializer; no network or workbook reads."""
    from azure.core.pipeline.transport import HttpResponse, HttpTransport
    from azure.storage.filedatalake import DataLakeDirectoryClient

    class Response(HttpResponse):
        def __init__(self, request: Any, page: int):
            super().__init__(request, None)
            self.status_code = 200
            self.headers = {"Content-Type": "application/json"}
            self.content_type = "application/json"
            if page == 0:
                self.headers["x-ms-continuation"] = "second-page"
            self.payload = {
                "paths": [
                    {
                        "name": ROOT + f"/folder-{page}/" + NAME,
                        "isDirectory": False,
                        "contentLength": str(page),
                        "lastModified": "Mon, 19 Oct 2026 12:00:00 GMT",
                        "etag": f'"version-{page}"',
                    }
                ]
            }

        def body(self) -> bytes:
            return json.dumps(self.payload).encode()

    class Transport(HttpTransport):
        def __init__(self) -> None:
            self.requests: list[Any] = []

        def open(self) -> None:
            pass

        def close(self) -> None:
            pass

        def __enter__(self) -> Any:
            return self

        def __exit__(self, *args: object) -> None:
            pass

        def send(self, request: Any, **kwargs: Any) -> Response:
            assert request.method == "GET"
            assert "resource=filesystem" in request.url
            page = len(self.requests)
            assert page < 2, "Unexpected additional service request"
            if page == 1:
                assert "continuation=second-page" in request.url
            self.requests.append(request)
            return Response(request, page)

    transport = Transport()
    client = DataLakeDirectoryClient(
        account_url="https://onelake.dfs.fabric.microsoft.com",
        file_system_name="synthetic-workspace",
        directory_name=ROOT,
        transport=transport,
    )
    try:
        result = app.inspectMetadata(client)
        assert result["Status"] == "METADATA_VISIBLE"
        assert result["CompleteDirectoryListing"] is True
        assert result["MatchingBridgeFiles"] == 2
        assert result["WorkbookContentsRead"] is False
        assert len(transport.requests) == 2
    finally:
        client.close()


def test_explicit_walk_reaches_nested_bridges_and_other_years() -> None:
    def folder(relative: str) -> Any:
        value = row(is_directory=True)
        value.name = ROOT + "/" + relative
        return value

    root = Directory([[folder("2026"), folder("2028")]])
    year = Directory([[folder("2026/10 Oct 26")]])
    month = Directory([[folder("2026/10 Oct 26/Bridge Files")]])
    bridge = row()
    bridge.name = ROOT + "/2026/10 Oct 26/Bridge Files/" + NAME
    bridge_folder = Directory([[bridge]])
    future = row("UK_Paed SIP_Bridge_Jul 28_EF-Jun 28_IMS-May 28_V99.xlsx")
    future.name = ROOT + "/2028/" + future.name.rsplit("/", 1)[-1]
    future_year = Directory([[future]])
    root.children.update(
        {
            "2026": year,
            "2028": future_year,
            "2026/10 Oct 26": month,
            "2026/10 Oct 26/Bridge Files": bridge_folder,
        }
    )
    result = app.inspectMetadata(root)
    assert result["Status"] == "METADATA_VISIBLE"
    assert result["MatchingBridgeFiles"] == 2
    assert result["DirectoriesListed"] == 5
    assert result["EntriesFound"] == 6
    assert all(child.closed for child in root.children.values())
    assert not root.closed


def test_failed_nested_folder_does_not_report_complete() -> None:
    folder = row(is_directory=True)
    folder.name = ROOT + "/2026"
    root = Directory([[folder]])
    child = Directory([], error=True)
    root.children["2026"] = child
    with pytest.raises(OSError, match="Provider failed"):
        app.inspectMetadata(root)
    assert child.closed
