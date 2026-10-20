# Native ad hoc refresh R01

This adds a native OneLake request producer, a separate notebook and a separate
pipeline. It reuses the R05.4 refresh calculations, revision retention, current
file identities, model confirmation and shared writer lock. The original
hourly pipeline, SharePoint controller, notebook and Power Automate button are
retained. There is no five-minute polling schedule.

**Local qualification passed; company installation, function publication,
event delivery and automatic button completion are pending.** The installer
does not run a refresh, publish a function, create a rule or alter a schedule.

## First receiving step: install the new items

1. Leave the OneLake event wizard unfinished. Keep its tab open while using a
   separate Fabric browser tab for setup.
2. In the office coordination repository, use VS Code's terminal to run
   `git pull --ff-only` on `main`. Open
   `handoff/native-adhoc-r01/SETUP NATIVE ADHOC R01.txt` and copy the entire file.
3. In workspace **UK-ANI-Demand**, create a separate, unscheduled Python notebook
   named **ForecastMaster_Native_Setup**. Paste the copied text into its first
   code cell and run that cell. Do not paste it into the hourly refresh worker.
4. Retain the complete output. Expected messages include `Verified
   ForecastMaster_Native_Adhoc`, `Verified ForecastMaster_Adhoc`, their IDs and
   `READY: native notebook and pipeline definitions verified. No job or rule
   started.` The final exit value starts `READY: native items created and
   verified`.

The setup uses the signed-in user's existing permissions. It creates only
`ForecastMaster_Native_Adhoc` (Notebook) and `ForecastMaster_Adhoc` (DataPipeline),
then reads their definitions back. The maintained notebook supplies its existing
default Lakehouse binding. Matching existing native items are verified without
overwrite; different definitions or ambiguous names stop setup. If an operation
is pending or the API rejects a request, retain the exact output before retrying.
Nothing in this package calls tenant settings or requires an app registration.

## Subsequent steps, after the receiving output is checked

Follow these one stage at a time and retain each result.

1. Publish the full **ForecastMaster-Actions-R06-native.txt** source into the
   existing **ForecastMaster_Actions** item. It includes the three original
   R05.2 helper functions unchanged and adds `submitNativeRefreshR06`, using the
   existing `ForecastMaster` Lakehouse connection alias. Preserve the Functions
   item's current bindings and dependencies. Publish success is a separate gate
   from successful invocation.
2. Test only `submitNativeRefreshR06`. Expect `Status: QUEUED`, a new `RequestID`,
   a `RequestFile` under
   `Files/ForecastMasterRefreshState/native-requests/refresh-<GUID>.json`, and a
   readiness receipt under `native-ready`. QUEUED means accepted, not completed.
3. Manually run the new **ForecastMaster_Adhoc** pipeline. Set its **Subject**
   parameter to `/` followed by the returned `RequestFile`. Leave Type and Source
   blank for this manual test. Expect the Notebook activity to succeed, the
   returned batch/request receipts to show SUCCESS and `ModelRefresh.Status` to
   show COMPLETED. UpdatedFiles may legitimately be zero for unchanged sources.
4. Run it again with exactly the same Subject. Expect `ALREADY_PROCESSED`, the
   same request receipt and no new ingestion/model refresh. A notebook session
   can still start for this duplicate event. Failed requests retain their failed
   receipts and do not become green IDLE results on a retry.
5. Return to the unfinished OneLake event wizard. Use only
   `Microsoft.Fabric.OneLake.FileCreated`, Lakehouse ForecastMaster, folder
   `Files/ForecastMasterRefreshState`, and this exact header filter:

   | Field | Operator | Value |
   | --- | --- | --- |
   | subject | String begins with | `/Files/ForecastMasterRefreshState/native-requests/refresh-` |

   The review truncates long values: use Back to check the full value before
   Finish. The prefix excludes batches, ledger writes, readiness receipts,
   baseline files and upgrade files, avoiding refresh-output event loops.
   Native OneLake events do not cover files reached through the SharePoint
   shortcut, which is why the existing controller cannot serve this new rule.
6. After Finish returns to **Add rule**, name the rule
   `ForecastMaster_Adhoc_NativeRequests`. Check **On each event**, choose **Run
   Pipeline**, and change the Fabric item to **ForecastMaster_Adhoc**. Map
   Subject to `__subject`, Type to `__type`, and Source to `__source`. Save in
   UK-ANI-Demand with an Activator named `ForecastMaster_Adhoc_Events`. Review
   the exact target and listener capacity implications before Create.
7. In the existing report's Refresh Demand page, add a **data-function button**
   alongside the existing Power Automate button, bound to
   ForecastMaster_Actions -> `submitNativeRefreshR06`. Power BI supports this in
   the Service editor. Use a distinct label such as **Refresh Demand (native)**.
   This is a request button, not a chart or report-calculation change.
8. Click the native button once and **do not manually run a pipeline**. Retain
   the returned RequestID, automatic pipeline run, successful request receipt
   and confirmed model refresh. This is the company automatic-delivery gate.
   Retain any exact failure; QUEUED alone does not pass it.

The hourly schedule remains active at 08:00 through 17:00 every day in the London
time zone, starting 21 October 2026. Its first scheduled run remains a separate
receiving check. Leave the old controller polling schedule off.

## Capacity and reliability boundaries

The native rule removes the repeated idle controller pipeline runs. It is not
free. Microsoft's published Fabric-event listener rate checked on 20 October
2026 is **0.0222 CU-hours per hour**, approximately **0.5328 CU-hours per day**
for one continuously existing listener, plus event operations, applicable
Activator processing, data-function writes, pipeline activities, Spark and model
refresh. This is a published-rate baseline, not measured company consumption.
An active Activator also has rule-related consumption; do not substitute the
Fabric-event listener number for a complete price estimate. Microsoft states
that stopping a rule does not stop its listener's consumption.

For comparison only, five non-copy controller activities every five minutes
would account for 5 x 288 x 0.0056 = 8.064 CU-hours/day at the published pipeline
activity rate, excluding refreshes. This is an estimate for continuous polling,
not the usage of the current, unscheduled controller.

An Azure Data Lake upload can emit FileCreated before final flush. The producer
therefore reads back the request and publishes a separate SHA-256 readiness
receipt. The worker admits only ready requests; a target not ready or a busy
shared lock fails without acknowledgment. The new Notebook activity has five
retries at 120-second intervals, triggered only by a delivered request event.
A longer lock conflict or service outage can exhaust these retries and requires
review of that failed run; there is no claim of an unlimited delivery guarantee.
Duplicate events skip completed requests before the refresh imports run.

## Package, verification and evidence

- `SETUP NATIVE ADHOC R01.txt`: one pasteable setup cell.
- `ForecastMaster_Native_Adhoc.ipynb`: separate event worker.
- `ForecastMaster-Actions-R06-native.txt`: full Functions source with native
  producer appended to the original helpers.
- `native_producer.py`, `native_consumer.py`, `native_preflight.txt`,
  `install_native.py`, `build_native.py`: reviewable source and deterministic
  rebuild (`python handoff/native-adhoc-r01/build_native.py`).
- `test_native_adhoc_r01.py`, `validation-unit.xml`, `VALIDATION.json` and
  `PRESERVATION.json`: exact local evidence. Original handoff packages retain
  their prior recorded bytes in HANDOFF-MANIFEST.json.

Run the new unit checks together with the retained worker's tests:

```bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest \
  handoff/native-adhoc-r01/test_native_adhoc_r01.py \
  handoff/notebook-r05.4/Refresh/tests/test_request_worker.py \
  -q -p no:cacheprovider
python tools/verify_handoff.py
```

No company APIs, Spark engine, report publication or workbook calculation rerun
were exercised by these synthetic tests. Unchanged calculation modules are
checked against their retained parent cells and source files. GitNexus impact
was unavailable because the WSL root filesystem was full; direct tracing and
focused tests supplement it, without claiming complete graph coverage.

## Official references checked on 20 October 2026

- [OneLake event source, filters and pipeline actions](https://learn.microsoft.com/en-us/fabric/real-time-hub/set-alerts-fabric-onelake-events)
- [Fabric event capacity rates](https://learn.microsoft.com/en-us/fabric/real-time-hub/fabric-events-capacity-consumption)
- [Activator capacity accounting and listener lifetime](https://learn.microsoft.com/en-us/fabric/real-time-intelligence/data-activator/activator-capacity-usage)
- [Pipeline activity consumption](https://learn.microsoft.com/en-us/fabric/data-factory/pricing-pipelines)
- [Power BI data-function buttons, including Service authoring](https://learn.microsoft.com/en-us/power-bi/create-reports/translytical-task-flow-button)
- [Create Fabric item API and supported caller identities](https://learn.microsoft.com/en-us/rest/api/fabric/core/items/create-item)
- [Pipeline Notebook activity definition](https://learn.microsoft.com/en-us/rest/api/fabric/articles/item-management/definitions/datapipeline-definition#tridentnotebook-activity-properties)
