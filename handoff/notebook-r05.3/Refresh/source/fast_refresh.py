"""Changed-file Fabric ingestion. The notebook embeds this module and the unchanged value decoder."""

from __future__ import annotations

import hashlib
import json
import re
import time
import uuid
from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any
from urllib.parse import unquote

from delta.tables import DeltaTable
from pyspark.sql import functions as F
from pyspark.sql import types as T

FILE_MONTH = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{2}"
NAME_PATTERN = re.compile(
    rf"[^_]+_.+?_Bridge_{FILE_MONTH}_EF-{FILE_MONTH}_IMS-{FILE_MONTH}_.+\.(?:xlsx|xlsm)",
    re.IGNORECASE,
)
FILE_GLOB = "*_[Bb][Rr][Ii][Dd][Gg][Ee]_*_[Ee][Ff]-*_[Ii][Mm][Ss]-*.[Xx][Ll][Ss]*"
EVENT_FIELDS = [
    "RunID",
    "ObservedAtUtc",
    "SourcePath",
    "SourceRelativePath",
    "SourceModifiedAt",
    "SourceBytes",
    "ReaderContract",
    "Status",
    "SourceRevisionID",
    "Observations",
    "Message",
]


def filename_candidate(name: str) -> bool:
    """Any version suffix and any folder; only the agreed xlsx/xlsm filename contract."""
    return not name.startswith("~$") and NAME_PATTERN.fullmatch(name) is not None


def normalized_path(path: str) -> str:
    """SharePoint paths are case insensitive; separators do not create scenarios."""
    return "/".join(p for p in path.replace("\\", "/").split("/") if p).casefold()


def report_identity(content_id: str, path: str, original_path: str = "") -> str:
    """One permanent report identity per saved file, independent of edited bytes."""
    if not path:
        raise ValueError("A saved file needs an explicit relative path")
    return hashlib.sha256(
        ("current-file-v1|" + normalized_path(path)).encode()
    ).hexdigest()


def current_content_ids(
    pointers: list[dict[str, str]], completed: set[str]
) -> list[str]:
    """Do not delete any dataset still referenced by a complete file pointer."""
    active = {row["SourceRevisionID"] for row in pointers}
    if not active or not active <= completed:
        raise ValueError("Cannot compact an incomplete current-file index")
    return sorted(active)


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


class FastRefresh:
    """One writer. Events are batched; each changed workbook is materialized and merged once."""

    def __init__(self, spark: Any, reader: dict[str, Any], config: dict[str, Any]):
        self.spark, self.reader, self.config = spark, reader, config
        self.prefix = config["TABLE_PREFIX"]
        if not re.fullmatch(r"[a-z][a-z0-9_]*", self.prefix):
            raise ValueError("Invalid table prefix")
        self.allowed = set(config["ALLOWED_PROFILES"])
        if not self.allowed or not self.allowed <= {"Local", "Ext"}:
            raise ValueError("Choose Local and/or Ext explicitly")
        self.root = config["SOURCE_ROOT"].rstrip("/")
        self.run_id = str(uuid.uuid4())
        self.contract = (
            reader["CONTRACT"] + "|affiliate-bridge-cycle-ef-ims-any-suffix-v1"
        )
        self.events: list[dict[str, str]] = []
        self.timings: list[dict[str, Any]] = []
        self.writes: Counter[str] = Counter()
        self.state_updates: list[dict[str, str]] = []
        self.new_source_ids: list[str] = []
        self.completed: dict[str, dict[str, str]] = {}
        self.source_changed = False
        self.stage_errors: list[str] = []
        self.report_changed = False
        self.current_report_files = 0
        self.failed_files = 0
        self.discovered_paths: set[str] | None = None
        self.discovery_metadata: list[dict[str, Any]] = []
        self.run_started = time.perf_counter()

    @contextmanager
    def stage(self, name: str, filename: str = "") -> Iterator[None]:
        started = time.perf_counter()
        record = {"Stage": name, "FileName": filename, "Seconds": 0.0, "Status": "OK"}
        print(f"Starting: {name}" + (f" — {filename}" if filename else ""), flush=True)
        try:
            yield
        except Exception:
            record["Status"] = "FAILED"
            raise
        finally:
            record["Seconds"] = round(time.perf_counter() - started, 3)
            self.timings.append(record)
            print(f"{name}: {record['Seconds']:.2f}s ({record['Status']})", flush=True)

    def event(
        self,
        meta: dict[str, Any],
        status: str,
        source_id: str = "",
        count: int = 0,
        message: str = "",
    ) -> None:
        self.events.append(
            dict(
                zip(
                    EVENT_FIELDS,
                    [
                        self.run_id,
                        utc_now(),
                        meta["path"],
                        meta["relative"],
                        meta["modified"],
                        str(meta["size"]),
                        self.contract,
                        status,
                        source_id,
                        str(count),
                        message,
                    ],
                    strict=True,
                )
            )
        )

    def string_frame(self, rows: list[dict[str, str]], names: list[str]) -> Any:
        schema = T.StructType([T.StructField(n, T.StringType(), True) for n in names])
        return self.spark.createDataFrame(rows, schema)

    def upsert(
        self,
        name: str,
        frame: Any,
        keys: list[str],
        *,
        source_id: str = "",
        update: bool = False,
    ) -> None:
        """Content tables insert missing keys; mutable metadata pointers may update."""
        if not self.spark.catalog.tableExists(name):
            frame.coalesce(2).write.format("delta").mode("errorifexists").saveAsTable(
                name
            )
        else:
            condition = " AND ".join(f"target.`{k}` <=> source.`{k}`" for k in keys)
            if source_id:
                condition += " AND target.SourceRevisionID = '" + source_id + "'"
            merge = (
                DeltaTable.forName(self.spark, name)
                .alias("target")
                .merge(frame.alias("source"), condition)
            )
            if update:
                merge = merge.whenMatchedUpdateAll()
            merge.whenNotMatchedInsertAll().execute()
        self.writes[name] += 1

    def replace_snapshot(self, name: str, frame: Any, keys: list[str]) -> None:
        """Atomically replace a derived/configuration snapshot using its declared unique keys."""
        if not self.spark.catalog.tableExists(name):
            frame.coalesce(1).write.format("delta").mode("errorifexists").saveAsTable(
                name
            )
        else:
            condition = " AND ".join(f"target.`{k}` <=> source.`{k}`" for k in keys)
            (
                DeltaTable.forName(self.spark, name)
                .alias("target")
                .merge(frame.alias("source"), condition)
                .whenMatchedUpdateAll()
                .whenNotMatchedInsertAll()
                .whenNotMatchedBySourceDelete()
                .execute()
            )
        self.writes[name] += 1

    def _metadata(self, row: Any) -> dict[str, Any]:
        path = row["path"]
        decoded = unquote(path)
        marker = "/" + self.root.strip("/") + "/"
        if marker not in decoded:
            raise ValueError(
                "Discovered source is outside the configured Demand root: " + decoded
            )
        relative = decoded.split(marker, 1)[1]
        return {
            "path": path,
            "relative": relative,
            "name": relative.rsplit("/", 1)[-1],
            "size": int(row["length"]),
            "modified": row["modificationTime"].isoformat(),
            "modified_value": row["modificationTime"],
        }

    def discover(self) -> list[dict[str, Any]]:
        """Full discovery finds new folders. FILES mode checks exact known paths without a root crawl."""
        mode = self.config.get("REFRESH_MODE", "ALL").upper()
        paths = self.config.get("SELECTED_RELATIVE_PATHS", [])
        if mode == "FILES":
            if not paths or any(
                p.startswith("/") or ":" in p or ".." in p.split("/") for p in paths
            ):
                raise ValueError("FILES mode needs exact relative paths inside Demand")
            roots = [self.root + "/" + p for p in dict.fromkeys(paths)]
        elif mode == "ALL":
            roots = self.root
        else:
            raise ValueError("REFRESH_MODE must be ALL or FILES")
        rows = (
            self.spark.read.format("binaryFile")
            .option("recursiveFileLookup", True)
            .option("pathGlobFilter", FILE_GLOB)
            .load(roots)
            .select("path", "length", "modificationTime")
            .collect()
        )
        candidates = []
        for row in rows:
            meta = self._metadata(row)
            if filename_candidate(meta["name"]):
                candidates.append(meta)
            else:
                self.event(meta, "OUTSIDE_FILENAME_PATTERN")
        print(
            f"Files inspected: {len(rows)}; matching bridge filenames: {len(candidates)}",
            flush=True,
        )
        if not candidates:
            raise ValueError(
                "No files match the agreed bridge filename convention in this scope"
            )
        return sorted(candidates, key=lambda x: x["path"])

    def load_state(self) -> dict[str, tuple[str, str, str]]:
        revisions = self.prefix + "_source_revisions"
        if self.spark.catalog.tableExists(revisions):
            self.completed = {
                r["SourceRevisionID"]: r.asDict()
                for r in self.spark.table(revisions).collect()
            }
        state_name = self.prefix + "_file_state"
        if self.spark.catalog.tableExists(state_name):
            return {
                r["SourcePath"]: (
                    r["SourceModifiedAt"],
                    r["SourceBytes"],
                    r["SourceRevisionID"],
                )
                for r in self.spark.table(state_name)
                .where(F.col("ReaderContract") == self.contract)
                .collect()
            }
        events = self.prefix + "_ingestion_events"
        if not self.spark.catalog.tableExists(events):
            return {}
        rows = (
            self.spark.table(events)
            .where(F.col("Status").isin("SUCCEEDED", "SAME_CONTENT"))
            .where(F.col("ReaderContract") == self.contract)
            .groupBy("SourcePath")
            .agg(
                F.max(
                    F.struct(
                        "ObservedAtUtc",
                        "SourceModifiedAt",
                        "SourceBytes",
                        "SourceRevisionID",
                    )
                ).alias("last")
            )
            .collect()
        )
        return {
            r["SourcePath"]: (
                r["last"]["SourceModifiedAt"],
                r["last"]["SourceBytes"],
                r["last"]["SourceRevisionID"],
            )
            for r in rows
        }

    def remember(self, meta: dict[str, Any], source_id: str) -> None:
        self.state_updates.append(
            {
                "SourcePath": meta["path"],
                "SourceRelativePath": meta["relative"],
                "SourceModifiedAt": meta["modified"],
                "SourceBytes": str(meta["size"]),
                "SourceRevisionID": source_id,
                "ReaderContract": self.contract,
                "LastSuccessAtUtc": utc_now(),
            }
        )

    def ingest_one(
        self, meta: dict[str, Any], previous: dict[str, tuple[str, str, str]]
    ) -> None:
        prior = previous.get(meta["path"])
        if (
            not self.config.get("FORCE_REHASH", False)
            and normalized_path(meta["relative"])
            not in {
                normalized_path(path)
                for path in self.config.get("FORCE_REHASH_PATHS", [])
            }
            and prior
            and prior[:2] == (meta["modified"], str(meta["size"]))
            and prior[2] in self.completed
            and self.completed[prior[2]]["SourceProfile"] in self.allowed
        ):
            self.event(meta, "METADATA_UNCHANGED", prior[2])
            self.remember(meta, prior[2])
            return
        if meta["size"] > self.config.get("MAX_BRIDGE_BYTES", 128 * 1024 * 1024):
            raise ValueError(
                "Matching workbook exceeds the configured per-file byte bound"
            )
        with self.stage("Read saved workbook", meta["name"]):
            found = (
                self.spark.read.format("binaryFile")
                .load(meta["path"])
                .select("content", "length", "modificationTime")
                .collect()
            )
            if (
                len(found) != 1
                or int(found[0]["length"]) != meta["size"]
                or found[0]["modificationTime"] != meta["modified_value"]
            ):
                raise ValueError(
                    "The file changed while being read; save/upload must finish before retry"
                )
            content = bytes(found[0]["content"])
            source_id = hashlib.sha256(content).hexdigest()
        if source_id in self.completed:
            receipt = self.completed[source_id]
            expected_cycle = self.reader["folder_cycle"](meta["relative"])
            if receipt["DemandCycle"] != expected_cycle:
                raise ValueError(
                    "Saved content cycle differs from the matching filename cycle"
                )
            if receipt["SourceProfile"] not in self.allowed:
                self.event(meta, "OTHER_PROFILE", source_id)
                return
            self.event(meta, "SAME_CONTENT", source_id)
            self.remember(meta, source_id)
            return
        with self.stage("Decode saved values", meta["name"]):
            reader = self.reader["BridgeReader"](content, meta["relative"])
            iterator = reader.rows()
            first = next(iterator)
            if reader.metadata["SourceProfile"] not in self.allowed:
                self.event(meta, "OTHER_PROFILE", source_id)
                return
            raw_rows = [
                self.reader["history_record"](
                    first, source_id, meta["name"], meta["relative"]
                )
            ]
            for row in iterator:
                raw_rows.append(
                    self.reader["history_record"](
                        row, source_id, meta["name"], meta["relative"]
                    )
                )
                if reader.observation_count > self.config.get(
                    "MAX_OBSERVATIONS_PER_FILE", 5_000_000
                ):
                    raise ValueError(
                        "Workbook exceeds the configured single-file materialization bound"
                    )
        with self.stage("Commit source tables", meta["name"]):
            self.write_source(raw_rows, source_id, reader.observation_count)
            receipt = self.reader["revision_record"](reader, utc_now())
            self.upsert(
                self.prefix + "_source_revisions",
                self.string_frame([receipt], list(self.reader["REVISION_FIELDS"])),
                ["SourceRevisionID"],
            )
        self.completed[source_id] = receipt
        self.new_source_ids.append(source_id)
        self.source_changed = True
        self.event(meta, "SUCCEEDED", source_id, reader.observation_count)
        self.remember(meta, source_id)

    def write_source(
        self, rows: list[dict[str, Any]], source_id: str, expected: int
    ) -> None:
        month_fields = [
            "DemandMonth",
            "SourceMonthHeader",
            "ValueKind",
            "ValueRaw",
            "ValueNumber",
            "ValueText",
            "ValueBoolean",
            "SourceFormula",
            "FormulaCacheState",
        ]
        month_types = [
            T.StringType(),
            T.StringType(),
            T.StringType(),
            T.StringType(),
            T.DoubleType(),
            T.StringType(),
            T.BooleanType(),
            T.StringType(),
            T.StringType(),
        ]
        months = T.StructType(
            [
                T.StructField(k, v, True)
                for k, v in zip(month_fields, month_types, strict=True)
            ]
        )
        schema = T.StructType(
            [T.StructField(n, T.StringType(), True) for n in self.reader["WIDE_FIELDS"]]
            + [
                T.StructField("SourceRow", T.LongType(), False),
                T.StructField("Months", T.ArrayType(months, False), False),
            ]
        )
        frame = (
            self.spark.createDataFrame(rows, schema)
            .coalesce(2)
            .select("*", F.explode("Months").alias("Observation"))
            .select("*", "Observation.*")
            .drop("Months", "Observation")
            .withColumn("DemandMonth", F.to_date("DemandMonth"))
            .withColumn(
                "ObservationID",
                F.sha2(
                    F.concat_ws(
                        "|",
                        "SourceRevisionID",
                        "SourceTable",
                        F.col("SourceRow").cast("string"),
                        F.col("DemandMonth").cast("string"),
                    ),
                    256,
                ),
            )
            .withColumn(
                "SourceMeasureID",
                F.sha2(F.concat_ws("|", "SourceRevisionID", "MeasureKey"), 256),
            )
            .persist()
        )
        try:
            if frame.count() != expected:
                raise ValueError(
                    "Materialized source observation count differs from the saved workbook"
                )
            self.upsert(
                self.prefix + "_history", frame, ["ObservationID"], source_id=source_id
            )
            measure_names = [
                "SourceRevisionID",
                "SourceMeasureID",
                "MeasureKey",
                "Country",
                "SourceProfile",
                "GrowthDriver",
                "DemandCycle",
                "Section",
                "Measure",
                "CanonicalSection",
                "ContextRole",
            ]
            self.upsert(
                self.prefix + "_source_measures",
                frame.select(*measure_names).distinct(),
                ["SourceMeasureID"],
                source_id=source_id,
            )
            calendar = (
                frame.where(F.col("ContextRole") == "Calendar")
                .select(
                    "SourceRevisionID",
                    "SourceProfile",
                    "Country",
                    "GrowthDriver",
                    "DemandCycle",
                    "DemandMonth",
                    F.dayofmonth(F.last_day("DemandMonth")).alias("CalendarDays"),
                    F.col("ValueNumber").alias("WorkingDays"),
                )
                .distinct()
                .withColumn(
                    "CalendarID",
                    F.sha2(
                        F.concat_ws(
                            "|", "SourceRevisionID", F.col("DemandMonth").cast("string")
                        ),
                        256,
                    ),
                )
            )
            self.upsert(
                self.prefix + "_calendar", calendar, ["CalendarID"], source_id=source_id
            )
            controls = (
                frame.where(F.col("ContextRole") == "Model Control")
                .select(
                    "SourceRevisionID",
                    "SourceProfile",
                    "Country",
                    "GrowthDriver",
                    "DemandCycle",
                    "SourceSheet",
                    "SourceTable",
                    "SourceRow",
                    "Channel",
                    "SubChannel",
                    "Sector",
                    "Manufacturer",
                    "Product",
                    "Section",
                    "Measure",
                )
                .distinct()
                .withColumn(
                    "ControlID",
                    F.sha2(
                        F.concat_ws(
                            "|",
                            "SourceRevisionID",
                            "SourceTable",
                            F.col("SourceRow").cast("string"),
                        ),
                        256,
                    ),
                )
                .withColumn(
                    "InputSlot", F.regexp_extract("Measure", r"Contract (\d+)", 1)
                )
            )
            roles = {r["ContextRole"] for r in rows}
            if "Model Control" in roles or not self.spark.catalog.tableExists(
                self.prefix + "_controls"
            ):
                self.upsert(
                    self.prefix + "_controls",
                    controls,
                    ["ControlID"],
                    source_id=source_id,
                )
            if "Data Quality" in roles or not self.spark.catalog.tableExists(
                self.prefix + "_quality"
            ):
                self.upsert(
                    self.prefix + "_quality",
                    frame.where(F.col("ContextRole") == "Data Quality"),
                    ["ObservationID"],
                    source_id=source_id,
                )
            saved = (
                self.spark.table(self.prefix + "_history")
                .where(F.col("SourceRevisionID") == source_id)
                .count()
            )
            if saved != expected:
                raise ValueError(
                    "Committed observation count differs; source receipt will not be published"
                )
        finally:
            frame.unpersist()

    def flush(self) -> None:
        """One audit commit per run; file-state pointers exist only for complete source receipts."""
        if self.events:
            frame = self.string_frame(self.events, EVENT_FIELDS)
            frame.coalesce(1).write.format("delta").mode("append").saveAsTable(
                self.prefix + "_ingestion_events"
            )
            self.writes[self.prefix + "_ingestion_events"] += 1
        if self.state_updates:
            # Existing metadata pointers are cheap; avoid updating them on an unchanged run.
            name = self.prefix + "_file_state"
            if (
                self.source_changed
                or any(e["Status"] == "SAME_CONTENT" for e in self.events)
                or not self.spark.catalog.tableExists(name)
            ):
                frame = self.string_frame(
                    self.state_updates, list(self.state_updates[0])
                )
                self.upsert(name, frame, ["SourcePath"], update=True)
        # A completed recursive inventory retires deleted/renamed paths. FILES
        # mode never removes paths outside its requested scope. Failed files
        # still present in the inventory keep their last successful pointer.
        name = self.prefix + "_file_state"
        if self.spark.catalog.tableExists(name):
            original = [r.asDict() for r in self.spark.table(name).collect()]
            latest: dict[str, dict[str, str]] = {}
            for row in original:
                key = normalized_path(row["SourceRelativePath"])
                if (
                    self.discovered_paths is not None
                    and key not in self.discovered_paths
                ):
                    continue
                if (
                    key not in latest
                    or row["LastSuccessAtUtc"] > latest[key]["LastSuccessAtUtc"]
                ):
                    latest[key] = row
            if len(latest) != len(original):
                if not latest:
                    raise ValueError(
                        "Current-file retirement would leave an empty index"
                    )
                self.replace_snapshot(
                    name,
                    self.string_frame(list(latest.values()), list(original[0])),
                    ["SourcePath"],
                )
                self.source_changed = True

    def ingest(self) -> None:
        with self.stage("Discover matching files"):
            candidates = self.discover()
            self.discovery_metadata = candidates
            if self.config.get("REFRESH_MODE", "ALL").upper() == "ALL":
                self.discovered_paths = {
                    normalized_path(m["relative"]) for m in candidates
                }
        with self.stage("Load compact change index"):
            previous = self.load_state()
        try:
            for meta in candidates:
                try:
                    self.ingest_one(meta, previous)
                except Exception as exc:  # noqa: BLE001 -- retain stage diagnostics and surface failure  # noqa: BLE001 -- retain attributable per-file failures and continue other sources
                    self.failed_files += 1
                    self.event(meta, "FAILED", message=str(exc))
                    print("FAILED:", meta["relative"], str(exc), flush=True)
        finally:
            with self.stage("Commit batched audit and change index"):
                self.flush()

    def report_sources(self) -> list[dict[str, str]]:
        """Only the latest complete pointer per saved path enters reporting."""
        name = self.prefix + "_file_state"
        if not self.spark.catalog.tableExists(name):
            raise ValueError("No committed current-file index is available")
        latest: dict[str, dict[str, str]] = {}
        for item in self.spark.table(name).collect():
            row = item.asDict()
            key = normalized_path(row["SourceRelativePath"])
            prior = latest.get(key)
            if prior is None or (row.get("LastSuccessAtUtc", ""), row["SourcePath"]) > (
                prior.get("LastSuccessAtUtc", ""),
                prior["SourcePath"],
            ):
                latest[key] = row
        rows = []
        for _, pointer in sorted(latest.items()):
            source_id, relative = (
                pointer["SourceRevisionID"],
                pointer["SourceRelativePath"],
            )
            raw = self.completed.get(source_id)
            if raw is None:
                raise ValueError(
                    "Current file has no completed source receipt: " + relative
                )
            if raw["SourceProfile"] not in self.allowed or not filename_candidate(
                relative.rsplit("/", 1)[-1]
            ):
                continue
            row = dict(raw)
            row.update(
                RawSourceRevisionID=source_id,
                SourceRevisionID=report_identity(source_id, relative),
                SourceRelativePath=relative,
                SourceFileName=relative.rsplit("/", 1)[-1],
                PathFirstSeenAtUtc=pointer["LastSuccessAtUtc"],
            )
            rows.append(row)
        if not rows:
            raise ValueError(
                "No complete matching current files are available for reporting"
            )
        self.current_report_files = len(rows)
        return rows

    def compact_current_sources(self) -> dict[str, int]:
        """Remove superseded full datasets after current reporting/model confirmation.

        Shared content survives while ANY saved path still points to it. Audit
        events keep hashes/status/timestamps, never a second full workbook copy.
        Delta's ordinary recovery retention is not disabled.
        """
        pointers = (
            self.spark.table(self.prefix + "_file_state")
            .select("SourceRevisionID")
            .distinct()
        )
        active = current_content_ids(
            [row.asDict() for row in pointers.collect()], set(self.completed)
        )
        signature = hashlib.sha256(json.dumps(sorted(active)).encode()).hexdigest()
        state_name = self.prefix + "_current_storage_state"
        previous = (
            self.spark.table(state_name).first()
            if self.spark.catalog.tableExists(state_name)
            else None
        )
        if previous and previous["Signature"] == signature and not self.failed_files:
            print(
                "Current-file data unchanged: no compaction scans or writes.",
                flush=True,
            )
            self.maintain_storage()
            return {}
        counts = {}
        for suffix in (
            "history",
            "source_measures",
            "calendar",
            "controls",
            "quality",
            "measure_assignments",
            "source_revisions",
        ):
            name = self.prefix + "_" + suffix
            if not self.spark.catalog.tableExists(name):
                continue
            stale = ~F.col("SourceRevisionID").isin(active)
            count = self.spark.table(name).where(stale).count()
            if count:
                DeltaTable.forName(self.spark, name).delete(stale)
                self.writes[name] += 1
            counts[name] = count
        self.completed = {sid: self.completed[sid] for sid in active}
        self.replace_snapshot(
            state_name,
            self.string_frame(
                [{"Signature": signature, "CompletedAtUtc": utc_now()}],
                ["Signature", "CompletedAtUtc"],
            ),
            ["Signature"],
        )
        self.maintain_storage()
        print(
            "Current-file compaction: removed superseded rows",
            json.dumps(counts),
            flush=True,
        )
        return counts

    def maintain_storage(self) -> None:
        """Weekly vacuum during an actual requested run; retain at least seven days.

        This never disables retention checks, starts an idle Spark session, or
        treats recovery files as report scenarios. Retry unfinished maintenance.
        """
        name = self.prefix + "_storage_maintenance"
        prior = (
            self.spark.table(name).first()
            if self.spark.catalog.tableExists(name)
            else None
        )
        if (
            prior
            and (
                datetime.now(UTC) - datetime.fromisoformat(prior["CompletedAtUtc"])
            ).total_seconds()
            < 7 * 86400
        ):
            return
        if prior is None:
            # Establish the weekly cadence without scanning fresh recovery files
            # on the one-time migration. First vacuum occurs after seven days.
            self.replace_snapshot(
                name,
                self.string_frame([{"CompletedAtUtc": utc_now()}], ["CompletedAtUtc"]),
                ["CompletedAtUtc"],
            )
            print(
                "Physical cleanup cadence initialized; seven-day recovery retention preserved.",
                flush=True,
            )
            return
        prefixes = {self.prefix, self.config.get("REPORT_PREFIX", "fm_review")}
        managed = {
            self.prefix + "_" + s
            for s in (
                "history",
                "source_measures",
                "calendar",
                "controls",
                "quality",
                "source_revisions",
                "measure_assignments",
                "file_state",
                "ingestion_events",
            )
        }
        managed.update(
            self.config.get("REPORT_PREFIX", "fm_review") + "_" + s
            for s in ("facts", "files", "reference", "projection_receipts", "series")
        )
        for table in sorted(managed):
            if not any(table.startswith(prefix + "_") for prefix in prefixes):
                raise ValueError("Unexpected maintenance table")
            if self.spark.catalog.tableExists(table):
                DeltaTable.forName(self.spark, table).vacuum(168)
        self.replace_snapshot(
            name,
            self.string_frame([{"CompletedAtUtc": utc_now()}], ["CompletedAtUtc"]),
            ["CompletedAtUtc"],
        )

    def summary(self) -> dict[str, Any]:
        status = "PARTIAL" if self.failed_files or self.stage_errors else "SUCCESS"
        return {
            "RunID": self.run_id,
            "Status": status,
            "FileResults": dict(Counter(e["Status"] for e in self.events)),
            "UpdatedFiles": sum(e["Status"] == "SUCCEEDED" for e in self.events),
            "DecodedChangedFiles": len(self.new_source_ids),
            "CurrentReportFiles": self.current_report_files,
            "StoragePolicy": "CURRENT_FILE_PER_PATH",
            "TableWrites": dict(self.writes),
            "StageErrors": self.stage_errors,
            "SecondsAfterSessionReady": round(
                time.perf_counter() - self.run_started, 3
            ),
        }
