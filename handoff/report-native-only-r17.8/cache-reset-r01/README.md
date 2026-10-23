# R17.8 — isolated TEST date-cache reset R01

R03 completed all requested reads on 23 October 2026. Physical Lakehouse cutoff
and month columns are DATE with no invalid dates. In TEST, the fact, review,
start and end dictionaries each have 84 valid months, but **83 of 84 axis dates
are invalid**. Model date types, entity names and source-column names match the
expected declarations. Earlier R01 observed invalid original/native TEST file
cutoffs. These are physical/semantic discrepancies; they do not establish the
precise engine cause or a permanent repair. No source rewrite is indicated.

The next controlled attempt is to clear loaded values in ONLY existing TEST,
then perform a full refresh and compare exact date metadata privately. Normal
Direct Lake framing may retain dictionaries for unchanged files. Microsoft's
Fabric Toolbox demonstrates clearValues followed by full to obtain a cold
Direct Lake model. This is an evidence-backed cache-reset attempt, not a claim
that a cache defect has been proved.

## What this cell does

- Verifies exact TEST identity `31d00232-ac03-48fe-af39-f2e4bae82443`, its known
  OneLake source identifiers and date bindings. Reads only scoped file/date
  metadata through DAX/Spark. It never guesses dates from filenames.
- Compares exact cutoff dates per source ID and all fact/axis/review/start/end
  month keys privately. If they already match, no processing is submitted.
- Refuses invalid physical dates, mismatched physical month sets, unexpected
  routing, an active/unknown refresh, an existing attempt marker, failed backup
  verification or concurrent metadata/cloud-mapping changes.
- Creates a private definition/connection/count backup and verifies FULL UTF-8
  file length and SHA-256 using file copy, never preview reads. Creates one
  persistent private attempt marker before processing to prevent blind reruns.
- Submits `clearValues`, waits for confirmed completion, then submits `full`.
  Both use transactional mode, parallelism 1 and requested retryCount 0. SDK
  submission retries are disabled too. Service-internal retries remain possible.
- Checks complete model-definition/cloud-mapping preservation, physical date
  metadata stability, exact semantic/date equality and refresh messages.
  A refresh marked Completed alone cannot pass the date checks.

**This cell changes TEST processing state.** Loaded TEST values are cleared,
and TEST can be unavailable until full processing succeeds. It does not write
model definitions, physical Delta tables, business formulas, connection
settings, schedules, credentials or production R16.6. Model processing may read
business data internally; the script submits no amount query and prints/stores
no financial observations. Backup metadata stays private in the existing
Lakehouse Files area. No company runtime execution occurred on this host.

## Next steps on the company laptop

1. Close the R17.7 TEST report in Desktop. In Coordination's PowerShell terminal:

   ```powershell
   git pull --ff-only
   Get-Content -LiteralPath '.\handoff\report-native-only-r17.8\cache-reset-r01\RESET TEST DATE CACHE R01.py' -Raw -Encoding UTF8 | Set-Clipboard
   ```

2. In **UK-ANI-Demand → ForecastMaster_GM_Setup**, add **ONE NEW Python/PySpark
   cell**, paste the WHOLE file and run **ONLY that cell ONCE**. Keep the existing
   Spark/Lakehouse context. Do not use Run all or edit earlier setup cells.
   Allow the two processing phases to finish; progress messages identify them.

3. Send the final JSON. Do not manually refresh again, rerun this cell, delete
   its attempt marker, install an older updater or publish.

Expected qualified result: `TEST_R178_DATE_CACHE_RESET_VERIFIED`, with date
parity, stable physical date metadata, definition/cloud preservation and both
processing phases confirmed. `TEST_R178_DATES_ALREADY_MATCH_NO_RESET` means
current exact date parity needed no reset. Both still need the returned JSON.

Any STOPPED result must be reviewed. `Processing` records whether each request
may have been submitted and whether completion was confirmed. In particular,
after clearValues succeeds, a failed/ambiguous full refresh can leave TEST
unavailable. Keep the backup and return the JSON/request IDs; do not clear again
or assume no action occurred. Recovery should follow the known operation state.

This revision does not install the draft R17.8 selection adapter or replace the
report. Date correctness must be reviewed before that next qualification step.
The compact native SAMPLE and all previous packages retain their bytes. Built-in
Power BI visuals only; native rendering, numerical parity and speed remain open.

## Local evidence and sources

Sixteen mocked checks cover identity/routing boundaries, processing order,
pending HTTP 202 polling, no resubmission after ambiguous errors, backups,
concurrency, metadata readback, exact date parity and private output. Python
3.10 syntax parses. Spark/Delta and company REST/DAX processing are unexecuted
here. All 1118 prior protected manifest files are preserved, excluding only the
four mutable root guidance/status documents. GitNexus cannot resolve this repo;
full graph impact is unknown and direct checks are the bounded fallback.

References: [Direct Lake framing and dictionary retention](https://learn.microsoft.com/en-us/fabric/fundamentals/direct-lake-how-it-works),
[Microsoft Fabric Toolbox cold-state implementation](https://github.com/microsoft/fabric-toolbox/blob/main/tools/DAXPerformanceTesting/DAXPerformanceTesting.ipynb),
[enhanced processing types and transactions](https://learn.microsoft.com/en-us/power-bi/connect-data/asynchronous-refresh),
[refresh submission and service-internal retry caveat](https://learn.microsoft.com/en-us/rest/api/power-bi/datasets/refresh-dataset-in-group),
[refresh execution details and HTTP 202](https://learn.microsoft.com/en-us/rest/api/power-bi/datasets/get-refresh-execution-details-in-group).
