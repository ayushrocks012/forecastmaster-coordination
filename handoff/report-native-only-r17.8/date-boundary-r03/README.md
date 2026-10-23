# R17.8 date-boundary R03 — one read-only diagnostic cell

R02 returned `R178_DATE_BOUNDARY_CHECK_STOPPED / RuntimeError` after its initial
read-only message. No model/Lakehouse write, refresh or publication was requested.
Its identity check had passed before that message, but it does not retain the
failing step or intermediate results. The cause is **unknown**; this is not
evidence of invalid physical dates, permissions, cancellation or a failed model
update. Preserve R02 and the existing private backup. Do not rerun R02.

R03 corrects that diagnostic weakness. It preserves per-step results and safe
failure codes/HTTP statuses; it never prints raw errors, headers, connections,
file records, source revision IDs or company amounts. After exact TEST identity
verification, definition bindings, semantic month-key counts and physical date
checks are independent. A failed definition read therefore does not suppress
the Lakehouse date evidence. Individual physical table failures remain partial.

The definition reader uses the same `x-ms-operation-id` route and bounded
360-second wait as earlier company readers, honoring bounded Retry-After.
It also accepts validated known-host operation Locations, without following
arbitrary response URLs. This addresses a fragility in R02's Location-only,
fixed 60-second reader; it does **not** establish that this caused R02 to stop.
There is one definition POST, no automatic resubmission, source conversion,
updater, refresh or publication path.

## Next steps on the company laptop

1. In the Coordination repository's PowerShell terminal, run:

   ```powershell
   git pull --ff-only
   Get-Content -LiteralPath '.\handoff\report-native-only-r17.8\date-boundary-r03\CHECK DATE BOUNDARY R03.py' -Raw -Encoding UTF8 | Set-Clipboard
   ```

2. In **UK-ANI-Demand → ForecastMaster_GM_Setup**, add **ONE NEW Python/PySpark
   cell**, paste the WHOLE file and run **ONLY that cell ONCE**. Keep the existing
   notebook Spark/Lakehouse context. Do not use Run all or alter old cells.
   Definition processing may take several minutes; normal operation polling
   is read-only.

3. Send the final JSON, including `PARTIAL` or `STOPPED`. Do not rerun the cell,
   an updater or the TEST refresh, and do not change credentials/settings.

`COMPLETED` means the requested reads completed, not that dates are valid or
the report is repaired. `PARTIAL` retains whichever reads completed alongside
the failing checkpoints. A wrong/unavailable TEST identity stops before any
definition, DAX or Lakehouse reads. Known metadata COUNTROWS blanks represent
empty counts only; financial blanks/zeroes are never read or rewritten.

R01's prior result remains: all three October file rows *inside TEST* read as
invalid IMS/EF cutoffs, including both automatic ADS sources; the native helper
matches. The physical storage versus semantic binding/loading boundary remains
unconfirmed. R03 reads the same known date fields/month keys, with no amounts.
It probes only the four expected table paths (flat or dbo-qualified) in the
already-used Lakehouse. Non-date physical columns are reported without casting.

No report/adapter/package changes are made by this revision. The optional
[compact native SAMPLE](../candidate/ForecastMaster%20Compact%20Native%20R17.8%20SAMPLE.zip)
remains fabricated data for layout review. Production R16.6 remains untouched;
there is still no company-connected R17.8 TEST ZIP or updater.

## Local evidence

Ten mocked route/identity/async/privacy/count/partial-result guards pass, with
Python 3.10 syntax validation. A small Spark-shaped fake exercises metadata
projection and failure isolation; it is not a Spark/Delta runtime test. No
company DAX, physical read, native Desktop rendering or speed test ran here.
All 1113 prior protected manifest entries retain their bytes, excluding only
the four mutable root guidance/status documents. GitNexus cannot resolve the
Coordination repository; complete graph impact remains unknown.

Microsoft documents [definition retrieval](https://learn.microsoft.com/en-us/rest/api/fabric/semanticmodel/items/get-semantic-model-definition)
and the [operation-ID polling route](https://learn.microsoft.com/en-us/rest/api/fabric/core/long-running-operations/get-operation-state).
