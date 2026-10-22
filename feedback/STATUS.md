# Company setup status

## 22 October 2026 — R16.6 corrects aggregate Share and shortens Demand table

The operator's R16.5 screenshots show numeric S&OP results and an aggregate Share
that does not equal the visible Abbott/Market ratio. Direct tracing and a replay
against R16.5 reproduce the paired-member mask defect: missing Abbott removed
valid Market from the ratio denominator while Market's amount row retained it.
R16.6 aggregates the two sides independently under SUM_AVAILABLE_V1, then divides
the period totals. Both Demand/S&OP Units and Value Shares use that rule. Source
values, missing flags and strict single-tier behavior remain unchanged. Known
mixed-currency value populations use the same configured FX basis on both sides.

The operator clarified that the reported year-formatting difference meant dash
versus $0. These remain unavailable versus numeric-zero states; S&OP cell tooltips
explain them. No historical blank was converted to zero. A later request also
removes the repeated Demand header date subtitles and two-line sector/driver
labels. Exact ranges remain in tooltips; flat labels are Sector – Driver, while
hierarchy view names the driver once. Partial counts move to tooltips. In local
before/after tests, row height falls from about 52px to 29px, with 80 numeric cells
preserved and expansion retained. Native scale/height still needs receiving review.

A bounded independent synthetic review passes 1,728 numeric/rendered assertions
across all 18 displayed S&OP measures, Units/Value, exact FY/YTD/YTG/H1/H2 windows,
IMS/EF cutoffs, run rate, same-period PY growth, source net/channel amounts, signed
leaves counted once and Demand reconciliation. A further 720 randomized oracle
comparisons test asymmetric missingness, ratio populations and mixed-rate/cache
behavior. Existing numeric/selection/cache/FX/hover and hierarchy controls pass.
This is report-runtime evidence, not an exhaustive workbook/formula audit or
actual company-source reconciliation. The source workbook/data was not changed.

TypeScript/package lint and ten available project-schema checks pass. Two retained
visualContainer 2.14.0 schema URLs remain unavailable. GitNexus impact/scope remains
partial/UNKNOWN; direct tracing/tests supplement it. All 56 R16.5 tracked files
are byte-preserved. The original connection/feed, native Refresh Demand and
rollback source are retained in a new private PBIP/ZIP. No company model/Fabric/
Service item was changed or published. No setup/model refresh is needed. Native
rendering/zoom/drag, company reconciliation, measured speed and publication remain
receiving gates. Public receipts contain synthetic observations only.


## 22 October 2026 — R16.5 corrects interpolated monthly hover

The operator reported tooltip amounts changing on tiny pointer movements although
the source data is monthly. Direct source inspection and a synthetic replay of
the preserved R16.4 package reproduce this in both Demand and S&OP: the label
rounded to a month while the amount interpolated between adjacent month points.

R16.5 reads the nearest existing monthly point and snaps guide/markers to it.
Values stay fixed until the nearest month changes. Blank points are not filled;
zero, a valid neighbour, the final month and a single-month view remain usable.
If no selected series has data, the tooltip says so. Pinning and logical zoom
coordinates are retained; drawn lines and numerical calculations are unchanged.

Local package tests pass for both modes at 50%, 80% and 100%, exact actual/
forecast/trend amounts, USD conversion and weighted Share, boundaries/pinning,
blank/zero and endpoints. The viewport regression now requires identical monthly
tooltips across zoom, replacing its former interpolation tolerance. TypeScript,
package lint/build, aggregate/selection/cache/FX and ten available project-schema
checks pass. Two retained schema URLs remain unavailable. The full R16.4 numeric
engine, source/transport, layout/viewport/order, setup/rules and all 59 tracked
R16.4 files are byte-preserved. GitNexus remains partial/UNKNOWN and is supplemented
by direct tracing and focused tests. Original connection/feed, native Refresh
Demand and rollback source remain preserved in a new private PBIP/ZIP. No company
source/model/Fabric/Service content was modified. Setup/model refresh must not be
repeated for this update. Native rendering/zoom/drag, company reconciliation,
measured speed and publication remain receiving gates.


## 22 October 2026 — R16.3 received; R16.4 native canvas, periods and ordering

The operator's screenshots confirm R16.3 opens with the compact cascading scope
and two native pages. Native zoom still exposed roughly the same viewport, and
the operator explicitly preferred familiar native controls over an internal zoom
toolbar. A tiny outer margin at Fit to width was reported; that alone does not
establish a rendering defect. R16.4 is a separate report-only candidate with a
1440 x 2400 native canvas/matching visual, opening at FitToWidth. Its default
synthetic Demand/S&OP content fits that height, allowing native-style zoom to
expose more content. Very large expanded detail retains a safety content scroller.
Actual native Desktop/Service zoom acceptance remains unexecuted here.

The same third Review summary period dropdown now sits beside driver/tier choices
on both modes, with search and filtered Select all/Clear all. Selected periods
carry across mode navigation, stay constrained to Review months' years and remain
empty after explicit clearing. FY/YTD/YTG and exact H1/H2 windows are supported.
The Demand headline compares every selected period in one Plan/trend matrix.
Actuals-only periods say so and omit redundant table variance columns; detection
uses exact months against saved cutoffs, including past FY and future YTD cases.
The lower executive toolbar keeps Table rows left, Trend comparisons right, and
the shared-scope caption/Hide alongside the heading.

S&OP allows hold-drag within each hierarchy level and Reset order. The table and
graph legend follow that order. Default grouping keeps all Contracts contexts
together; source order within parents and the source catalogue remain unchanged.
Pointer tests verify all three move levels, rejected cross-parent movement,
keyboard/cancel, reset and saved-order restore without changing values or ticks.

Local TypeScript/package lint, synthetic numeric/transport regressions, 500-tier
cascade, period integration, pointer dragging and canvas geometry pass. Browser
interactions/resize use the cached data without new fetches. Ten available schema
checks pass; two preserved 2.14.0 visualContainer schema URLs return 404. The full
R16.3 engine/source helpers/setup/rules and all older tracked handoff files remain
byte-preserved. Original connection/feed expressions, native Refresh Demand and
rollback PBIX bytes are retained in a separate private project/ZIP. GitNexus
impact/scope evidence remains partial/UNKNOWN and is supplemented by direct
tracing and focused tests. No company source/model/Service item was modified.
Do not repeat the successful setup. Native zoom/drag, company reconciliation,
measured speed and publication remain receiving gates.


## 22 October 2026 — R16.2 received; R16.3 corrects totals and navigation

The operator's R16.2 screenshots confirm native loading and numeric results in
both review modes. They identified incomplete driver-level history caused by
strict tier guards, a tier dropdown still listing unselected drivers, ineffective
content zoom, and mismatched header/filter placement. They clarified that the
GM needs available-value driver totals even when an individual tier has a gap.

The application-owned BR-018 later SUM_AVAILABLE_V1 display policy and current
operator_formulas/sector_summary code already support available-member display
sums. R16.3 applies that rule monthly and fits trends on the selected aggregate.
Individual tier gaps remain unavailable; a wholly unreported month or missing/
ambiguous source remains unavailable. Source data and leaf formulas are unchanged.
The earlier R16.2 strict aggregate rule is superseded for this GM display.

Forecast tiers now cascade from selected drivers, with parent scope independent
of child ticks. Both review modes share matching calendar/source/filter geometry,
reserving blank Section/Measure positions in S&OP. Host viewport updates scale
cached content and hover coordinates without a data reload. Synthetic Edge tests
pass at 50%, 80%, 100% and approximately 103%, including resize-only updates with
no dataViews. Native work-laptop zoom remains a separate receiving check.

The operator questioned the duplicate native S&OP page. The new candidate has
GM Review and Refresh Demand only; Demand and S&OP are two modes of the SAME
review instance, avoiding independent duplicate selections/data loads. Existing
three-page projects remain untouched rollback copies. The native refresh page,
original source bytes, model connection, feed expressions and setup are preserved.
Do not repeat the already successful reporting setup or native model rebuild.

Local TypeScript/packaging, synthetic aggregate/detail, source/cascade, 500-tier,
FX/Share, transport/date, refresh-cache, paired-header and viewport checks pass.
Ten project files validate against Microsoft schemas; two preserved visual
containers have unavailable 2.14.0 schema URLs. Company R16.3 rendering, source
totals, native zoom, measured speed and publication remain receiving gates.
GitNexus impact remains partial/UNKNOWN and is supplemented by direct tracing
and tests. No cloud content or company source was modified or published.

## 22 October 2026 — R16.1 company load passed; R16.2 compact correction

The operator confirmed that R16.1 opens and retrieves saved reporting data.
The reporting setup returned READY with a rules backup. A subsequent native
refresh returned SUCCESS, no stage errors, rebuilt the review projection and
confirmed ModelRefresh COMPLETED. Screenshots show numeric Core Oral and Paed
SIP rows. Those receiving results supersede the earlier pending setup/load notes.

The old selector exposed every model driver despite only two usable ADS driver
sources. Its long checkbox tree, nested scrollbars and repeated FY/YTD/YTG
headline/shortcut text crowded the page. The authorized separate R16.2 package
uses source-aware searchable driver/tier dropdowns, stable scope identities,
one labelled headline period and a single vertical content viewport. It keeps
every selected executive-table period and existing graph/table numeric rules.
Inactive S&OP channel rows are more compact; active bridge contexts retain order.

A read-only Market Value history check for Sep 2025–Aug 2026 found 12 complete
months for Vegan, but 11 or 8 for Vegan 2K across returned source revisions,
with 1 or 4 missing cells. Thus a Plan may exist while its full-scope 12M trend
is unavailable. Removing that tier legitimately changes Plan and can restore
the remaining scope's benchmark. R16.2 explains incomplete history; it never
fills missing values, switches training windows or repairs company source data.
Actual-only YTD retains actuals, so its trend variance remains zero.

Local packaged Edge tests pass for 500 tiers across ten drivers with a constant
selector height below 160px at desktop width, source preference and exclusions,
selection/reselection arithmetic, complete-data guards, shared internal review
navigation, FX/Share, refresh invalidation and one vertical content scroller.
All 31 tracked R16.1 files and exact numeric/transport functions are preserved.
The setup/rules are unchanged: do not repeat the already completed company setup.

The new private project/ZIP preserves the source report and native Refresh Demand
page. No company report was published. R16.2 Desktop rendering, source-total
reconciliation, measured company speed and eventual published-button checks
remain receiving gates. Public code and receipts contain synthetic data only.
GitNexus impact remained partial/UNKNOWN, supplemented by direct tracing and
focused tests; no zero-impact conclusion is claimed.

## 21 October 2026 — R16 opened; clean model grain; R16.1 reader correction

The operator opened all three R16 pages in Desktop on the work laptop. During
the initial model load, before the one-time S&OP setup, a missing-fields message
was followed by `Duplicate monthly component. Complete totals withheld`.
The working source PBIX did not have that failure.

A user-run read-only DAX query found 216,384 fact rows in 216,384 monthly groups,
zero groups with multiple rows and maximum group size one. The axis has 84 rows,
84 distinct dates and zero non-month-start dates. These diagnostic counts show
no source-grain duplication; no company fact or calendar cleanup was performed.

R16's date decoder sliced zoned timestamp strings before reading the local
calendar month, unlike the working R04.2 reader. Synthetic London timestamps
reproduce the exact duplicate error across the spring clock change. The new
`handoff/report-gm-desktop-r16.1/` restores the working date handling; 84 months
pass across four time zones. Actual company DataView bytes were not inspected.
Identical aggregate-delivery replay, raw blank/empty aggregate identities,
metadata carriers, conflicting amounts/missing counts and complete-period
guards have focused regressions. Empty startup views now wait for data.

The replacement retains the same visual GUID with version 16.0.1.0. Reporting
rules/setup and business formulas are unchanged, and all 28 tracked R16 files
are preserved. Local TypeScript, packaging, reader and packaged-browser checks
are separate from R16.1 company rendering, reconciliation and speed, which
remain pending. No company setup, source change or publication was performed.
Open the replacement in a separate folder and verify the first load before
continuing the existing one-time S&OP setup and publication checklist.

## 21 October 2026 — R16 Desktop candidate prepared, company opening pending

The user authorized the approved paired design in Power BI Desktop and supplied
a thin Redesign PBIX. The new private generated project has Demand review,
S&OP review and the unchanged separate Refresh Demand page. The old Review
meeting page is absent from the new project. The original PBIX and all four
Refresh Demand definition files are verified byte-preserved. The existing live
semantic-model connection is retained; no Service report was changed/published.

The public implementation is `handoff/report-gm-desktop-r16/README.md`. Its
production bundle uses saved bridge components rather than illustrative values.
Twelve additive reporting definitions supply the missing S&OP identities;
existing leaf ADS components are reused. Setup is a separate user-run notebook
cell with a rule backup, readback, shared writer lease and concurrent-change
guard, followed by one normal native request to rebuild reporting and refresh
the model. No company setup/refresh was performed by this task.

Local TypeScript/packaging lint, numeric edge cases and packaged-browser checks
passed with 17,280 explicitly synthetic monthly rows. Both views reconcile on
known fixture totals; zero/missing FX, weighted share, complete training/period
windows, visibility, local selections and refresh invalidation are checked.
Eleven project files validate against public Microsoft schemas. Three visual
containers retain the source 2.14.0 schema, whose public URL returned HTTP 404;
that part remains unvalidated. Desktop native opening and live DAX/model
execution are pending because local Computer Use failed before app inspection.
These files are a PBIP candidate, not a claimed Desktop-saved PBIX.

Use internal review navigation to carry selections/rates between views; native
Power BI page tabs maintain separate visual sessions. Company reconciliation,
initial load/interaction speed, published native-button operation and final
publication remain receiving checks. All previous HTML/handoff packages remain
unchanged.

## 21 October 2026 — R15 simplifies rates to source currencies

The user removed plan-year and country/Affiliate-specific rate inputs. The
current paired HTML proposal is `design/currency-plan-review-r15/`. Plan rates
is always visible in either page's header, including Units view. It lists one
quote per distinct currency in the base metadata, such as **1 GBP = [rate] USD**.
Rates are shared by currency across both pages, with no plan-year state.

The multi-Affiliate conversion model defaults Value to USD, converts each source
currency's contributions separately and sums their USD values. Missing required
rates withhold the complete total, mixed raw currency totals are rejected and
USD itself has an implicit rate of 1. The visible base remains the existing
UK/GBP sample; no other Affiliate or currency was invented for the UI. Isolated
GBP/EUR/USD fixtures validate future conversion plumbing and do not constitute
live multi-Affiliate data or page binding.

The named return point **Before currency-only rates — Plan-rate Review R14**
binds all 31 prior R14 files in
`design/checkpoints/before-currency-plan-review-r15.json`. Every earlier saved
package remains byte-preserved. The existing interaction checks retain 1,320
baseline numeric comparisons, while the currency checks cover simplified
controls, shared edits, monetary conversion, percentage preservation, missing,
zero and invalid FX, multi-currency summation, state restoration and narrow
light/dark layouts. See both R15 validation JSON files for the exact evidence.
Rates shown in check screenshots are artificial; no business rate is prefilled.

Power BI, Fabric, application source and workbooks are unchanged. Official rate
storage, actual multi-Affiliate/currency sources, shared page binding, numerical
reconciliation, refresh/cache checks and live performance remain implementation
work awaiting design approval.

## 21 October 2026 — R14 plan-rate controls on both HTML pages

The user authorized adding plan rates to both HTML pages, preserving the current
versions and syncing Coordination, with Power BI explicitly unchanged. The new
package is `design/plan-rate-review-r14/`; open `design/index.html`, select R14
and choose **Value** to reveal **GBP / USD** and **Plan rates** in the header.

The user chose one selected plan-year rate for the entire review, including
historical and forecast years. Rates are keyed by Affiliate/local currency/year
and shared by both pages. No actual business rate or extra affiliate is supplied:
the only sample Affiliate remains UK/GBP. USD values stay unavailable until a
numeric rate is entered. Numeric zero remains zero. Units, Share, business
growth, variance percentages and ranking remain independent of FX. Monetary
actuals/forecasts/trends/plans/absolute variances/run rates convert once, with
currency labels updated throughout.

**Before plan rates — Connected GM Review R13** is the saved return point at
`design/checkpoints/before-plan-rate-review-r14.json`, binding all 21 preceding
paired-page files. R13 and every earlier saved package remain byte-preserved.
Open the saved R13 link in the design chooser to revert the preview.

Local FX qualification compares 576 Demand and 972 S&OP observations directly
with R13 in units/GBP, then performs 1,548 USD/percentage-preservation comparisons
at explicit artificial test rates. It covers prior/current/future review years,
different stored annual rates, bidirectional edits, missing/zero/invalid input,
Apply/Cancel/Escape, monthly amounts, state persistence and light/dark layouts at
1080/1024/736/390/320px. The inherited interaction check also retains its 1,320
older-baseline numeric comparisons. See the R14 validation JSON files and saved
hash receipt for the exact local results. Fixture rates in screenshots/checks
are illustrative inputs, not official or prefilled business plan rates.

HTML storage is local to the preview; there is no company rate-table write.
Actual Affiliate/currency metadata, official rate storage/editing, common source
binding, cross-page numeric reconciliation, refresh/cache checks and measured
Power BI speed remain live-implementation work. No report, model, visual,
Function, Fabric rule/pipeline, application source or workbook was changed.

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

## 21 October 2026 — R08 proposal and named R07 baseline

The user requested seeing the executive improvements while preserving the
preceding design for comparison or return. **R07 — Driver and Sector Review**
is saved unchanged at `design/executive-review-r07/`, with the named Git tag
`design-driver-sector-r07` and checkpoint record in `design/checkpoints/`.

**R08 — Executive Overview** is a separate proposal in
`design/executive-overview-r08/`. Open `design/index.html` to choose either.
It adds a dynamic plan/variance observation, offsetting driver movements,
actuals/YTG/source context, clearer control labels, period dates and graph
shading, direct combined-chart labels, signed variance bars and explicit ranking.
R07's selection, Both views, arithmetic and ADS rules are retained.

Local synthetic browser checks passed for both the new executive information
and the retained hierarchy/source-selection cases. The refresh timestamp in
R08 is explicitly sample metadata. Neither design constitutes production
installation, live speed evidence or approval. The report implementation pause
remains in force while the user reviews the two versions.

## 21 October 2026 — R09 period-review improvements

R09 adds quick FY/YTG comparison, a separate overview for every selected period,
explicit overcall/undercall wording, trend-fitting history dates, forecast start
dates and numeric driver-period captions in Both graph mode. The new comparisons
and retained hierarchy/source-selection browser checks pass on synthetic data.
R07 and R08 remain preserved; the live Power BI report remains unchanged.

The user also requested removing variance bars. That step is pending the
session's required direct opt-in; the assistant requested it and continued
the independent improvements. Bar removal has not been performed or validated.

## 21 October 2026 — numeric variance table updated

This supersedes the pending bar-removal note above. The user provided the
explicit opt-in and requested a regenerated preview. R09 now displays the
standard numeric variance table without the small bars beneath Absolute.
Before/after numeric values and displayed number strings agree across default,
FY/YTG and multiple-measure/cycle views. The preview and screenshots are
regenerated. R07 and R08 remain unchanged, and no live Power BI changes were made.

## 21 October 2026 — R10 GM review proposal

The user approved applying the six GM-review refinements to HTML only and
explicitly retained the Power BI pause. R10 is separately saved at
`design/executive-gm-review-r10/`; open it from `design/index.html`.

Period selection now precedes the overview, the chart follows the selected
review period, and driver totals expand into sectors. Flat sector and Both
views remain available with one shared scope, explicit ranking periods,
frozen row names, unit-aware variance headings and selected-total labels.
ADS defaults, matching-file access and all numeric values remain intact.

Browser checks passed: 819 raw/formatted numeric cells match preserved R09
across seven scenarios; source-selection regressions, responsive layout and
light/dark rendering pass. The synthetic warm-render measurement is recorded
in `validation-gm-review.json`, with no requests during warm interactions.
It is not a measurement of company Power BI response time or production cache
invalidation. The GitNexus HTML-symbol/change-scope checks were unavailable or
incomplete; the source-preservation receipt and browser checks are the bounded
verification here. R07, R08 and R09 remain unchanged.

Pending: user design approval, followed by separately authorized Power BI
implementation and realistic performance/freshness validation. No report,
model, custom visual package, notebook, function or schedule was changed.

## 21 October 2026 — R11 restores month calendars

The user corrected R10's control placement. R11 restores visible From/To month
calendars at the top beside broad business filters and puts FY/YTG back in the
executive-summary controls. Chart months and summary periods are independent;
neither summary-period nor cycle changes reset the chosen chart range.

Browser checks pass for placement, calendar/summary independence, actual graph
points after date changes, reversed ranges, retained executive interactions,
source selection and responsive layout. All 819 numeric cells again agree with
preserved R09. R10 and previous versions remain unchanged. This is an HTML-only
proposal; production installation and speed/freshness validation remain paused.

## 21 October 2026 — separate S&OP build-up page R01

The user accepted the first-page R11 design and requested a second page that
builds its graph and table from the same progressive selections. The new
`design/sop-build-up-r01/` proposal is separately saved and linked in the chooser.
R07–R11 retain their recorded bytes.

The measure hierarchy follows Community's Market/share/Abbott/PI/net/factor
observations, Community Ex-factory ADS and its Wholesaler/Northern Ireland
children, plus Contracts and its seven source subchannels. No additional
cross-channel Contracts total is introduced. Units/Value switch together;
percentages are separate from amount graphs. The table offers FY/YTD/YTG or
the visible month range, while driver/sector scope is shared with the graph.
Optional stacked composition assigns each of eleven publishing leaves once,
even when selected parents and children overlap.

Synthetic browser validation passed 58 reconciliation comparisons, selection
and grouping interactions, distinct IMS/EF cutoffs, monthly/summary independence,
hover/touch details, empty states, responsive widths and light/dark rendering.
Warm local interactions generated no network requests. The saved timings do
not measure company Power BI performance. Current repository contracts informed
the hierarchy; workbook inputs were not read or copied. The existing GitNexus
HTML coverage limitation is retained rather than claiming a complete graph gate.

Pending: second-page design review, followed by separately authorized live
implementation, reviewed ADS source binding and actual freshness/performance
qualification. No application business code or Power BI/Fabric items changed.

## 21 October 2026 — S&OP left/right panel proposal R02

The user requested a floating-style selector on the left with channel and
subchannel buttons that toggle the graph and table on the right. Period controls
and shared driver/sector scope now sit above both columns. A Hide/Show selector
control changes layout without changing data. Buttons toggle independently,
including parent totals; the panel is the only channel-selection surface.

`design/sop-side-panel-r02/` is separately saved. The numerical fixture and
business rules remain those of R01. Local checks cover the new click/keyboard
behavior, placement, hide/show preservation, existing reconciliation and
responsive behavior, plus raw/formatted parity against R01. The receipt records
the exact scenarios and counts. All preceding design packages remain preserved.

Microsoft's current button-slicer and bookmark documentation supports the
anchored-panel design direction. Exact receiving-version selection behavior,
measure binding, layout reflow and production speed remain unqualified. The
prototype does not claim a freely draggable Power BI window. No live Power BI
or application business changes were made.

## 21 October 2026 — R03 follows the user's sketch

The user requested lean lines and supplied a sketch of two straight toggle
columns beside a graph, with the table below it. R03 at
`design/sop-channel-table-r03/` follows that arrangement. It retains channel
context, independent toggles, shared graph/table selections, top period/driver
controls and optional monthly columns. Bar view is removed, including restoration
from old state. R01, R02 and R07–R11 remain preserved.

Local checks pass for the new arrangement and retained behavior: 58 numerical
reconciliations, 385 raw/formatted cells matching R01 across five scenarios,
keyboard/hover/touch interactions and responsive light/dark rendering. These
are synthetic design checks. No live Power BI or application changes were made.

## 21 October 2026 — R04 separates three business roles

The user requested Channel, Sub-channel and Measure instead of two mixed
columns. R04 groups parent totals, real source subchannels and IMS/ADS measures
separately. Units/Value remains above. Ex-factory ADS can hide/restore the chosen
channel/subchannel lines and table rows without discarding those choices; the
off state is explicit. IMS references stay on the Community basis.

The new behavior and retained line/table controls pass locally, with 58
reconciliation comparisons and 385 cells matching preserved R01. All earlier
design packages remain unchanged. Actual source binding and production speed
are unverified; no Power BI or application source changes were made.

## 21 October 2026 — R05 uses spaced bands and a shared right axis

The user clarified that floating buttons meant spacing: Community and its
measures at the top, Contracts beside Homecare/Hospital, and Retail in a separate
lower band. R05 follows that sketch with three aligned columns and expandable
extra choices. The user then requested Share on the same graph's right axis and
the summary to build selected periods in bridge order. Amounts retain their
left scale, percentages use the right scale, and hover values follow each
series' unit. Summary period selection is beside the table; row order is fixed
to the bridge story regardless of the click sequence.

`design/sop-spaced-groups-r05/` is separately saved. Local checks cover the new
spacing and expansion, both numeric axes, ratio-only display, period selection,
bridge row order, 58 numerical reconciliations and 388 raw/formatted cells
matching R01 across five scenarios. Responsive widths and light/dark rendering
pass. Warm interactions make no network requests; their synthetic timing is not
Power BI performance evidence. Previous design packages, including approved R11
and R04, remain byte-preserved. No workbook, application source or live Power BI
content changed. Design approval and separately authorized live work are pending.

## 21 October 2026 — R06 corrects cascade, labels and bridge identities

The user identified that R05's columns were independent, Ex-factory Cur was not
explicitly selectable, Units/Value captions were inconsistent and measure order
did not match the bridge. R06 now cascades Channel → target total/subchannel →
Measure. Community IMS requires its blank-subchannel total. Wholesaler alone
has its own Ex-factory choices. Channel off removes dependent series while
remembering choices; empty target selections disable Ex-factory measures.

The retained neutral V18 identities for Core Oral and Paed SIP were inspected
directly, along with the maintained common-layout and binding source. The new
sanitized catalogue records 44 direct measure identities and five explicit
review aggregates/diagnostics, including separate Cur/Pub/ADS, the IMS basis of
net IMS, Out of Pocket → Retail and source context order. It includes no source
values, formulas, products or customers. The user-requested executive primary
order is Abbott IMS, Market, PI, Ex-factory at Community total, followed by the
other source contexts. Cur/Pub observations are additional synthetic fixtures;
they are not claims about receiving data or a renamed ADS feed.

The selector, legends, tooltips and table now change all relevant names between
units and value, including unit/value share on the same graph's right axis.
The summary labels each channel/subchannel context and keeps selected periods
beside the table. Local checks pass 12 behavior groups, 102 reconciliation
comparisons and 372 existing ADS/IMS cells matching R05 in five scenarios.
Responsive light/dark layouts and warm local interactions also pass. GitNexus
reported stale authority; bounded current-source/descriptor inspection supplied
the lookup evidence without refreshing the index. No actual workbook or live
Power BI content was modified. Earlier designs remain preserved; design review,
real source binding and company performance qualification remain pending.

## 21 October 2026 — R07 source-only selection and broad filters

The user prohibited invented Channels, Sub-channels and Measures and requested
missing broad filters, including Affiliate. The separately saved R07 second-page
prototype removes R06's derived Contracts combined contexts, effective uplift
and matched-calendar diagnostic. Its exposed catalogue contains only 44 direct
retained source identities, an executive subset rather than every bridge field.
There is no preselected Channel, context or Measure. Choosing a Channel enables
its source choices without adding a graph series or table row. Graph and table
show only explicitly selected valid combinations. Real blank contexts stay
blank; no IMS allocation to Wholesaler or Contracts is created.

The top now includes searchable Affiliate, Demand cycle and source Section,
Units/Value and the visible calendars. Shared driver/sector choices have search;
Channel/Sub-channel/Measure remain solely in the left selector. Only the
confirmed UK sample Affiliate is offered. Clearing Affiliate clears results;
Section filters applicable measures without changing the IMS/EF cutoff basis.
Units/Value changes measure names throughout, and Share keeps the right axis.
FY/YTD/YTG periods remain independent from chart/monthly dates.

Local integration checks passed 11 groups, 66 reconciliation comparisons and
264 retained source-measure fixture values matching saved R06. Responsive
light/dark layouts, cross-series hover, explicit selection gates and zero warm
network requests/script errors were checked. All 172 preceding saved design
files were verified against their prior manifest hashes. Numeric data remains
synthetic; this is not full source binding or Power BI speed evidence. No live
report, Fabric item, workbook or application source was changed. Design approval
and live implementation remain separate pending gates.

## 21 October 2026 — R08 aligns Sub-channel contexts and simplifies measures

The user removed Section and questioned Selected scope's role, identified the
misleading vertical alignment between blank-Sub-channel IMS measures and
Wholesaler, and requested removing Cur/Pub from this executive page. R08 gives
every source context its own aligned row. Community blank owns Share, Abbott
IMS, Market, PI, IMS minus PI and ADS; Wholesaler follows below all those measures
with its own ADS, then Northern Ireland and subsequent contexts. Each ADS
toggles independently, including its legend entry. Channel/context gates remain
explicit and the initial graph and table remain empty.

Retained source metadata confirms Share before Abbott IMS in both dimensions
(units rows 66/67, value rows 81/82); descriptor hashes were checked again.
The exposed executive catalogue has 18 direct source identities and no Cur/Pub.
The top contains Affiliate, cycle, Units/Value and visible calendars; shared
driver/sector scope remains. The former Selected scope dropdown was only a
presentation control and is now Total/Drivers/Sectors beside the graph. Table
periods retain their separate role.

Local checks passed 11 integration groups, 216 retained measure/period/cycle/
dimension fixture comparisons with R07 and 64 reconciliation comparisons.
Aligned context geometry, independent toggles, source order, dynamic labels,
responsive light/dark layouts, hover and zero warm network requests/script
errors were checked. All earlier designs remain preserved. Numbers remain
synthetic; live binding, Power BI implementation and performance remain pending.
No application source, workbook, Fabric item or live report was changed.

## 21 October 2026 — R09 audits all contexts and structures the S&OP summary

The user requested auditing the remaining source hierarchy/measures and improving
the summary's repeated heading lines. They explicitly chose ADS Units/Value only
for Homecare/Hospital, keeping detailed contract build-up workings outside this
GM page. R09 audits both retained neutral driver definitions: 29 sector plans,
13 source contexts, 18 executive measures in both dimensions, 10,179 structural
data rows, 1,044 identity matches and 58 source-order checks. All displayed
identities/orders match. Source row positions vary across sector layouts; the
catalogue now records per-driver ranges instead of implying a universal row.
No source forecast values, formulas or Product/Manufacturer identities are copied.

The selector now puts Retail before Private Order/Internal Account, matching the
bridge. Contracts resumes after Out of Pocket with one shared Channel control.
Every context retains an independent ADS toggle. The summary has one header row
and dedicated Channel, Sub-channel and Measure columns. Vertically merged labels
replace full-width hierarchy-heading lines; measure rows use short names without
repeating full paths. Multiple review groups/cycles use a merged scope column.

Local checks pass 13 integration groups, 216 retained fixture comparisons with
R08 and 64 reconciliations, plus the source audit above. All prior saved designs
remain preserved. Numbers are synthetic; live workbook/source binding, Power BI
implementation and performance remain separate pending gates. GitNexus reported
stale authority; direct retained metadata supplied the audit evidence without
refreshing a shared index or changing application/workbook/live report content.

## 21 October 2026 — R10 adds bridge-style spacing, run rate and PY growth

The user requested empty-row spacing and independent monthly-run-rate and
same-period-prior-year-growth switches in the S&OP table. Read-only inspection
of the current bridge reporting oracle, V18 template, BR-005 period rules and
S&OP Summary reference analysis confirmed the formulas and eligible blocks.
`summary-rules.json` records the source hashes and rules; no company workbook
or numeric source data was opened or copied.

The separately saved R10 adds 8px blank spacing between business blocks, keeping
Share with Abbott IMS. Optional detail rows sit beneath existing selected
amounts. Run rate divides a complete period amount by its month count, using
each measure's IMS or Ex-factory cutoff. Growth divides the complete amount by
the exact same months last year, minus one. Missing or zero prior stays blank.
Share remains percentage-only; PI/net IMS have run rate but omit growth, matching
the bridge. Monthly view hides redundant run rate and remembers its setting;
monthly growth compares the same month last year. Toggles affect only the
summary, preserving graph selections and source amount rows.

Local browser checks passed 16 integration groups, 384 independent derived
fixture comparisons, 216 amount values matching R09 and 64 reconciliations.
Merged-cell geometry with spacers/detail rows, all source context selections,
dynamic Units/Value labels, monthly behavior, responsive light/dark layouts,
hover and zero warm network requests/script errors were checked. R09's source
catalogue/audit files and all prior saved designs remain byte-preserved.

GitNexus workflow lookup reported stale authority/index; current source and
canonical business rules supplied the calculation evidence without refreshing
the index. All displayed values are synthetic. This is not live Excel/Fabric
source binding, Power BI deployment or measured report-performance evidence.
The approved first page, application source and workbooks remain unchanged;
Power BI implementation is still paused for design approval.

## 21 October 2026 — R11 adds independent section visibility

The user requested a local Hide control for the selector, graph and S&OP summary.
The separately saved R11 places Hide at the top right of each section. A collapsed
section keeps a compact heading and Show control. The selector's former detached
button is removed; collapsing it releases the left column so results widen.
Hidden sections retain all selections, calendar/summary periods and run-rate/
growth settings. Showing them restores current content and correct graph width.

Local browser checks pass 17 integration groups, including all eight visibility
combinations, top-right controls, keyboard restore, hidden-state changes and
saved host-state restoration. They also retain 216 amount comparisons with R10,
384 derived comparisons, 64 reconciliations, responsive light/dark layouts and
zero warm network requests/script errors. Source catalogue, source audit and
summary-rule bytes are unchanged; prior saved designs remain preserved.

The numbers remain synthetic. This is HTML design work only: the approved first
page, live Power BI report, Fabric items, application source and workbooks were
not changed. Live implementation remains paused for design approval.

## 21 October 2026 — R12 links summary years to calendars and clarifies spacing

The user identified that 2027 FY remained available during a January–December
2026 review, and requested small standard spacing between measures and
Sub-channels as well as Channels. R12 labels the top dates Review months and
limits summary years to that range. Widening adds choices without selecting
new columns; narrowing removes out-of-range selections. Changing entirely to
new years carries selected period kinds across; an explicitly cleared selection
stays empty. Named FY/YTD/YTG business windows remain intact, with a visible
caption explaining FY is January–December. Monthly uses the exact selected months.

The summary now has a contrasting 6px gap at every selected business-block
boundary, including Share before Abbott IMS, Sub-channels and Channels.
Run-rate/growth details stay with their measure's amount. Merged hierarchy
geometry and source order remain intact. The reference analysis confirms
business-block spacer rows; no workbook layout was modified.

Local checks pass 18 browser integration groups, including dynamic open-picker
updates, stale-column removal, year switching, clear-state retention, partial
year semantics and hidden-summary updates. They verify all 17 measure/context
boundaries, 216 retained amount comparisons with R11, 384 derived comparisons,
64 reconciliations and all eight Hide/Show combinations. Responsive light/dark
layouts, hover and zero warm requests/script errors also pass.

All prior designs remain preserved and observations remain synthetic. No live
Power BI report, Fabric item, application source or workbook was changed. Live
source binding, report performance and implementation remain pending approval.

## 21 October 2026 — R13 applies the final GM refinements to both HTML pages

The user authorized updating both HTML designs, saving a before-change version
and syncing Coordination while leaving Power BI unchanged. R13 combines the
pages in one offline preview with Explore in S&OP / Back to Demand review.
Affiliate, cycle, sectors, review months and Units/Value carry across; each page
retains its own explicit measure/context and presentation choices. Demand
review now also limits summary years to the calendar range and has a dynamic
FY/YTG shortcut. It starts with Total, driver rows, 12M and collapsed files.

Both pages have independent Hide/Show and matching source-selection status:
resolved ADS IDs, separate IMS/EF cutoffs and a labelled sample refresh. Source
versions expand on demand. Line emphasis from legend/table hover or keyboard
focus preserves selections; Share retains its right axis. Real blank source
Sub-channels display as a dash with explanatory tooltip. S&OP measures are not
automatically selected by navigation.

Eight local integration groups pass, including bidirectional scope transfer,
retained local state, calendar restrictions, ADS precedence, line emphasis,
keyboard operation, responsive light/dark layouts and combined saved-state
restore. There are no script errors or warm network requests. Numeric checks
preserve 672 Demand observations and 648 S&OP observations against their saved
baseline pages. Source audit/catalogue/rules and calculation functions remain
preserved, alongside all earlier saved designs. The named checkpoint binds
Demand R11 and S&OP R12 before the connected revision.

The two legacy illustrative numeric models remain independent. The shared
source-status display is design behavior, not proof of live source binding or
numeric reconciliation between those models. Binding both pages to the same
actual revisions, reconciling matching scopes/periods, cache invalidation and
measuring Power BI interaction speed remain unexecuted migration gates. No
Power BI report, Fabric item, application source or workbook was changed.


## 22 October 2026 — published R16.6 reported; native R17 candidate prepared

The operator reported that ForecastMaster Review was successfully published and
replaced. This records the user's report; no independent Service report-ID or
access check was performed here. The saved R16.6 project and ZIP remain intact.

The next authorized task is a native Power BI rebuild without silently losing
functions. The separate [R17 package](../handoff/report-native-r17/README.md)
creates native Demand/S&OP pages, charts, matrices, slicers, bookmarks and clean
export tables. A small selector/rate control retains hierarchical gates,
sibling order and unrestricted finite plan-rate entry; it renders no sales
figures. Original Refresh Demand, live connection and the full R16.6 Advanced
workspace remain preserved in the candidate. The Smart Demand Manager checkout
and workbooks were not edited.

Local numerical evidence: 2,593 primary checks, 3,888 FX checks and 16
scenario/export/blank-tier checks passed in the actual local Power BI Analysis
Services engine, with independent fabricated-data oracles. Twelve packaged
controller checks passed in Edge with a mocked Power BI host. All 129 candidate
PBIR JSON files with reachable published schemas passed; two unchanged legacy
visual-schema URLs returned 404. All 122 synthetic-preview PBIR schema checks
passed. No company source amounts were read for these tests.

Private Downloads deliveries are ForecastMaster Native Preview R17 -
SYNTHETIC.zip and ForecastMaster Native Review R17 - Candidate.zip. The sample
has no company connection or real refresh page; its semantic model matches the
native-engine fixture. The company candidate's first step is read-only PROBE,
not installation or publication. Actual source storage mode remains UNKNOWN;
the current additive adapter supports Direct Lake on SQL only.

**Release status: NO-GO for production replacement.** Computer Use could not
initialize in this WSL chat; actual rendering, native zoom/Fit/secondary axis,
line styling, all/empty bookmark behavior, preference sync, native exports,
run-rate/PY column visibility, exact largest-gap ranking, company calculations
and speed remain open gates. The README records the differences explicitly.
Neither new report nor native model support was installed/published in Fabric.
GitNexus coverage remains partial and cannot establish zero impact.


## 22 October 2026 — connected candidate now available through Coordination

The user explicitly asked to sync the connected candidate for remote pulling.
The repository was checked and is public. The original prepared thin-report ZIP
is now in `handoff/report-native-r17/candidate/`, with its company connection
reference preserved. Its SHA256 is
`feca03b94b2cf3fd5abacb46acf870e6f3d201c860224a7b5036c4bf1e3ed5b1`.
The bounded package check found no stored credential patterns or cached sales
model/PBIX/PBIT/local-cache files. This specific package was explicitly requested;
credentials, exported business data, full models and private execution backups
remain excluded. No company model/report was changed or published by this sync.

`WORK LAPTOP - OPEN CANDIDATE.txt` gives pull/extract/read-only-PROBE steps.
`CAPABILITIES-VS-R16.6.md` expands the earlier incomplete comparison: native R17
is missing multi-measure Demand, simultaneous chart trend windows, half-year
periods, driver/sector S&OP summary breakdown, exact gap ranking, pinned readout,
linked hover emphasis and automatic reflow. Source inspection also found
cross-year YTD/YTG, mixed-cutoff and negative-benchmark percentage differences.
They were not covered by the existing 6,497 checks and are not accepted parity.
The native implementation remains a NO-GO candidate; production R16.6 is intact.


## 22 October 2026 — readable metadata probe replaces the paste-heavy step

The operator's Notepad screenshot showed the combined installer's encoded
payload; they reported a failed paste into Fabric. The original source measured
331,830 bytes and its longest line was 318,966 characters. This is packaged data,
not evidence of file corruption. The exact clipboard/editor limit was not
observed. A separate 4,021-byte, 81-line metadata-only probe now avoids that
payload. Its max source line is 96 characters, and it contains no installation,
lease, sales query, write, refresh or publication action.

`READABLE PROBE - STEPS.txt` copies the new source directly from Coordination
with PowerShell Get-Content -Raw -Encoding UTF8 | Set-Clipboard, then targets one
new code cell in the screenshot-confirmed ForecastMaster_GM_Setup notebook.
The optional one-cell READ ONLY.ipynb has identical source and no saved outputs.
Eleven mocked API checks pass. No live company API, actual clipboard paste,
notebook execution, model/report update or source arithmetic change was made.
Original candidate/preview ZIP bytes and qualified native business code remain
unchanged, and the native candidate remains NO-GO for replacing R16.6.


## 22 October 2026 — first native source probe received

The operator supplied the successful metadata-read output: one directLake entity
fact partition, 15 existing tables, zero native helper tables and zero
model-defined roles. SourceAmountsRead and ModelUpdated were false. The M-text
SQL check was false and the adapter guard reported incompatibility. This is
operator-supplied receiving evidence, not independent access from this host.

The result does not identify the SQL/OneLake/source-reference route. The probe
omitted the detailed source shape, so SOURCE ROUTE - READ ONLY.py now reports
source-key names, reference flags, allowlisted connector/type/protocol hints
and address-key names without their values. SOURCE ROUTE - STEPS.txt gives the
clipboard/new-cell workflow in ForecastMaster_GM_Setup. Eight mocked source
shape/privacy checks pass. No installer/model/business calculation change,
storage-mode conversion, company refresh or publication was performed. The
source route and native deployment remain pending the additional result.

## 22 October 2026 — OneLake route confirmed; isolated R17.1 candidate prepared

The operator's second read-only result confirms one Direct Lake entity fact
partition, a named M expression using AzureStorage.DataLake, dbo schema and a
matching fact entity. No dataSource reference or connection values were printed;
source amounts were not read and the model was not updated. This supersedes
the unresolved-route statements above. The raw value-free result is retained in
feedback/logs/2026-10-22-native-r17-source-route.json. The original SQL-only R17
PREPARE/APPLY cannot serve this route; its ZIP and business source remain intact.

handoff/report-native-onelake-r17.1/ is a separate create-only qualification path.
It creates ForecastMaster Native OneLake R17.1 - TEST, preserving the original
Direct Lake tables and roles in that new model and adding 20 calculated metadata
helpers. It has no original-model update, Delta write, worker installation,
refresh, permission edit or report-publication endpoint. Existing test names and
concurrent metadata changes are refused; create calls are not retried. The
readable Python and single-code-cell notebook contain identical code, about
62 KB, without the former giant encoded line. Receiving steps still use one new
cell in ForecastMaster_GM_Setup; no Run all and no edits to the old setup cells.

The chart helper uses catalogue identities instead of every rank permutation;
table drag ordering retains the existing rank tokens. The model dependencies
could keep source metadata inside the existing model refresh path, but Direct
Lake referenced calculated tables are a Microsoft preview feature. Actual
company creation, processing and source-change propagation remain unverified.
The separate test model is not wired into the production worker schedule.

Eleven local mocked preservation/API tests and 2,654 local Power BI engine
checks pass. The latter use fabricated calculated/import sources and cover the
prior numeric oracle plus dynamic metadata and chart selection at varied ranks.
They do not qualify the Direct Lake preview or any company/native UI/export
gate. GitNexus could not map Coordination: structure was unregistered and impact
returned UNAVAILABLE/AUTHORITY_DRIFT_BLOCKS_CONCLUSION. Direct tracing and the
focused tests provide bounded fallback evidence, not a zero-impact graph claim.
The R17 capability gaps and additional numerical parity cases remain open.
No company installation, production refresh or report replacement was performed.

## 22 October 2026 — TEST model creation confirmed; processing is next

The operator supplied successful ONELAKE_TEST_CREATED output for ForecastMaster
Native OneLake R17.1 - TEST, ID 31d00232-ac03-48fe-af39-f2e4bae82443. Readback
reported the original model unchanged, all old tables and roles copied exactly,
20 calculated helper definitions confirmed, no sales-amount query, no refresh
request and no publication. This supersedes the unverified creation status
above; it does not prove processing or preview query support. The supplied
operation IDs and value-free output are in the dated feedback log.

The next receiving step is a single Refresh now of this TEST semantic model in
the Fabric workspace. Use its refresh history/status and stop on a failure or
connection prompt. The existing report Refresh Demand button targets the original
ingestion/model path and does not refresh this separate TEST item. Direct Lake
successful framing is not always listed as a separate history row; do not turn
an absent row into repeated refresh requests or a claimed processing pass.

The separately bound thin-report ZIP is now candidate/ForecastMaster Native
Review R17.1 TEST.zip under the OneLake package. Its project and connection
reference the new TEST model. Exactly two project payloads change (PBIP path,
PBIR connection); 136 other project files retain source bytes. The original
candidate ZIP remains unchanged. The old SQL setup/probe is omitted from the new
ZIP. Five local binding/preservation checks pass; actual company refresh,
Desktop rendering/zoom/export and reconciliation remain unverified. No business
visual or numerical code changed in this handoff. R17's feature/calculation gaps
remain open and production R16.6 is still the working version. Coordination is
not registered in GitNexus; direct package tracing supplies bounded evidence.

## 22 October 2026 — TEST refresh requires an explicit connection with GAC

The operator supplied a failed-refresh photo (10-second data attempt), then
copied the complete error. It explicitly identifies calculated tables/columns
referring to Direct Lake and requires an explicit connection with granular
access control. The TEST association comes from the conversation; the model
name is not visible in the photo. The earlier creation/readback remains
confirmed. No successful processing or native rendering/export/company
calculation acceptance is established. The value-free error is retained in
feedback/logs/2026-10-22-native-r171-refresh-failed.json; the raw photo is not
copied into the public repository.

FIX TEST CONNECTION - STEPS.txt now owns the immediate receiving step. Map only
TEST to a matching existing shareable cloud connection, or create a Cloud
connection through Maps to > Create a connection with the existing source
fields prefilled and normal company OAuth sign-in. Apply and refresh TEST once,
then supply the result. Microsoft documents that shareable cloud connections
always enforce GAC. This avoids tenant/workspace policy changes and does not
require disabling SSO, changing source mode, switching to SQL or recreating the
model. If these UI controls/source defaults are unavailable, request the exact
options shown before choosing a further remedy. No broad source-mode probe.

Direct tracing confirms that the create-only script contains no explicit
shareable-connection binding call. The actual original/TEST connection mappings
have not been inspected from this host, and no binding has been changed here.
The error does not establish universal OneLake calculation incompatibility.
Production R16.6, the create cell, TEST report ZIP and business code retain their
bytes. The packaged NEXT instructions remain byte-preserved for reproducibility;
current repository instructions explicitly require the connection fix first.


## 22 October 2026 - targeted hourly FILES execution confirmed

The operator confirmed the quick updater returned HOURLY_NOTEBOOK_UPDATED for
the existing ForecastMaster_Refresh (cells 4, 8, 10, 12), with a retained native
definition backup and no workbook reads or refresh from installation. The
operator then published the prepared Functions source and manually ran
ForecastMaster_Hourly successfully. This supersedes the installation-pending
status of hourly-targeted-r01 for these receiving steps.

The detector found eight files, exactly two changed October ADS workbooks
(Core Oral and Paed SIP), no removals, and read no workbook contents. Its
metadata listing still traversed 291 directories in 62.052 seconds (68-second
activity). The worker's SUCCESS exit value explicitly reports RefreshMode FILES,
two content checks, two SUCCEEDED/decoded revisions, eight current report files,
no StageErrors and COMPLETED model refresh correlated by RequestID. The notebook
activity took 261 seconds, with 226.276 seconds after session ready. These are
observed durations, not a measured before/after CU saving.

The receiving receipt is feedback/logs/2026-10-22-hourly-targeted-files-success.json.
The retained-revision/current-file policies are reported by the worker; an
independent historical-row audit was not performed. Legacy R05/R05.4 CodeVersion
strings were retained; RefreshMode and the installed cell guards identify this
patch's behavior. Next, with sources unchanged, manually rerun the same hourly
pipeline once and confirm UNCHANGED / NeedsRefresh false with the notebook
skipped. Schedule reactivation is pending that check. Historical-correction,
removal/rename and injected-failure receiving cases remain unrun; local checks
are recorded separately. No production or TEST report/model definitions were
changed by this evidence-only handoff.

## 22 October 2026 — TEST refresh completes with inherited-feed syntax warnings

The operator's latest photo reports Completed with warnings: data stage completed
in 26 seconds and query cache in less than one second. The copied details identify
nine old FM UI measures with terminal `displayFolder: Forecast review\Visual feed`
inside their DAX expressions. The earlier explicit-connection error did not recur.
The current actual cloud mapping and production's expressions have not been
independently read by this host. No clean processing or report acceptance is
established by this warning status. The value-free receiving log is
feedback/logs/2026-10-22-native-r171-refresh-warnings.json.

The new measure-repair-r01 package targets the existing TEST identity only. It
verifies a private company backup, moves only the exact terminal metadata on
nine allowlisted expressions, disallows purging and checks all remaining model
definition values and the cloud mapping afterward. It refuses unexpected shapes
or concurrent changes and never retries an update automatically. It makes no
sales query, explicit refresh, source/connection/permission edit, original-model
write or publication request. The earlier create cell and both report ZIPs retain
their bytes. Run its one new cell in ForecastMaster_GM_Setup, then one TEST
Refresh now and supply the outcome; no Run all or recreation.

Nineteen synthetic metadata/API/filesystem tests pass, including the full public
feed-formula templates with the reported suffix injected. This is body and API
scope preservation evidence, not live Direct Lake processing. Company repair,
clean refresh, native UI/export, performance and R16.6 parity remain pending.
GitNexus structure was unregistered; edit-impact reported authority drift and
quick-graph returned ACTIONABLE_PARTIAL. Direct tracing and focused tests are
bounded fallback evidence, not a claim of zero impact. Production remains R16.6.

## 22 October 2026 — R01 repair stops before model write; R02 verifies full backup

The operator supplied a RuntimeError traceback at R01's fs.head comparison after
fs.put, before its model-update request. This confirms no model write was reached.
The actual returned string/length was not captured, so neither preview truncation
nor backup corruption is established. Existing cloud mapping, TEST model and
any partial backup stay in place. The trace is summarized without model content
in feedback/logs/2026-10-22-native-r171-repair-backup-stopped.json.

measure-repair-r02 uses a full file copy to a private temporary Fabric-driver
directory, then compares UTF-8 byte count and SHA256. It checks write/copy results,
removes the temporary copy and keeps the company backup. At most three readback
attempts allow transient reads; no backup write or model update is retried.
Persistent failure still refuses any model write and emits only size/path
diagnostics. All nine-measure/body and definition/cloud-preservation guards are
retained. R01 and all old packages remain byte-preserved. The operator should
run one new R02 cell and refresh TEST once only after its success result.

Twenty-three local synthetic/mock tests pass, including original feed-body/API
preservation, large Unicode files, truncated and same-length corrupt reads,
false write/copy returns, bounded read recovery and temporary-file cleanup.
These simulations do not prove the receiving mismatch cause or live Fabric
success. GitNexus edit-impact remained UNAVAILABLE with authority drift; direct
tracing and focused tests provide bounded fallback. Company R02 full-file
verification, repair, warning-free refresh and native/R16.6 parity remain pending.
