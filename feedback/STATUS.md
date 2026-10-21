# Company setup status

Last confirmed in chat before the office-laptop handoff on 20 October 2026:

- Power BI `ForecastMaster Review`: R04.1 published on the original shared report link.
- `ForecastMaster_Actions`: R05.2 source published; `checkNativeStateR05` returned `NATIVE_STATE_READY` with the test lease released.
- `ForecastMaster_Hourly`: `checkDemandChangesR05` ran successfully, found 8 bridges, and returned `BASELINE_REQUIRED` / `NeedsRefresh: true` without reading workbook contents.
- `Refresh_only_when_changed`: expression saved; True and False branches empty.
- New hourly schedule: off.
- R05.3 notebook: prepared and locally tested, company installation pending.
- Existing `ForecastMaster_Controller` schedule: confirm its current state before the notebook update.

Next: finish SSH/VS Code setup, obtain `handoff/notebook-r05.3/INSTALL NOTEBOOK R05.3.txt`, then resume the one-time notebook update described in its README.

After installation, update this file with the date, action, output filename, observed notebook heading, and any error. The first hourly refresh, unchanged-run skip, every-day 08:00–17:00 schedule, and native on-demand button pathway remain pending.

## Receiving observations on 20 October 2026

- The operator confirmed the coordination repository opened on the Abbott laptop.
- The R05.3 installer photo shows `UPDATED: ForecastMaster_Refresh R05.3 (existing notebook ID retained)` and a saved backup under `Files/ForecastMasterRefreshState/upgrades/`.
- A later photo of the reopened notebook confirms the R05.3 heading and the default `REQUESTS` parameter cell.
- The operator selected an existing connection named `ForecastMaster_Notebook Ayush.goyal` from the OneLake Catalog. Its authentication kind and runtime permissions have not been independently verified.
- The saved hourly pipeline photo shows `Check_Demand_Metadata` connected to `Refresh_only_when_changed`, a Notebook activity in the True branch, an empty False branch, workspace `UK-ANI-Demand`, notebook `ForecastMaster_Refresh`, and string `FM_RUN_MODE=HOURLY`.
- `FM_METADATA_JSON` appears as a dynamic expression beginning `@activity('Check_Demand_Metadata...`; the photo truncates the suffix. Confirm its full value is exactly `@activity('Check_Demand_Metadata').output.output` before the first run.
- No company hourly refresh or unchanged-run skip result has been observed. Schedules were instructed to stay paused; their live toggle state is not visible in these photos.

## R05.4 correction

R05.3's automatic source compaction deletes superseded imported revisions and its maintenance path can vacuum Delta recovery files. The new R05.4 handoff removes those operations. All original R05.3 handoff bytes remain available. Current report selection remains one scenario per saved file path.

Next: receive and install `handoff/notebook-r05.4/INSTALL NOTEBOOK R05.4.txt`, confirm its reopened heading, then verify the saved expression and run one company test with no competing writer. R05.4 company installation and runtime qualification are pending.

## Latest receiving result on 20 October 2026

- The operator reports the R05.4 installer printed the expected success message and the reopened notebook shows R05.4. The installer output was not retained; this milestone is operator-reported.
- The first hourly attempt reached the Notebook activity after `Check_Demand_Metadata` succeeded. Notebook launch failed with code `2011`: `Failed to get Workspace Identity access token ... PowerBIEntityNotFound`.
- The operator then created a workspace identity. The photo shows State `Active`, ID `ab5c0278-357c-4e54-b748-e5d9cdd3c57f`, App ID `d920cd74-bfbc-4438-b39f-0e5a591c48f4`.
- The next Manage access photo confirms the `UK-ANI-Demand` identity has `Contributor` access to the `UK-ANI-Demand` workspace.
- A subsequent manual attempt again passed the metadata check but failed the Notebook activity with code `2461`, failure type `User configuration issue`: `Failed to get workspace details with http error code - 'Unauthorized'`; nested message `The caller is not authenticated to access this resource`, `isRetriable: false`.
- The latest photographed pipeline run ID is `7c8e19de-6614-49f2-80d4-c15fb575a132`. No successful hourly notebook execution, baseline advancement, semantic-model confirmation or unchanged-run skip has been observed.

Previous diagnostic suggestion, superseded by the operator's constraint below: inspect the tenant setting `Service principals can call Fabric public APIs` and confirm that its allowed scope includes this newly created workspace identity. Workspace Admin and Fabric administrator are separate roles. The setting, its group scope, connection binding and permission propagation have not been independently verified. Current notebook code and pipeline parameter values do not need speculative edits for this launch-authentication error. Keep scheduling off until receiving tests pass.

## No IT dependency: current next step on 20 October 2026

The operator cannot access Tenant Settings and explicitly requires a route that needs no IT support. The Workspace Identity route is therefore no longer the selected implementation path. No tenant setting or identity permission change is being requested.

Microsoft's current documentation describes pipeline notebook execution under the pipeline's last modified user, and its definition schema makes the notebook activity's connection reference optional. The new `handoff/pipeline-user-context-r01/SET HOURLY USER CONTEXT.txt` uses the already signed-in user's tokens to save and verify the full existing pipeline definition, omit only `Run_ForecastMaster_Hourly.externalReferences`, and read back the change. It retains the same pipeline/notebook IDs, parameters, metadata function connection, branches and other definition parts. It does not start a refresh or edit schedules, source files, workspace identity or roles.

Local synthetic qualification: 29 tests passed, including execution of the exact pasteable cell. Both new code files passed Ruff's E4/E7/E9/F checks. No company API call was made by local qualification. The GitNexus quick graph returned `ACTIONABLE_PARTIAL`; full graph impact is unknown.

Receiving next step: pull the coordination repository, close the hourly pipeline editor, and run the cell in a separate unscheduled notebook named `ForecastMaster_Pipeline_Setup` in `UK-ANI-Demand`. After a verified update, reopen the saved hourly pipeline and test one manual run. Keep the output and backup path. If the current editor requires an explicit connection again, retain its exact message before choosing another route.

Company installation of this pipeline correction, user-context notebook launch, baseline advancement, semantic-model confirmation, unchanged-run skip, hourly schedule and on-demand button remain pending. Definition update success alone does not establish runtime success.

## Current receiving state: late 20 October 2026

This section supersedes earlier pending statements while retaining them as the
setup chronology. Evidence was supplied directly in chat as screenshots and
pasted outputs; the raw screenshots have not been copied into this repository.

### Hourly: manual execution and skip confirmed; first scheduled run pending

- User-context correction saved and read back. Pipeline ID retained:
  `ef3ba5c2-3eef-4c20-bac1-a8399fa5cb20`. Backup:
  `Files/ForecastMasterRefreshState/upgrades/hourly-user-context-r01-20261020T211449999621Z-269e0b0b-cd30-404c-8a21-7f6fe6a69abf.json`.
- Manual hourly pipeline run `b92901ad-22cf-4f27-aeb7-9de8dd12aa86` succeeded.
  Notebook run `1558b8dd-82e3-4a94-88bb-b4629679e877` reported R05.4,
  Mode HOURLY, Status SUCCESS, batch
  `06571043-59f9-4f65-a056-2bb465a52e18`. Eight current report files: six
  SAME_CONTENT and two SUCCEEDED, two updated/decoded files, no StageErrors.
  ModelRefresh COMPLETED with RequestID
  `13d59473-1df7-411f-9d54-a4162eecf153`.
- Baseline fingerprint:
  `f47fa95c437ace650ada4971984c765b1f7304cdd62dfcd03e33640e4e8c9ae3`.
  Baseline receipt `metadata-baselines/06571043-59f9-4f65-a056-2bb465a52e18.json`.
- Second pipeline run `2883d1a2-d510-4b6b-9669-fb2fa5ffb994` succeeded with
  only the metadata function and If condition. Function invocation
  `feff52b7-c029-4829-90a3-ddf6b7a5973e` returned UNCHANGED,
  NeedsRefresh false, CurrentFiles 8, no changed/removed files,
  WorkbookContentsRead false and the same fingerprint. Notebook correctly skipped.
- Screenshot confirmed an ACTIVE every-day schedule at 08:00, 09:00, 10:00,
  11:00, 12:00, 13:00, 14:00, 15:00, 16:00 and 17:00, start 21/10/2026,
  end 31/12/2099, `(UTC) Dublin, Edinburgh, Lisbon, London`, modified by Ayush
  Goyal. Next-run countdown matched the next morning. First automatic run is
  still unverified; keep this working schedule active.

### Ad hoc: existing button plus manual controller confirmed

- Controller notebook settings showed empty Connection, workspace UK-ANI-Demand,
  notebook ForecastMaster_Refresh and no base parameters (REQUESTS default).
- Idle manual pipeline `868dd453-c561-4231-b97e-b6d2808c908a` succeeded:
  Pending_requests ItemsCount 3, FilteredItemsCount 0, Value empty; no Notebook
  activity ran.
- One Refresh Demand click produced
  `refresh-37337f73-89d7-4247-83e4-b6790274ea22.json`. Pending_requests reported
  ItemsCount 4, FilteredItemsCount 1, containing exactly that filename.
- Manual controller pipeline `9add1ab8-72cc-43b3-b770-40b6c123c1d0` succeeded;
  notebook `e422575d-a572-4293-946f-14a8a5ff973d`, batch
  `2f364f49-fab3-4810-a3dc-742411ea19fb`, request Status SUCCESS, all eight
  files METADATA_UNCHANGED, UpdatedFiles 0, DecodedChangedFiles 0, no StageErrors.
  ModelRefresh COMPLETED, RequestID `4caddd54-475e-4cc7-82a0-5c76fb78caa6`.
- The user rejected recurring five-minute polling because of capacity usage.
  Controller schedule stays off. Manual button-to-controller success does not
  establish automatic button pickup. Further chart validation is outside scope.

### Native automatic delivery: package ready locally, all company gates pending

The existing button writes through a SharePoint shortcut. Microsoft documents
that shortcut changes do not emit OneLake events. The unfinished wizard selects
FileCreated on native `Files/ForecastMasterRefreshState` and a subject prefix;
the 23:20 review screenshot truncates the value. Intended exact value is
`/Files/ForecastMasterRefreshState/native-requests/refresh-`. The outer rule
still targets the old controller and has not been created.

The new [native extension](../handoff/native-adhoc-r01/README.md) creates a
separate native worker and pipeline, appends a producer to the existing
Functions helpers and preserves the hourly and SharePoint items. Fifty-five
focused local tests passed. No company API or refresh was run by that
qualification. Company setup, R06 function publication, manual native execution,
duplicate-request skip, rule activation, Service button binding and automatic
button-to-completion proof are all pending. The rule must target the new
ForecastMaster_Adhoc after these setup checks, not ForecastMaster_Controller.

Published Fabric event listener baseline checked on 20 October 2026:
0.0222 CU-hours/hour (about 0.5328 CU-hours/day), plus event and applicable
rule/action/refresh consumption. This is an estimate from published rates, not
a company usage measurement. No claim of free idle event listening is made.

## Current receiving state: 21 October 2026, report-button test passed

This section supersedes the native pending gates above. Evidence consists of
operator-provided company output JSON and screenshots in this chat. The
structured [acceptance record](logs/2026-10-21-native-adhoc-acceptance.json)
retains the IDs and observed gates. No cloud action was performed by the local
documentation update.

- Setup created and read back `ForecastMaster_Native_Adhoc`, notebook ID
  `e9ce6cb0-1622-44cd-b83a-4f8680199478`, and `ForecastMaster_Adhoc`, pipeline ID
  `62dcc460-bbd0-49b7-bcce-8f95885643c3`.
- The operator published Functions R06-NATIVE-R01 and confirmed
  `submitNativeRefreshR06` alongside the three retained helpers. Direct function
  invocation returned QUEUED and native request/readiness paths.
- Manual request `eca394eb-1df7-4f98-aaf5-7a5596afcc51` completed in batch
  `48c51892-7c97-45af-a1aa-fdde5eeeb78c`; model confirmation RequestID
  `79356414-8503-4cf7-b0e4-049425435ed5`. Repeating it returned ALREADY_PROCESSED
  with the same receipt before the refresh code ran.
- Activator `ForecastMaster_Adhoc_Events` contains the Running rule
  `ForecastMaster_Adhoc_NativeRequests`. Its Definition screenshot confirmed
  Run Pipeline -> ForecastMaster_Adhoc, with Type/Subject/Source mapped to the
  corresponding event values. The empty Controller Rules pane was not evidence
  of an absent native rule; the Activator itself showed the saved rule.
- A new function request `67c5b6e5-4cdd-4d7a-92f1-cd2daba53c10` automatically
  started the native pipeline, completed in batch
  `98b28eec-6133-4cdf-9635-4d80d2e696cd`, and confirmed model refresh RequestID
  `dfe898c8-1d0b-4e7b-8590-6134168b25b4`. The overlapping run first returned
  NATIVE_WRITER_BUSY, then automatically retried and returned ALREADY_PROCESSED
  with that same successful receipt. The parent pipeline finished Succeeded.
- The report's Refresh Demand page now has a saved **Refresh Demand (native)**
  data-function button, linked to submitNativeRefreshR06 and positioned beside
  the original Power Automate button. The operator tested it in Reading view.
- The operator later clarified they clicked the native button a couple of times
  or more. Two requests, `09dcffab-186e-40d8-9191-73ee6255e68b` and
  `0b656ad4-74dc-4aca-9a88-bd7ae15b1413`, were processed together in batch
  `e925d0bf-be28-44f1-ac2e-7439df5e58de`, notebook run
  `006424d2-ab33-4e03-ac4f-c661e60a9c33`. Both request receipts show SUCCESS.
  There was one Refresh.RunID `bf224f11-f572-438e-bce7-2531bb2d6cc3`, no
  StageErrors, and ModelRefresh COMPLETED with RequestID
  `874383f4-3f2e-44bb-b885-92f242482000`. All eight files were METADATA_UNCHANGED;
  UpdatedFiles and DecodedChangedFiles were zero, as expected for this test.
- The 01:35 run list showed four automatic pipeline runs eventually Succeeded.
  One supplied overlapping attempt returned NATIVE_WRITER_BUSY; its retry
  returned ALREADY_PROCESSED for `09dcffab...` and the original batch e925d0bf.
  This verifies recovered contention and duplicate handling. It is not a
  one-click event-count test, nor proof that duplicate starts cost no capacity.

The native report-button path is confirmed for the tested operator and the
unchanged eight-source inventory. No additional ad hoc test runs are required
for this gate. Continue normal use with one click and wait for completion.

**Remaining receiving check:** at or after 08:00 London time on 21 October
2026, inspect ForecastMaster_Hourly run history for its first automatically
scheduled run. Keep the existing 08:00 through 17:00 schedule active. If sources
are unchanged, expect metadata UNCHANGED / NeedsRefresh false and a skipped
notebook. Capture the metadata output and any notebook output if one runs.
Schedule execution remains unverified until that evidence is supplied. The old
controller's polling schedule stays off; no new schedule or IT action is needed.


## 21 October 2026: Review meeting performance update prepared

The operator removed the old Run flow button and saved the Service report. Their
01:55 screenshot still shows Connected model R04.1 and a long yellow
"Loading monthly aggregates for this selection" after changing Section/Measure.
They explicitly requested demand-cycle loading followed by fast local selections.

`handoff/report-cycle-cache-r04.2/` is a prepared implementation, not a company
installation result. It loads the selected country/cycle set across all seven
measures, drivers and profiles; the remaining filters run locally. The same-GUID
visual is imported into the current saved Service report before the separate
model-feed installer is run. The source refresh system and its hourly schedule
are unchanged. The existing native button remains in the current Service report.

Local checks passed: retained arithmetic and browser regressions, native DAX
execution of all seven measures over four synthetic files/two cycles, exact
agreement between query-defined and stored expressions, installer preservation
and failure gates, refresh replacement, stale-response rejection and complete
segment loading. A 53,984-row/128-file synthetic browser test made zero host
queries for local selections, with approximately 8 ms median and 14 ms worst
measured response in that run. These are local synthetic timings, not company
capacity measurements. See the package VALIDATION.json for exact results.

**Pending:** import the R04.2 visual, run the model-feed installer, reload the
company report, and confirm local interactions and saved business values. The
first scheduled hourly run also remains unverified; this report optimization
does not turn that earlier pending check into a pass.


## 21 October 2026 - targeted hourly refresh patch prepared

`handoff/hourly-targeted-r01/OPEN THIS FIRST.txt` owns the receiving steps.
The package targets the existing R05.4 hourly notebook: exact FILES mode for
added/modified sources, ALL for removal/rename/baseline recovery/manual rebuild,
selected-scope validation, and model completion retry tracking. Raw revision
history and the existing atomic affected-file reporting replacement are retained.
Two shared detector helper changes recover from invalid metadata baselines.
The current native ad hoc endpoints and its separate notebook are preserved.

Local scope/retry regression checks: 28 passed; three runtime modules passed
strict mypy, bounded Ruff and Bandit checks. All generated notebook cells compile.
Spark/Delta integration, company installation, hourly FILES execution and measured
CU savings are NOT RUN. The previous company acceptance entries remain historical
evidence for their original versions. Repository delivery alone installs nothing.

## 21 October 2026 — executive design review, R07

This later instruction pauses the R04.2 report installation steps above. The user
requested an HTML design review before changing the live Power BI visual, and
then requested this prototype be synced to Coordination for review elsewhere.

Open [the R07 guide](../design/executive-review-r07/README.md), then open the
folder's `index.html` in a browser. It includes simultaneous driver/sector
selection, a Both chart view with each driver's total and sector lines, and a
Both table layout with driver subtotals and sector rows. Existing flat layouts,
shared scope, FY/YTG column groups and automatic ADS defaults are retained.
The preceding R06 design is available alongside it for comparison.

Local browser checks passed for hierarchy selection, partial parents, totals
without double counting, weighted share ratios, graph/table view independence,
FY/YTG expansion, ADS ranking/override/missing/ambiguous cases and responsive
widths. The receipts and sample screenshots are in the design folder.

**Pending:** user design approval, production implementation/data binding and
company performance/business-value validation. These prototype results do not
install R04.2 or change the company report, refresh system or schedules.
