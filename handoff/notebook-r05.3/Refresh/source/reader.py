"""Read current V18 saved bridge values without an intermediate Excel Master."""

from __future__ import annotations

import hashlib
import io
import json
import math
import posixpath
import re
from collections.abc import Iterator, Mapping, Sequence
from datetime import date
from typing import TYPE_CHECKING, Any
from urllib.parse import unquote
from zipfile import ZipFile

from defusedxml.ElementTree import fromstring, iterparse

if TYPE_CHECKING:
    from xml.etree.ElementTree import (
        # annotation only; all parsing uses defusedxml.
        Element,  # nosec B405
    )

CONTRACT = "V18-explicit-profile-and-context-v2|legacy-metadata-compat-v1"
NS = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
RID = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
IDS = (
    "Channel",
    "Sub Channel",
    "Sector",
    "Manufacturer",
    "Product",
    "Section",
    "Measure",
)
MONTHS = (
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
)
LONG_MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)
SECTION_ALIASES = {
    "Ex-Factory": "Sub Channel - Exfactory",
    "Ex-Factory - New Contracts": "Sub Channel - Exfactory - New Contracts",
    "Ex-Factory - Shipment Adjustments": "Sub Channel - Exfactory - Shipment Adjustments",
}
WORKDAYS = {"Working days in month", "Working days in month (value)", "Working days"}


def measure_key(section: str, measure: str) -> str:
    """Keep source measure identity independent of its editable display label."""
    value = json.dumps([section, measure], ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(value.encode()).hexdigest()


def folder_identity(relative_path: str) -> tuple[str, str]:
    """Use the agreed filename cycle anywhere under Demand; folders are not admission rules."""
    filename = unquote(relative_path).replace("\\", "/").rsplit("/", 1)[-1]
    month = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{2}"
    match = re.fullmatch(
        rf"[^_]+_.+?_Bridge_(?P<cycle>{month})_EF-{month}_IMS-{month}_.+\.(?:xlsx|xlsm)",
        filename,
        re.IGNORECASE,
    )
    if match is None or filename.startswith("~$"):
        raise ValueError("Filename is outside the agreed bridge naming convention")
    label, year = match["cycle"].split(" ")
    number = next(
        i for i, name in enumerate(MONTHS, 1) if name.casefold() == label.casefold()
    )
    return f"{2000 + int(year):04d}-{number:02d}", ""


def folder_cycle(relative_path: str) -> str:
    """Compatibility name: the cycle now comes from the filename, never a folder."""
    return folder_identity(relative_path)[0]


def relationships(package: ZipFile, owner: str) -> dict[str, str]:
    """Resolve the workbook's internal sheet and table parts."""
    folder, name = posixpath.split(owner)
    path = f"{folder}/_rels/{name}.rels"
    if path not in package.namelist():
        return {}
    return {
        node.attrib["Id"]: node.attrib["Target"].lstrip("/")
        if node.attrib["Target"].startswith("/")
        else posixpath.normpath(posixpath.join(folder, node.attrib["Target"]))
        for node in fromstring(package.read(path))
        if node.attrib.get("TargetMode") != "External"
    }


def column_number(address: str) -> int:
    """Translate an OOXML cell address to a one-based column."""
    result = 0
    for char in "".join(c for c in address if c.isalpha()).upper():
        result = result * 26 + ord(char) - 64
    return result


def cached_value(cell: Element | None, strings: Sequence[str]) -> dict[str, Any]:
    """Preserve saved cache type, formula, blank and true numeric zero."""
    node = cell.find("s:v", NS) if cell is not None else None
    formula = cell.find("s:f", NS) if cell is not None else None
    value = node.text if node is not None else None
    result: dict[str, Any] = {
        "kind": "blank",
        "raw": None,
        "number": None,
        "text": None,
        "boolean": None,
        "formula": None if formula is None else (formula.text or ""),
        "cache_state": "absent"
        if node is None
        else "empty"
        if value in {None, ""}
        else "present",
    }
    kind = cell.get("t", "n") if cell is not None else "n"
    if kind == "e":
        raise ValueError("Cached Excel error: " + str(value))
    if kind == "inlineStr" and cell is not None:
        inline = cell.find("s:is", NS)
        value = "".join(inline.itertext()) if inline is not None else ""
        kind = "str"
    if value in {None, ""}:
        return result
    return _typed_cache(result, kind, str(value), strings)


def _typed_cache(
    result: dict[str, Any], kind: str, value: str, strings: Sequence[str]
) -> dict[str, Any]:
    """Decode a nonempty saved value without broad null/zero coercion."""
    if kind in {"s", "str", "d"}:
        text = strings[int(value)] if kind == "s" else value
        if text:
            result.update(kind="date" if kind == "d" else "text", raw=text, text=text)
    elif kind == "b":
        if value not in {"0", "1"}:
            raise ValueError("Invalid cached boolean")
        result.update(kind="bool", raw=value, boolean=value == "1")
    else:
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("Nonfinite cached number")
        result.update(kind="number", raw=value, number=number)
    return result


def explicit_metadata(book: Element, cycle: str, folder_profile: str) -> dict[str, str]:
    """Read saved identities; normalize legacy profile tags while retaining original names."""
    definitions = {
        n.attrib["name"]: n.text or ""
        for n in book.findall("s:definedNames/s:definedName", NS)
    }
    named = {}
    for key, value in definitions.items():
        literal = value.removeprefix("=")
        if (
            key.startswith("Bridge_")
            and literal.startswith('"')
            and literal.endswith('"')
        ):
            named[key.removeprefix("Bridge_")] = literal[1:-1].replace('""', '"')
    required = (
        "Country",
        "GrowthDriver",
        "Cycle",
        "BridgeRevision",
        "SourceProfile",
        "PublicationStatus",
        "ExFactoryActualsThrough",
        "IMSActualsThrough",
    )
    missing = [key for key in required if not named.get(key)]
    if missing:
        raise ValueError("Missing explicit workbook metadata: " + ", ".join(missing))
    raw_profile = named["SourceProfile"]
    legacy = re.fullmatch(r"V[0-9]+(?P<ext>_Ext)?", raw_profile, re.IGNORECASE)
    if legacy is not None:
        named["SourceProfile"] = "Ext" if legacy["ext"] else "Local"
        if "Bridge_PublicationOrigin" not in definitions:
            # Explicitly unavailable; this does not manufacture publication provenance.
            named["PublicationOrigin"] = "NOT_RECORDED"
    if not named.get("PublicationOrigin"):
        raise ValueError("Missing explicit workbook metadata: PublicationOrigin")
    if named["Cycle"] != cycle or named["SourceProfile"] not in {"Local", "Ext"}:
        raise ValueError("Workbook cycle/profile differs from source scope")
    if folder_profile and named["SourceProfile"] != folder_profile:
        raise ValueError("Workbook profile differs from V18/V18_Ext subfolder")
    for key in ("ExFactoryActualsThrough", "IMSActualsThrough"):
        date.fromisoformat(named[key])
        if named[key][:7] >= cycle:
            raise ValueError("Actuals cutoff is not before the forecast cycle")
    version = {"DEVELOPMENT": "Dev", "PUBLISHED": "ADS"}.get(
        named["PublicationStatus"], "UNKNOWN"
    )
    return {
        **named,
        "DemandCycle": cycle,
        "Version": version,
        "Revision": named["BridgeRevision"],
        "PreviousPublication": named.get("PreviousPublication", ""),
        "DefinedNamesJson": json.dumps(definitions, ensure_ascii=False),
        "Contract": CONTRACT,
    }


def context_role(section: str, measure: str) -> str:
    """Keep the upgraded Master's calendar, controls and saved quality observable."""
    if measure in WORKDAYS:
        return "Calendar"
    if measure == "Residual Product" or (
        section
        in {"Ex-Factory - New Contracts", "Sub Channel - Exfactory - New Contracts"}
        and re.fullmatch(r"Contract \d+ (Litres|Pounds)", measure)
    ):
        return "Model Control"
    if section == "Product reconciliation checks" or (section, measure) == (
        "Pricing",
        "Status",
    ):
        return "Data Quality"
    return "Observation"


class BridgeReader:
    """Stream the current integrated source tables from one saved bridge."""

    def __init__(self, content: bytes, relative_path: str) -> None:
        """Keep source bytes and scope separate from business publication approval."""
        self.content = content
        self.relative_path = unquote(relative_path)
        self.sha256 = hashlib.sha256(content).hexdigest()
        self.cycle, self.folder_profile = folder_identity(relative_path)
        self.metadata: dict[str, str] = {}
        self.row_count = 0
        self.observation_count = 0
        self.type_counts: dict[str, int] = {}
        self.calendar: tuple[float | None, ...] | None = None

    def rows(self) -> Iterator[dict[str, Any]]:
        """Read every labelled row and month; never apply a fixed measure allowlist."""
        with ZipFile(io.BytesIO(self.content)) as package:
            book = fromstring(package.read("xl/workbook.xml"))
            self.metadata = explicit_metadata(book, self.cycle, self.folder_profile)
            strings = self._strings(package)
            parts = relationships(package, "xl/workbook.xml")
            seen: set[tuple[str, ...]] = set()
            horizon: list[str] | None = None
            tables = 0
            for sheet in book.findall("s:sheets/s:sheet", NS):
                part = parts[sheet.attrib[RID]]
                table = self._model_table(package, part)
                if table is None:
                    continue
                tables += 1
                headers = [
                    n.attrib["name"]
                    for n in table.findall("s:tableColumns/s:tableColumn", NS)
                ]
                dates = _month_dates(headers)
                if horizon is not None and horizon != headers[7:]:
                    raise ValueError("Sector month horizons differ")
                horizon = headers[7:]
                yield from self._sheet_rows(
                    package,
                    part,
                    table,
                    sheet.attrib["name"],
                    headers,
                    dates,
                    strings,
                    seen,
                )
            if not tables or self.calendar is None:
                raise ValueError(
                    "Missing SectorModel tables or source working-day calendar"
                )

    @staticmethod
    def _strings(package: ZipFile) -> list[str]:
        """Read shared strings with their original text."""
        if "xl/sharedStrings.xml" not in package.namelist():
            return []
        return [
            "".join(n.itertext())
            for n in fromstring(package.read("xl/sharedStrings.xml")).findall(
                "s:si", NS
            )
        ]

    @staticmethod
    def _model_table(package: ZipFile, part: str) -> Element | None:
        """Locate one integrated sector table without depending on sheet order."""
        models = []
        for target in relationships(package, part).values():
            if target.startswith("xl/tables/") and target.endswith(".xml"):
                table = fromstring(package.read(target))
                if re.fullmatch(r"SectorModel\d+", table.attrib.get("name", "")):
                    models.append(table)
        if len(models) > 1:
            raise ValueError("Expected one integrated table per sector")
        return models[0] if models else None

    def _sheet_rows(
        self,
        package: ZipFile,
        part: str,
        table: Element,
        sheet: str,
        headers: list[str],
        dates: list[str],
        strings: list[str],
        seen: set[tuple[str, ...]],
    ) -> Iterator[dict[str, Any]]:
        """Stream saved rows within the named table bounds."""
        first, last = table.attrib["ref"].split(":")
        first_col = column_number(first)
        first_row, last_row = (int(re.sub(r"\D", "", p)) for p in (first, last))
        if column_number(last) - first_col + 1 != len(headers):
            raise ValueError("Table width differs from headers")
        with package.open(part) as stream:
            for _, row in iterparse(stream, events=("end",)):
                if row.tag != "{" + NS["s"] + "}row":
                    continue
                ordinal = int(row.attrib["r"])
                if first_row < ordinal <= last_row:
                    cells = {column_number(c.attrib["r"]): c for c in row}
                    values = [
                        cached_value(cells.get(first_col + i), strings)
                        for i in range(len(headers))
                    ]
                    ids = tuple(
                        ""
                        if c["kind"] == "blank"
                        else str(c["text"] if c["kind"] == "text" else c["raw"])
                        for c in values[:7]
                    )
                    if ids[5] or ids[6]:
                        _check_identity(ids, sheet, seen)
                        months = self._months(headers[7:], dates, values[7:])
                        self._check_context(ids, values[7:])
                        self.row_count += 1
                        yield {
                            "sheet": sheet,
                            "table": table.attrib["name"],
                            "row": ordinal,
                            "ids": ids,
                            "months": months,
                            "metadata": self.metadata,
                            "context_role": context_role(ids[5], ids[6]),
                        }
                row.clear()

    def _months(
        self, labels: list[str], dates: list[str], values: list[dict[str, Any]]
    ) -> list[tuple[Any, ...]]:
        """Expand explicit month observations while retaining every null month."""
        result = []
        for label, day, value in zip(labels, dates, values, strict=True):
            result.append(
                (
                    day,
                    label,
                    value["kind"],
                    value["raw"],
                    value["number"],
                    value["text"],
                    value["boolean"],
                    value["formula"],
                    value["cache_state"],
                )
            )
            self.observation_count += 1
            kind = value["kind"]
            self.type_counts[kind] = self.type_counts.get(kind, 0) + 1
        return result

    def _check_context(
        self, ids: tuple[str, ...], values: list[dict[str, Any]]
    ) -> None:
        """Validate source calendar equality and structural residual selectors."""
        if ids[6] == "Residual Product" and any(v["kind"] != "blank" for v in values):
            raise ValueError("Residual selector gained monthly values")
        if ids[6] in WORKDAYS:
            if any(v["kind"] not in {"number", "blank"} for v in values):
                raise ValueError("Working-day calendar contains a nonnumeric value")
            current = tuple(v["number"] for v in values)
            if self.calendar is not None and self.calendar != current:
                raise ValueError("Repeated source working days differ")
            self.calendar = current


def _check_identity(
    ids: tuple[str, ...], sheet: str, seen: set[tuple[str, ...]]
) -> None:
    """Reject incomplete or duplicate business identities instead of summing them."""
    if not ids[5] or not ids[6] or ids[2] != sheet or ids in seen:
        raise ValueError("Incomplete, wrong-sector or duplicate bridge identity")
    seen.add(ids)


def _month_dates(headers: list[str]) -> list[str]:
    """Accept an extended continuous horizon with the exact seven identity columns."""
    if tuple(headers[:7]) != IDS:
        raise ValueError("Source layout needs an adapter")
    dates = []
    for header in headers[7:]:
        match = re.fullmatch(r"(\d{4})-([A-Za-z]{3})", header)
        if not match or match[2] not in MONTHS:
            raise ValueError("Unknown model month header: " + header)
        dates.append(date(int(match[1]), MONTHS.index(match[2]) + 1, 1).isoformat())
    ordinal = [int(d[:4]) * 12 + int(d[5:7]) for d in dates]
    if not ordinal or ordinal != list(range(ordinal[0], ordinal[0] + len(ordinal))):
        raise ValueError("Model month horizon is not continuous")
    return dates


def normalize_catalog(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    """Validate user-editable definitions without changing original measure identities."""
    normalized = []
    intervals: dict[str, list[tuple[str, str]]] = {}
    for original in rows:
        section, measure = original.get("SourceSection"), original.get("SourceMeasure")
        if (
            not isinstance(section, str)
            or not isinstance(measure, str)
            or not section
            or not measure
        ):
            raise ValueError("Catalog needs exact SourceSection and SourceMeasure")
        row = {k: "" if v is None else str(v) for k, v in original.items()}
        key = measure_key(section, measure)
        enabled = row.get("ReportingEnabled", "true").lower()
        if enabled not in {"true", "false"}:
            raise ValueError("ReportingEnabled must be true or false")
        lower, upper = _effective_range(row)
        if any(max(lower, a) <= min(upper, b) for a, b in intervals.get(key, [])):
            raise ValueError("Catalog effective ranges overlap")
        intervals.setdefault(key, []).append((lower, upper))
        row.update(
            MeasureKey=key,
            ReportingEnabled=enabled,
            EffectiveFromCycle=lower,
            EffectiveToCycle=upper,
            DisplayName=row.get("DisplayName") or measure,
            RawConfigurationJson=json.dumps(
                dict(original), ensure_ascii=False, sort_keys=True, default=str
            ),
        )
        normalized.append(row)
    return normalized


def _effective_range(row: Mapping[str, str]) -> tuple[str, str]:
    """Require real, ordered year/month bounds for a reporting definition."""
    result = []
    for field, fallback in (
        ("EffectiveFromCycle", "0001-01"),
        ("EffectiveToCycle", "9999-12"),
    ):
        value = row.get(field) or fallback
        if not re.fullmatch(r"\d{4}-\d{2}", value):
            raise ValueError("Invalid effective cycle")
        date(int(value[:4]), int(value[5:]), 1)
        result.append(value)
    if result[0] > result[1]:
        raise ValueError("Effective cycle range is reversed")
    return result[0], result[1]


WIDE_FIELDS = (
    "SourceRevisionID",
    "SourceFileName",
    "SourceRelativePath",
    "SourceSheet",
    "SourceTable",
    "MeasureKey",
    "Country",
    "GrowthDriver",
    "DemandCycle",
    "Version",
    "Revision",
    "ExFactoryActualsThrough",
    "IMSActualsThrough",
    "PublicationStatus",
    "PublicationOrigin",
    "SourceProfile",
    "PreviousPublication",
    "CanonicalSection",
    "ContextRole",
    "Channel",
    "SubChannel",
    "Sector",
    "Manufacturer",
    "Product",
    "Section",
    "Measure",
)
REVISION_FIELDS = (
    "SourceRevisionID",
    "SourceBytes",
    "SourceFileName",
    "SourceRelativePath",
    "Contract",
    "FirstImportedAtUtc",
    "WideRows",
    "Observations",
    "DefinedNamesJson",
    "PublicationStatus",
    "PublicationOrigin",
    "SourceProfile",
    "Country",
    "GrowthDriver",
    "DemandCycle",
    "Revision",
    "ExFactoryActualsThrough",
    "IMSActualsThrough",
    "PreviousPublication",
)


def history_record(
    row: Mapping[str, Any], source_id: str, filename: str, relative: str
) -> dict[str, Any]:
    """Bind one compact parsed row to the named Spark boundary schema."""
    meta, ids = row["metadata"], row["ids"]
    result = {
        name: meta[name]
        for name in (
            "Country",
            "GrowthDriver",
            "DemandCycle",
            "Version",
            "Revision",
            "ExFactoryActualsThrough",
            "IMSActualsThrough",
            "PublicationStatus",
            "PublicationOrigin",
            "SourceProfile",
            "PreviousPublication",
        )
    }
    result.update(
        zip(
            (
                "Channel",
                "SubChannel",
                "Sector",
                "Manufacturer",
                "Product",
                "Section",
                "Measure",
            ),
            ids,
            strict=True,
        )
    )
    result.update(
        SourceRevisionID=source_id,
        SourceFileName=filename,
        SourceRelativePath=relative,
        SourceSheet=row["sheet"],
        SourceTable=row["table"],
        SourceRow=row["row"],
        Months=row["months"],
        MeasureKey=measure_key(ids[5], ids[6]),
        CanonicalSection=SECTION_ALIASES.get(ids[5], ids[5]),
        ContextRole=row["context_role"],
    )
    return result


def revision_record(reader: BridgeReader, captured_at: str) -> dict[str, str]:
    """Keep explicit publication provenance and profile in the completion receipt."""
    meta = reader.metadata
    result = {
        name: meta[name]
        for name in (
            "Country",
            "GrowthDriver",
            "DemandCycle",
            "Revision",
            "ExFactoryActualsThrough",
            "IMSActualsThrough",
            "PublicationStatus",
            "PublicationOrigin",
            "SourceProfile",
            "PreviousPublication",
            "DefinedNamesJson",
            "Contract",
        )
    }
    result.update(
        SourceRevisionID=reader.sha256,
        SourceBytes=str(len(reader.content)),
        SourceFileName=reader.relative_path.rsplit("/", 1)[-1],
        SourceRelativePath=reader.relative_path,
        FirstImportedAtUtc=captured_at,
        WideRows=str(reader.row_count),
        Observations=str(reader.observation_count),
    )
    return result
