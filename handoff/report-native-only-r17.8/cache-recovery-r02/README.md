# R17.8 — one consolidated TEST recovery and diagnostic run

The last R01 cell accepted a clearValues request (HTTP 202), then rejected the
response Location before recording its ID or polling it. It **never submitted
full**. The printed OperationState=Succeeded and PollCount=1 belonged to an
earlier getDefinition operation. They do not confirm clearValues completion.
TEST may currently have cleared loaded values. Do not rerun R01 or delete
either attempt marker. This R02 cell never submits clearValues.

This combines the receiving checks in one new cell and returns one detailed
JSON. It can complete **one missing full refresh on the existing TEST only**;
it does not install an R17.8 adapter or change model definitions. Independent
failed checks stay in the report. Dependent unsafe or uninformative checks are
explicitly skipped, rather than being labelled passed.

## Exactly what to do on the company laptop

1. Close the TEST report in Power BI Desktop. Let any running TEST notebook or
   model operation finish; do not start another refresh/updater during this run.
2. In the Coordination clone's PowerShell terminal, run:

   ```powershell
   git pull --ff-only
   Get-Content -LiteralPath '.\handoff\report-native-only-r17.8\cache-recovery-r02\RECOVER AND DIAGNOSE TEST R02.py' -Raw -Encoding UTF8 | Set-Clipboard
   ```

3. Open **UK-ANI-Demand → ForecastMaster_GM_Setup**. Add **ONE NEW Python/PySpark
   cell**, paste the entire file and run **ONLY that cell ONCE**. Keep the
   notebook's existing Spark/Lakehouse context. Do not use Run all or rerun an
   earlier cell. No credentials, tenant change or IT request is needed.
4. Let the batch finish. A known processing job can be polled for up to 20
   minutes; scalar reads have a 15-minute batch budget checked between queries.
   Individual SemPy/Spark calls still use their configured service timeouts,
   so these are not hard whole-cell deadlines. Progress messages continue
   without printing values. Interrupting stops further work and preserves any
   safe partial scalar progress if Python can handle the interruption.
5. Copy **the entire final JSON** here, including Checks and Processing. Send
   NEEDS_REVIEW/INTERRUPTED results too. Do not send dataframes, raw error text,
   source rows, financial values or connection definitions. Do not rerun,
   manually refresh, install an updater or publish after this batch.

No separate manual refresh is required before or after this cell. It follows
an existing full request or conditionally submits the single missing full itself.

## Coverage and recovery rules

- Verify the exact existing TEST ID/name/type and read the **exact reported R01
  private backup** and attempt marker. Read whole files; never use preview/head
  reads. Validate the saved count schema before it can enter public output.
- Read complete current model metadata, inventory tables/measures/partition
  modes/relationships, validate known OneLake identifiers and the four original
  date bindings, and compare the whole definition/cloud mapping with the backup.
- Read canonical TEST refresh history since the pinned backup time. Require
  coverage and uniquely identify one ClearValues plus at most one later Full.
  Poll only canonical TEST URLs, using UUIDs. Response URLs are never followed;
  relative, regional, queried or missing Location headers cannot select a host.
- Follow a known running request. Reuse an existing Full rather than submit a
  second one. Fail closed on ambiguous history, unsupported processing types,
  failure, bad source metadata, changed definition/mapping or an unresolved
  prior full-attempt marker. TEST may remain unavailable if completion cannot
  be confirmed; the JSON identifies that hold.
- Before the sole possible Full POST, check history and metadata concurrency,
  write a new private no-overwrite marker, and verify its complete UTF-8 length
  and SHA-256. Request transactional processing, parallelism 1, retryCount 0
  and no refresh-policy application. SDK POST retries are disabled. Internal
  service retries can still occur. A lost response leads only to read-only
  history reconciliation, never another POST.
- Compare exact source/native IMS and EF dates **per source ID**, plus complete
  fact/axis/review/start/end month sets: nine kinds, all rows in UK/October and
  all model month keys. Compare physical metadata before/after and whole model
  definition/cloud mapping. Completed alone is insufficient.
- Independently compare DAX-formatted date text/YEAR with SemPy's typed date
  results and physical dates. Output aggregate agreement/invalid counts only.
  This separates an engine-side date discrepancy from a typed client conversion
  discrepancy; neither is assumed in advance. Failed reads remain unknown.
- Run original/native metadata coverage and selection guard queries separately,
  retaining both results even when one fails. Date mismatch or invalid guards
  blocks financial probing. No dates are inferred from filenames; no source
  table, business formula, relationship or connection is rewritten.
- Only with safe, valid dates/guards/preservation, evaluate up to **90 sequential
  scalar reads**: one available UK/October ADS driver × Market/Ex-factory/Share
  × 6M/12M/24M × 2026/2027 × Plan/Benchmark/Variance/Variance %/future trend.
  Check finite and blank behavior, informative benchmark/trend results and
  internal `(Plan - Benchmark)` and `/ABS(Benchmark)` identities. Retain the
  existing tolerances (relative 1e-9, absolute 1e-6). Amounts stay in memory;
  output contains state, timing and boolean results only. A known cancellation,
  resource, timeout or permission failure skips further financial reads while
  safe final metadata reads continue. Source cohort and metadata are rechecked
  after the probes, together with refresh history and physical dates; changed
  dependencies or another processing job cannot qualify the batch.

Possible qualified stage: `TEST_R178_RECOVERY_AND_BOUNDED_CHECKS_VERIFIED`.
This means the stated recovery/date/internal-sanity checks passed on this run.
It does **not** establish an engine root cause, full company numerical parity,
R16.6 business acceptance, report speed, native rendering/export or acceptance
of the uninstalled R17.8 selection adapter. Every other stage needs review;
no unknown result is promoted to passed.

The notebook necessarily reads company data internally for processing and the
bounded numerical probes. It never prints or stores amount observations. Only
the new private marker is written; existing private backups are kept. There
are no physical Lakehouse table, model-definition, original model, credential,
schedule, report publication or visual changes. Built-in Power BI visuals only.

## Understanding and evidence

[UNDERSTANDING.md](../UNDERSTANDING.md) is the current evidence map for this
repair. [feedback/STATUS.md](../../../feedback/STATUS.md) remains the authority
for returned company results. Update those after reviewing the final JSON;
preserve each receiving attempt and keep old package bytes unchanged.

Local test results and limits are in [VALIDATION.json](VALIDATION.json).
These are simulated state/API checks; no company API, DAX, Spark or Desktop
execution has taken place on this host.

Official references: [refresh history](https://learn.microsoft.com/en-us/rest/api/power-bi/datasets/get-refresh-history-in-group),
[execution details, processing types and HTTP 202](https://learn.microsoft.com/en-us/rest/api/power-bi/datasets/get-refresh-execution-details-in-group),
[enhanced refresh and transactions](https://learn.microsoft.com/en-us/power-bi/connect-data/asynchronous-refresh),
[submission and service-internal retries](https://learn.microsoft.com/en-us/rest/api/power-bi/datasets/refresh-dataset-in-group).
