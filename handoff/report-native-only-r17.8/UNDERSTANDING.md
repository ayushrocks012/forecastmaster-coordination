# ForecastMaster native TEST — current understanding

This is the maintained evidence map for the native-report/date repair, requested
by the user on 23 October 2026. Read it before continuing this work. Runtime
receipts and the current receiving action remain in [feedback/STATUS.md](../../feedback/STATUS.md);
this file records interpretation, constraints and evidence needed for decisions.
It is not a promise that future errors are impossible or a replacement for
current verification. Latest review: R01 reset returned, R02 combined recovery
and diagnostics prepared; R02 company execution **pending**.

## System and ownership

- Coordination is the public code/instructions handoff. Company Power BI/Fabric
  and Desktop access are on the **other laptop**. Installed Power BI plugins
  here do not establish a company session or company execution evidence.
- Existing isolated TEST: `31d00232-ac03-48fe-af39-f2e4bae82443`, named
  `ForecastMaster Native OneLake R17.1 - TEST`; report version and model display
  name have different numbering. Production R16.6 is outside this repair.
- Physical data uses four relevant original Direct Lake entities:
  fm_review_files, fm_review_months, fm_review_axis, fm_review_facts. Native
  file/month helpers and measures sit above that layer. Source date bindings,
  physical storage, semantic loaded values, DAX guards and report layout are
  separate diagnostic boundaries.
- Work on main, one writer. Preserve published handoff/ZIP/receipt bytes. Keep
  company amounts, source records, raw definitions/connections/errors and
  screenshots out of this public repository. Safe summaries only.

## Confirmed findings and their limits

| Finding | Evidence | What it establishes |
| --- | --- | --- |
| R17.7 refresh was reported Completed, while both matrices and the plot stayed blank; 1899 cutoff labels appeared. | [UI receipt](../../feedback/logs/2026-10-23-native-r177-ui-rejected.json) | Completion did not establish valid loaded dates or working visuals. |
| All three October original TEST file rows and their native copies had invalid IMS/EF cutoffs; both ADS choices were affected. SourceOK=1 but cutoff, fit and period guards failed. | [Metadata receipt](../../feedback/logs/2026-10-23-native-r178-invalid-test-dates.json) | The helper was propagating invalid semantic metadata; there was no ID/metadata mismatch between original TEST and helper. It did not prove physical Lakehouse or workbook corruption. |
| Physical DATE columns were valid: three October files and 84 month keys in each checked month table. Semantic axis had 83/84 invalid dates; fact/review/start/end dictionaries were valid. Types/entity/source-column names matched. | [R03 boundary receipt](../../feedback/logs/2026-10-23-native-r178-boundary-r03-completed.json) | Physical and semantic date reads differed. R03 did not compare full source URI or exact values. A specific engine/cache defect was not proved. |
| R01 reset validated routing, exact private date mismatch, backups and concurrency, then accepted clearValues HTTP 202. Its response-URL validator stopped before polling clear or submitting full. | [R01 interrupted reset receipt](../../feedback/logs/2026-10-23-native-r178-reset-r01-stopped.json) | Clear may have executed; full was never requested by R01. The printed Succeeded/PollCount came from getDefinition and must not be attributed to clear. |

The **current actionable problem** is an accepted, unconfirmed TEST clear
request with no R01 full submission. Recover by identifying that request in
canonical TEST history, never by repeating clear. A successful cold load would
support this recovery path; it would not alone prove why date interpretation
failed or prevent recurrence.

R17.7 numerical preflight was narrowly qualified before this processed-date
state. Its 54 direct baseline + 18 definition-checked derived expectations
against 72 candidate results do not qualify later loaded values, the draft
R17.8 selection adapter, all company contexts or native UI. Preserve that
distinction when using historical evidence.

## Current action and decision gates

Run [the R02 combined cell](cache-recovery-r02/README.md) once on the company
laptop. It checks history/backup/binding/concurrency, follows or safely completes
the single missing full, then exact dates, metadata coverage, guards and bounded
private scalar sanity. All independent safe results stay in one JSON. Missing
dependencies are marked skipped; failure/ambiguity blocks mutation or dependent
amount reads. The code never submits another clearValues request.

Interpret the results in this order:

1. Was the accepted clear uniquely identified and completed? Was a later full
   found or submitted once and completed? Any uncertainty keeps TEST held.
2. Are the complete model definition/cloud mapping preserved and physical
   metadata stable? Changed dependencies invalidate qualification.
3. Do exact physical/semantic cutoffs per ID and all month sets match? Range
   or row-count agreement alone is insufficient. The independent DAX date-text
   versus SemPy typed-date check distinguishes engine and client conversion
   boundaries without printing date/ID observations. This distinction remains
   unexecuted until the receiving output returns.
4. Do source coverage, source choice, cutoff, fit and period guards pass?
5. Do the 90 representative scalar reads execute with informative results and
   correct internal variance identities? These are not an independent business
   reference and do not establish R16.6/Excel parity or full report speed.
6. Only after reviewing that evidence may a separately qualified R17.8 adapter
   and company-connected report be prepared. Desktop rendering/interactions,
   export, business parity and actual Performance Analyzer timings remain
   distinct receiving gates.

If dates still differ after confirmed processing and stable bindings/storage,
keep that exact negative result. Do not infer a fix, rewrite physical dates,
guess from filenames or suppress guards. Review the remaining engine/binding
boundary with the complete report before choosing another supported action.

## Native design contract

The user requires **built-in Power BI visuals only**. Preserve separate Section
and Measure, monthly Start/End, one graph/review trend and multiple Executive
table comparisons, plus native drill/expand. Use one clean searchable selectable
file list with import UTC time and no Ctrl requirement; keep full IDs internal.
Remove duplicate file tables, Apply filters and Source selection. Trend controls
belong compactly at the right; put the dynamic title above the plot, remove
the repeated in-plot title, and prevent overlap/clipping.

The [R17.8 SAMPLE](candidate/ForecastMaster%20Compact%20Native%20R17.8%20SAMPLE.zip)
uses fabricated data and has local geometry/schema checks only. Its 1330px
page is 29.4% shorter than the prior 1884px canvas. The selection adapter is an
uninstalled draft; **no company-connected R17.8 TEST ZIP is published**. Native
matrix height does not automatically reflow the following visuals as rows expand;
do not promise dynamic page reflow. Company render/speed acceptance is open.

## Rules for the next maintainer

- Start from this file and the latest STATUS section; inspect the narrow current
  source/receipt before acting. Historical completed stages are not current
  runtime facts. Do not make the user repeat an available decision.
- Preserve the exact private R01 backup and attempt marker. Do not rerun reset,
  delete markers, repeat an ambiguous POST or change connections to clear a hold.
  Use canonical pinned endpoints; headers provide hints, not trusted endpoints.
- Treat definition operations and processing jobs as different state objects.
  HTTP 202 means accepted, not completed. Keep per-check status and timing so a
  late failure cannot erase earlier successful diagnostics.
- Preserve blanks and financial zero, source choice/completeness semantics,
  `/ABS(Benchmark)` and existing tolerances. Invalid dates are unavailable,
  never fabricated zero or guessed date values.
- Run relevant local route/state/privacy/edge-case tests before the company
  batch. Label mocks/schema checks honestly. Company results must come from
  the receiving laptop; there is no full graph authority for this repo.
- When new JSON arrives, add a safe immutable receipt, update STATUS and this
  file's current interpretation/gates together. Correct disproved assumptions
  explicitly, link the evidence, and keep failed attempts intact. Do not copy
  this project record into global memory or create competing status ledgers.
