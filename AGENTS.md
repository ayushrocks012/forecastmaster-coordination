# ForecastMaster coordination repository

This is the separate office-laptop script and feedback handoff. Keep changes here; the Smart Demand Manager application checkout is outside this task's requested scope.

Use `main`. Pull with `--ff-only` before starting a handoff and commit/push the completed handoff before the other laptop receives it. Preserve local edits if a conflict occurs; do not reset or force-push to clear it.

`START-HERE.md` owns office SSH and VS Code setup. `feedback/STATUS.md` distinguishes confirmed company results from pending installation or runtime checks. The current company sources are notebook R05.4, the separate native ad hoc R01 notebook and Functions R06-NATIVE-R01 (which retains the R05.2 helpers). The R05.3 and R05.2 packages remain available with their original bytes.

R05.4 retains all imported source revisions and disables automatic Delta purging. Reports still select the current content per saved source path. Do not reintroduce revision deletion or automatic purging during a refresh. The company installation and runtime tests of R05.4 remain separate from local qualification.

`handoff/` contains byte-preserved, selected script packages prepared in the preceding chat. `HANDOFF-MANIFEST.json` records their initial file hashes. Run `python tools/verify_handoff.py` to check this receiving copy. Changes to handoff code require updating the relevant tests and manifest together and explaining the change to the receiving operator.

The notebook and Functions files are copy/paste inputs for Fabric; merely committing or cloning them does not install or run anything in Fabric. Keep local tests, company installation, company runtime results, and report publication as separate facts.

Receiving evidence later on 20 October 2026 confirms the R05.4 hourly refresh, model completion and UNCHANGED notebook skip. The daily 08:00–17:00 London schedule is active; its first scheduled run is unverified. The SharePoint request button plus manual controller execution also passed. See the latest dated section of feedback/STATUS.md, which supersedes the earlier pending observations below.

`handoff/native-adhoc-r01/` is the separately qualified extension installed in the company workspace. It adds `submitNativeRefreshR06`, `ForecastMaster_Native_Adhoc` and `ForecastMaster_Adhoc`. Preserve the original R05.4 cells and R05.2 helpers. Native requests use `Files/ForecastMasterRefreshState/native-requests/`, a separate readiness receipt and the existing shared lock/ledger. The OneLake event rule must target the new native pipeline, never the SharePoint controller. On 21 October 2026, receiving evidence confirmed the report button -> native request -> event -> pipeline -> model-completion path, duplicate skips and automatic busy-lock retry recovery. Two button requests coalesced into one successful batch/model refresh. The operator reported multiple test clicks; the four pipeline launches are not evidence of four launches from a single click. The first scheduled hourly run is still unverified. Avoid five-minute controller polling and report/chart validation outside the hourly/ad hoc objective. Published listener rates are an ongoing baseline, not zero idle consumption or measured total usage.

The operator cannot access tenant settings and explicitly requires zero IT dependency. Do not steer setup toward tenant-admin changes, service-principal registration or an IT request. The separate `handoff/pipeline-user-context-r01/` cell omits only the hourly notebook activity's explicit connection reference to use the documented default user context. Run it in a separate unscheduled setup notebook, never ahead of the refresh worker. Its company installation and manual hourly execution were confirmed on 20 October 2026; its preserved local package still describes the original receiving gates.

Keep SSH credentials outside the repository. Screenshots and run outputs belong in `feedback/`; this repository is public.

On 21 October 2026 the user explicitly requested faster Review meeting interactions after the native-button work. This authorizes the separate `handoff/report-cycle-cache-r04.2/` performance package. Its visual loads all measures/drivers/profiles for an affiliate and demand-cycle set; other selections are local. Six model feed expressions change, with the component arithmetic retained. Company R04.2 installation and speed remain unverified until receiving output is supplied. The earlier limit on further chart validation applied to the completed native ad hoc gate; this new performance request has its own tests and receiving steps. Preserve the operator's saved Service report and its native button; import the same-GUID visual first and update only the existing model's feed expressions. Never deploy the old reference report over the edited Service report.

Later on 21 October 2026 the user paused live report changes to review the design in HTML first. The current review package is `design/executive-review-r07/README.md`; open its `index.html` in a browser. It uses illustrative data and adds simultaneous growth-driver and sector selection, graph views and table rows. The user explicitly requested syncing this prototype into Coordination before final approval. Keep report/model/visual installation paused until that approval; local prototype checks are not live Power BI acceptance or speed evidence. The R04.2 package remains preserved separately.

The subsequent R08 proposal is `design/executive-overview-r08/README.md`. The user explicitly requested preserving the preceding design by name before reviewing changes. R07 is the unchanged **Driver and Sector Review** baseline, at tag `design-driver-sector-r07`; R08 is **Executive Overview**, awaiting review. Open `design/index.html` to choose either version. Switching prototypes does not require a Git reset or company deployment. Preserve both packages until the user chooses; the live-report pause still applies.

R09 is separately saved at `design/executive-period-review-r09/README.md`. It extends period comparison, trend-history context and driver variance captions while retaining the earlier versions. On 21 October 2026 the user explicitly opted in to removing variance bars while keeping every numeric value. That presentation change is now applied to R09; the numeric preservation receipt is in its folder. Production deployment remains paused.

R10 is the latest HTML-only proposal at `design/executive-gm-review-r10/README.md`, requested on 21 October 2026 after the GM review. It moves period selection to the top, aligns chart dates, simplifies shared selection, adds expandable driver totals and explicit ranking periods, and retains numeric values and ADS defaults. R07, R08 and R09 remain byte-preserved. Synthetic local response checks are separate from unmeasured Power BI performance. The user explicitly reiterated that Power BI must remain unchanged until design approval.

R11 at `design/executive-month-review-r11/README.md` supersedes R10's control placement. The user clarified that the top is for broad cycle/channel selections and that visible From/To month calendars are important. Keep those calendars visible at the top for chart months; FY/YTG belongs to the executive summary. Summary periods and cycles must not silently reset chart dates. R10 and all earlier versions remain preserved; the live Power BI pause continues.

The user subsequently accepted the R11 first-page design and requested a separate second S&OP page. `design/sop-build-up-r01/README.md` is that HTML-only proposal, pending review. One driver/sector scope and measure tree add rows to both graph and table. Preserve Community = Wholesaler + Northern Ireland, Contracts = its seven source subchannels and Total ADS = eleven publishing leaves counted once. Matched Community diagnostics use the IMS calendar; published channel ADS uses the EF calendar. Units/GBP are amounts, share/effective uplift are weighted ratios, and parent/child selections must not cause additive double counting. The stacked composition therefore assigns each leaf to the most specific selected node and labels partial parent remainders. This synthetic prototype does not replace the bridge engine or establish live source binding or performance. R07–R11 remain byte-preserved, and Power BI implementation is still paused.

The latest second-page proposal is `design/sop-side-panel-r02/README.md`: the user requested a left floating-style panel of on/off channel/subchannel buttons with the graph and table on the right, and period/driver filters above. Keep one canonical measure selection; parent buttons select their own total, not their children. Hiding the selector preserves all selections. All channel choices are available in the panel, with no duplicate channel dropdown or hidden channel filter. R01 calculations and figures are preserved. Power BI feasibility is documented separately; native bookmarks do not establish automatic resizing or exact measure-selector behavior. Preserve R01 and the approved first page; live implementation remains paused.

R03 at `design/sop-channel-table-r03/README.md` is the current second-page proposal, following the user's rough sketch. Keep two straight button columns (channel totals/build-up choices and labelled real subchannels), a lean actual/forecast line graph on the right and the summary directly below it. Bar mode is removed; incoming legacy bar state must resolve to lines. Channel grouping does not change source business classification. R01/R02 figures and all earlier designs remain preserved. This is still HTML-only work; Power BI remains paused.

R04 at `design/sop-three-column-r04/README.md` supersedes R03's selector grouping: the user requested Channel, Sub-channel and Measure to mirror the bridge's business roles. Keep Market/share/Abbott/PI/net/factor in Measure, not Channel or Sub-channel. Ex-factory ADS switches visibility of the chosen channel/subchannel series while preserving those choices. IMS measures remain explicit Community references, never fabricated allocations to other channels or leaves. Units/Value stays separate at the top. Preserve earlier versions and the approved first page; this remains a synthetic HTML proposal with no live Power BI change.

R05 at `design/sop-spaced-groups-r05/README.md` follows the user's spacing sketch: align each channel with its own subchannels and Community measures in roomy bands. Homecare/Hospital sit beside Contracts; Retail has a separate band. Extra choices can expand rather than crowd the first column. The user subsequently requested Share on the same graph's right percentage axis, selected S&OP periods beside the summary and rows in bridge order independent of click order. Keep units/GBP on the left axis, weighted percentages on the right, tooltips correctly formatted and the existing IMS/EF cutoff meaning. R04 and all earlier versions remain preserved. This is HTML-only design work; source binding, live Power BI feasibility and performance remain unqualified.

R06 at `design/sop-cascade-r06/README.md` supersedes the independent-button behavior: Channel gates its target totals/subchannels, which gate applicable measures. Community IMS requires its total/blank-subchannel target; Wholesaler alone has its own Ex-factory measures. The user requires the bridge's hierarchy and order, with Abbott IMS → Market → PI → Ex-factory for Community total, then each later source context. Direct V18 neutral identities now inform `bridge-catalog.json`; do not substitute an invented taxonomy. Retain Out of Pocket → Retail and explicit derived Contracts combined totals. Cur/Pub/ADS are separate measures. Units/Value must rename selector, legend, tooltip and summary labels; share remains the corresponding unit/value percentage. Net IMS retains its IMS calendar despite the Ex-Factory Section. Matched-calendar uplift is a diagnostic, not the editable IMS Factor input. All fixtures are synthetic; real source binding is pending. R05 and earlier designs remain preserved; no Power BI changes are authorized yet.

R07 at `design/sop-source-only-r07/README.md` supersedes R06's added review totals and default selections. The user explicitly prohibited invented Channels, Sub-channels and Measures: expose only direct retained source identities, remove the derived Contracts combined context and matched-calendar diagnostics, and start with no Channel/context/Measure selected. Choosing a Channel enables but never automatically selects descendants. Both graph and summary require explicit valid choices. The real blank Community context owns IMS; Contracts has only its source sub-channels. Restore Affiliate and other broad filters: the top contains Affiliate, cycle, source Section, Units/Value and month calendars; Channel/Sub-channel/Measure remain solely in the left selector. Use only the known UK sample in the prototype's Affiliate list; production lists must come from actual data. Keep dynamic Units/Value labels, Share on the right axis and bridge order. The 44-identity catalogue is an executive subset, not every workbook measure. Ask the user about unclear business relationships instead of filling gaps. Preserve R06 and all earlier designs. Power BI stays paused.

R08 at `design/sop-aligned-contexts-r08/README.md` supersedes R07's crowded family-level measure column. Keep each source Sub-channel on its own aligned row: Community blank owns Share → Abbott IMS → Market → PI → IMS minus PI → ADS; then Wholesaler with its own ADS, Northern Ireland with its own ADS and subsequent source contexts. Share above Abbott IMS is confirmed in retained bindings (units rows 66/67, value rows 81/82). Remove Cur/Pub from this executive page and remove Section and Selected scope from top filters. Preserve combined/driver/sector presentation as compact Total/Drivers/Sectors controls beside the graph, without changing data inclusion. Every context's ADS toggles independently; do not use one family-level ADS switch that affects sibling subchannels. Keep Affiliate, cycle, Units/Value, calendars, shared driver/sector choices, table periods and existing cutoff meaning. Only 18 direct identities are exposed in this requested executive subset. Preserve R07 and earlier designs. This remains HTML-only; Power BI is paused.

R09 at `design/sop-structured-summary-r09/README.md` verifies all 13 contexts and 18 displayed executive measures across both retained neutral driver definitions (29 sectors, 1,044 binding identity matches, 58 source-order checks). The user explicitly kept Homecare/Hospital at ADS Units/Value only; do not add detailed contract workings. Follow the true context order: Retail precedes Private Order/Internal Account, so Contracts continues after Out of Pocket. A single Channel toggle governs both Contracts segments. Do not treat one physical row number as universal: sector layouts vary; the catalogue records ranges and matching uses full identities. The S&OP summary is a standard Channel / Sub-channel / Measure matrix with merged hierarchy cells and one header row. Remove full-width context/group heading lines and repeated full-path labels. Add a merged Review scope column only when multiple presentation groups/cycles require it. Numeric observations, selection gates and cutoff rules stay unchanged. Retained metadata qualification is not a live workbook/Fabric or Power BI performance gate. Preserve R08 and all earlier designs; live implementation stays paused.

R10 at `design/sop-run-rate-growth-r10/README.md` adds requested blank spacing and two independent summary-only switches, initially off. Follow the bridge's S&OP block choices: all displayed amounts except Share can show monthly run rate; Abbott IMS, Market and displayed ADS contexts can also show growth. PI and IMS minus PI omit growth. Share has neither derived row. Run rate is the complete period amount divided by the number of months in that measure's FY/YTD/YTG window, retaining separate IMS/EF cutoffs. Growth is complete current amount / complete exact same months last year - 1; absent or zero prior is unavailable, never fabricated. Monthly table mode suppresses redundant run rate but remembers the choice; growth uses the same month last year. Use one blank spacer between business blocks while keeping Share with Abbott IMS. Derived/spacer rows must preserve merged hierarchy geometry, source order, amount values and graph selections. `summary-rules.json` binds the current source/rule lookup; this remains synthetic HTML design qualification, with no workbook or Power BI changes. Preserve R09 and all earlier designs.

R11 at `design/sop-section-visibility-r11/README.md` adds independent local Hide/Show controls to the selector, graph and S&OP summary. Keep Hide at each section's top right and leave a compact heading with Show when collapsed. The selector no longer uses a detached control; collapsing it releases its column so the graph and summary widen. Visibility must not clear or change any data selection, calendar, period, presentation choice or run-rate/growth setting. Restore hidden sections with current data and correct graph dimensions; retain accessible native controls and persisted visibility. Preserve R10's source/rule bytes, every prior design and the approved first page. This remains HTML-only; Power BI implementation is paused.

R12 at `design/sop-calendar-spacing-r12/README.md` supersedes the second page's independent summary-year availability. Top Review months now constrain the summary's available and selected years; January–December 2026 must not offer or show 2027 periods. Widening makes new-year choices available without automatically adding columns; narrowing removes stale ones. A move to entirely different years retains the selected period kinds, but explicit clearing stays empty. FY remains January–December, and YTD/YTG retain each measure's cutoff month; Monthly uses exact review months. Do not silently clip a named FY into a partial total. Add one small visible 6px spacer between every measure block, Sub-channel, Channel and review group, including Share before Abbott IMS. Keep amount/run-rate/growth detail rows together. This overrides the earlier Share/Abbott no-gap exception. Preserve source order, merged-cell geometry, numerical rules, independent Hide/Show and all prior designs. The approved first page and live Power BI remain unchanged.

R13 at `design/connected-gm-review-r13/README.md` is the latest paired HTML review. The user authorized applying the GM refinements to both pages, preserving the preceding versions, and syncing Coordination only. The named before-change checkpoint is `design/checkpoints/before-connected-gm-review-r13.json`, binding saved Demand R11 and S&OP R12. Navigation carries Affiliate/cycle/sectors/review months/Units-Value while retaining each page's explicit measure/context and display choices; never invent a Channel mapping or preselect S&OP measures. Both pages restrict summary years to Review months. Keep full named-period arithmetic and dynamic FY/YTG shortcuts. Demand defaults to driver summary, Total chart, 12M comparison and collapsed files. Both pages retain independent Hide/Show, shared source-selection status, expandable source versions and non-filtering line emphasis. True blank Sub-channels display as a dash with No sub-channel tooltip. Preserve the legacy illustrative calculations and earlier design bytes. Shared source metadata is not cross-page numeric reconciliation: actual shared source binding, live reconciliation, refresh/cache checks and measured Power BI speed are still unexecuted migration gates. Power BI, application source and workbooks remain out of scope until approved.

R14 at `design/plan-rate-review-r14/README.md` adds the user's requested plan rates to both paired HTML pages. The before-change checkpoint is `design/checkpoints/before-plan-rate-review-r14.json`, named **Before plan rates — Connected GM Review R13**. Value exposes GBP/USD and a compact header panel keyed by Affiliate/local currency/plan year. The user explicitly chose **one selected plan-year rate across the whole review**, including historical and future observations; do not switch to rates by each observation's year. Keep raw GBP/units and convert monetary outputs once. Units, Share, business growth, variance percentages and ranking remain independent of FX, including missing or numeric zero FX. No business rate is prefilled; missing FX means unavailable USD amounts, numeric zero means zero, and invalid/negative/Boolean rates are rejected. Edits and currency are shared across the two HTML pages and remembered in one combined local host state. Only the actual UK/GBP sample is exposed; future affiliates/currencies require real metadata. Preserve R13 and every earlier saved version. This remains an illustrative design: official rate storage/editing, common source binding, live cross-page reconciliation, refresh/cache qualification and Power BI performance are unexecuted migration work. No Power BI, Fabric, application source or workbook changes are authorized by this HTML request.

R15 at `design/currency-plan-review-r15/README.md` supersedes R14's annual Affiliate-specific rate rule. The user's latest instruction is one current plan rate per distinct source currency, with no plan-year selector or country/Affiliate label in the FX editor. Derive all input currencies from actual base metadata, deduplicate them, and share rates across both pages. Plan rates is always visible in the header; Currency display is shown for Value. Multiple Affiliates default Value to USD; convert each source-currency contribution before summing, never add mixed raw currencies or apply one rate to their combined amount. Missing required rates withhold the complete USD total; USD itself has rate 1. Keep the UI's actual UK/GBP base; isolated GBP/EUR/USD fixtures qualify the generic conversion model but are not visible real Affiliate sources. The current page adapters still supply their existing GBP sample observations, so live multi-Affiliate source binding and percentage aggregation remain implementation work. Preserve all 31 R14 files using `design/checkpoints/before-currency-plan-review-r15.json`, named Before currency-only rates — Plan-rate Review R14, and preserve all earlier versions. This remains HTML-only; Power BI, Fabric, application source and workbooks stay unchanged.

On 21 October 2026 the user approved implementing both R15 views, then chose a new Desktop report and supplied a thin Redesign PBIX. `handoff/report-gm-desktop-r16/README.md` is the new candidate handoff: Demand review, S&OP review, and a separate byte-preserved Refresh Demand page; remove the old Review meeting page only in the newly generated project. This authorization supersedes the earlier HTML-only pause for this report candidate. Never patch a PBIX binary: read the supplied report and create a new PBIP/PBIR, with an exact original PBIX backup. Keep company-bound project/output files outside this public repository. Both views use the same direct saved bridge components, with twelve additive reporting rules, complete-data guards and local selection caches. The user-run setup preserves existing rules and uses the shared writer lease; a subsequent native request rebuilds derived reporting and refreshes the existing model. Do not run or publish company changes from this host. Native Power BI page tabs retain separate visual sessions; internal review navigation carries shared choices and rates. Local browser arithmetic and project-preservation checks passed, but Desktop opening, live DAX/data reconciliation, company speed and publication remain receiving gates. The source visual schema 2.14.0 is preserved; its public schema URL returned 404 during local validation. GitNexus impact remained UNKNOWN/unavailable, supplemented by bounded direct tracing and focused tests. Preserve R15 and all preceding packages.

R16 opened on the work laptop but failed its first complete feed with Duplicate monthly component. The operator's read-only DAX result confirms unique monthly fact groups and 84 distinct month-start dates. `handoff/report-gm-desktop-r16.1/` corrects a reproduced timezone regression against the working R04.2 reader: parse zoned host timestamps before extracting the local calendar month. Do not change company facts to repair this transport error. Preserve distinct raw blank aggregate identities, count identical delivered aggregates once, reject conflicting amounts/missing counts or different dates folded into one month, and retain complete-total safeguards. R16.1 also treats empty startup views as loading. Its setup/rules/formulas remain unchanged; one-time S&OP preparation is still a separate receiving gate. Preserve all 28 tracked R16 files and every earlier package. R16.1 company rendering and reconciliation remain pending until the user tests the separate replacement project.

On 22 October 2026 receiving evidence confirmed R16.1 loading, successful reporting setup, native projection/model completion and numeric driver rows. `handoff/report-gm-desktop-r16.2/` is the separately authorized report-only compact correction. Populate searchable driver/tier dropdowns from the preferred ADS sources in the current Affiliate/cycle (or explicit custom files), not the whole-model dimension. Preserve missing/ambiguous cohort guards and explain excluded no-ADS drivers. Stable name-based selection identities must survive source reordering; legacy positional state resets explicitly rather than selecting a different tier. Keep one headline period with Plan and trend variance; retain all chosen periods in the executive table and remove redundant shortcuts/captions. One visual viewport owns vertical scrolling; new pages default to FitToPage. The operator's read-only history check found missing Vegan 2K observations; explain unavailable benchmarks without imputing, changing training windows or altering source data. Numeric/transport methods and setup rules remain unchanged. Do not repeat the completed setup for this report update. Preserve all R16.1 and earlier files; keep company-bound output private. R16.2 native rendering, company reconciliation and measured speed remain receiving checks; local synthetic 500-tier tests do not pass those gates.

R16.3 at `handoff/report-gm-desktop-r16.3/` supersedes R16.2's strict aggregate display rule. On 22 October 2026 the operator required driver/combined totals despite missing tier observations, dynamic parent-to-tier choices, working host zoom and aligned headers. Follow the later BR-018 SUM_AVAILABLE_V1 display policy and its operator_formulas/sector_summary owners: sum available members monthly and fit the trend at that selected aggregate level; do not sum individual tier fits or fill missing leaf cells. Entirely unreported months, missing/ambiguous source cohorts and invalid ratio denominators remain unavailable in this report. Single-tier comparisons retain their gaps. Restrict Forecast tiers to explicit selected scopeDrivers; clearing child ticks retains parent choices. Carry parent/child scope in the shared session. Handle host viewport changes before early returns, including resize-only updates without dataViews, scale logical chart coordinates and preserve cached state. Align calendars, source status and five filter positions in both modes; S&OP reserves blank Section/Measure positions. The operator also questioned duplicate native navigation: the new report has only GM Review (both Demand/S&OP modes in one instance) and the byte-preserved Refresh Demand page. Preserve all earlier three-page projects as rollback. Setup/model/feed definitions remain unchanged; do not repeat completed setup. Local synthetic tests do not pass company native zoom, reconciliation, performance or publication gates.


R16.4 at `handoff/report-gm-desktop-r16.4/` follows the operator's R16.3 native-zoom and summary/order feedback. Keep the native Power BI slider/Fit controls, with no internal zoom toolbar. The candidate has a 1440 x 2400 native page and matching visual, default FitToWidth: normal content uses native page scrolling, so zooming out can expose more content. Expanded detail retains one safety overflow scroller. Synthetic host geometry is not receiving Desktop/Service acceptance. Move Review summary period beside Growth drivers/Forecast tiers on BOTH modes, with search and filtered Select all/Clear all; share the chosen periods across navigation and retain calendar-year availability. Show all selected Demand periods in a concise Plan/trend matrix. Actual-only is determined from exact months and saved cutoffs; omit redundant variance columns only for those periods. Compact the lower table controls. S&OP supports hold-drag or Alt+Up/Down within siblings only, with Reset order; table and graph/legend share that saved permutation. The GM default groups all Contracts contexts together while retaining source order inside each parent; the neutral source catalogue stays unchanged. R16.3 numeric, source, transport, setup/rules and all older package bytes remain unchanged. The original connection/feed expressions and native Refresh Demand are preserved. Do not repeat the successful setup/model rebuild. Native zoom/drag, company reconciliation/speed and publication remain receiving gates.


R16.5 at `handoff/report-gm-desktop-r16.5/` corrects the operator's changing monthly tooltip values. Both charts previously interpolated between months while rounding the label. Hover must select the nearest monthly point and snap guide/markers to that point; no intra-month amount interpolation is allowed. Read the existing monthly series value, including trend/weighted Share and the chosen FX display. Missing monthly points remain unavailable, zero remains numeric, and valid neighbours/final or single months must work independently. Retain pinning and exact monthly values across zoom. All numeric/source/transport, viewport/layout/order, setup/rules and R16.4 bytes stay preserved. This is report-only; no setup/model rerun or company publication. Local synthetic tests reproduce the old defect and verify the new package; native zoom/drag/rendering, reconciliation and speed remain receiving gates.


R16.6 at `handoff/report-gm-desktop-r16.6/` supersedes the paired-member ratio rule in earlier report candidates. Aggregate Share must divide the independently available Abbott and Market amount totals for the same selection/calendar, matching displayed totals; a missing numerator must not silently remove valid Market. Never average monthly/sector percentages. Preserve strict missing leaf detail, required-month/source guards and zero denominator behavior. Mixed-currency Value Shares require one configured currency basis on both sides; unknown currencies/missing rates remain unavailable, with existing single-known-currency neutrality retained. The operator clarified that the year-formatting concern was dash versus $0: preserve unavailable versus numeric zero, explaining it in the tooltip rather than filling history. Demand table headings omit visible date-range subtitles (ranges remain tooltips); flat sector labels are one line Sector – Driver, hierarchy names its driver once, partial counts move to tooltips and body padding is smaller. No numeric cells are removed. Local bounded audits cover the 18 S&OP measures, period windows, run rate/PY growth, Demand/leaf reconciliation and Share populations with independent synthetic oracles; they are not company/workbook-wide qualification. Preserve all R16.5 bytes, source/transport/leaf logic, setup/model/feed, native Refresh Demand and rollback PBIX. No setup/model rerun or company publication. Native/reconciliation/speed remain receiving checks.


On 22 October 2026 the user reported successfully publishing and replacing
ForecastMaster Review with R16.6, then explicitly requested a native Power BI
rebuild preserving all functions and allowing custom components only when
necessary. This authorizes `handoff/report-native-r17/`, a separate qualification
candidate, not replacing production from this host. Its native charts, matrices,
slicers, navigation, bookmarks and clean export tables use additive native DAX.
A small new custom control owns only gated Channel/Sub-channel/Measure choices,
sibling order and free-form per-currency rate input. Preserve the complete
R16.6 Advanced workspace and the original native Refresh Demand page/connection.
The private source project and both receiving ZIPs remain outside this public
repository. Only neutral source, metadata, synthetic tests and counts-only
receipts belong here.

R17 passed 6,497 independent-oracle numerical checks in a task-owned local Power
BI Analysis Services engine and 12 packaged-control checks with a mocked host.
These do not establish Desktop rendering, native filter/sync acceptance,
Service behavior, export formatting, company reconciliation or performance.
Computer Use initialization failed for this WSL chat. The actual company model
mode is UNKNOWN from the thin report: the generated notebook defaults to
read-only PROBE. The current additive adapter supports Direct Lake on SQL only;
do not convert Import/DirectQuery/OneLake modes or change security to make it fit.
PREPARE/APPLY require their explicit later stages and preserve old tables/roles,
back up the definition, use the existing writer lease and disable purging. The
exactness ledger lists unresolved UI/feature differences, including largest-gap
ranking; R17 remains NO-GO for replacing production until they pass. A fallback
is preservation, not evidence of native parity. Do not repeat R16 reporting-feed
setup or run a company refresh simply because the native candidate was prepared.


On 22 October 2026 the user explicitly requested putting the company-connected
R17 candidate in Coordination for remote pulling. This supersedes the earlier
private-ZIP exclusion for this particular audited thin-report candidate only.
The repository was verified public. `handoff/report-native-r17/candidate/`
contains the original prepared ZIP, its company connection identifiers and a
bounded package-check receipt. No stored credential patterns, cached sales
model, PBIX/PBIT or local cache were found. Keep authentication tokens, exported
company figures, full/cached models and private execution backups out of Git.
Do not infer authorization to publish unrelated company artifacts. This package
sync does not install or publish anything in Power BI/Fabric.

`CAPABILITIES-VS-R16.6.md` records the more complete source comparison: native
R17 currently omits multiple Demand measures, simultaneous chart trend windows,
H1/H2, S&OP per-driver/per-sector summary rows, the exact gap-rank shortcut,
click-pinned readout, linked hover emphasis and automatic HTML reflow. It also
records cross-year YTD/YTG, mixed-cutoff and negative-benchmark percentage
calculation differences. The earlier local numerical checks do not establish
parity for these paths. Preserve the candidate's NO-GO status and R16.6 fallback;
recording the differences does not authorize changing business semantics.


On 22 October 2026 the operator reported that the ZIP's large encoded probe text
would not paste into Fabric. The original combined installer was 331,830 bytes
with a 318,966-character line. Preserve it and the original ZIP; use the separate
`PROBE ONLY - READABLE.py` for metadata inspection. It is 4,021 bytes, max line
96, with no installer, lease, data query, refresh or publication path. Current
receiving instructions name the screenshot-confirmed ForecastMaster_GM_Setup
notebook and copy exact source with Get-Content -Raw -Encoding UTF8 | Set-Clipboard
before pasting into one NEW cell. Never Run all or edit old setup cells. The
optional READ ONLY.ipynb contains identical code and empty outputs. Eleven local
mocked API tests pass; company/API/clipboard execution remains unverified. This
metadata-only repair changes no native business measures or release decision.


On 22 October 2026 the operator supplied the first readable probe result:
FactPartitionCount 1, SourceStorageModes [directLake], SourceType entity,
SQLSourceConfirmed false, NativeTablesAlreadyPresent 0, ExistingTableCount 15,
ExistingSecurityRoleCount 0, ModelUpdated false and SourceAmountsRead false.
This confirms the reported Direct Lake entity layout, not its SQL/OneLake route.
The original detector checked only named M connector text. Do not label the
company source OneLake or change modes merely from that false result. The next
read-only artifact is SOURCE ROUTE - READ ONLY.py, described by SOURCE ROUTE -
STEPS.txt; it emits only property names and allowlisted connector/type hints,
not connection values. Eight local mocked source/privacy checks pass. Keep the
original probe/installer ZIP/business code intact until actual source shape is
known. Model-role count zero is not a verdict on workspace/item authorization.

The operator's second probe on 22 October confirms the fact's named M expression
uses AzureStorage.DataLake: the company model is Direct Lake on OneLake. This
supersedes the unresolved route above. Both probes are complete; do not request
another broad source-mode probe or use the old SQL-only R17 PREPARE/APPLY.
The new receiving package is handoff/report-native-onelake-r17.1/OPEN FIRST -
ONELAKE.txt. It creates one separate ForecastMaster Native OneLake R17.1 - TEST
model only, copying the original tables/roles/source without modifying production.
Twenty calculated metadata helpers replace the SQL views/static Delta helpers.
Calculated tables referencing Direct Lake are a Microsoft preview capability:
company creation, processing and actual refresh propagation remain gates.
The separate TEST model is not scheduled by the production refresh worker.
Eleven mocked API/preservation tests and 2,654 synthetic local engine checks pass;
the engine sources are calculated/import and do not prove the Direct Lake preview
or Desktop/Service rendering/export. Keep R17's unresolved native feature and
calculation parity gaps explicit. Do not replace production R16.6 from this
create-only step. Preserve the original ZIP and source adapter bytes.

Later on 22 October the operator confirmed ONELAKE_TEST_CREATED for TEST model
31d00232-ac03-48fe-af39-f2e4bae82443, with all preservation/readback flags true
and RefreshRequested false. Creation is now confirmed; processing and native
rendering are not. Do not rerun the create cell. Current receiving instructions
are report-native-onelake-r17.1/NEXT - REFRESH AND OPEN TEST.txt. They refresh the
TEST model once in Fabric, then open the TEST-bound thin report from candidate/
if processing completed. The existing Refresh Demand button still targets the
original refresh path and is not the TEST-model refresh control. The new ZIP
changes only the project path and model connection; 136 report payloads retain
their bytes. It omits the stale SQL installer/probe and preserves the old ZIP.
No feature/calculation gap is closed by this binding, and production R16.6 must
not be replaced from this qualification step.

The next operator photo on 22 October reports a failed 10-second data refresh;
the subsequent copied full error explicitly requires an explicit connection with
granular access control for calculations referring to Direct Lake. TEST identity
is from the conversation, not visible in the photo. Immediate instructions are
report-native-onelake-r17.1/FIX TEST CONNECTION - STEPS.txt: map only TEST to a
matching shareable cloud connection (or create through prefilled source fields
and company OAuth), Apply, then refresh TEST once. Microsoft states shareable
cloud connections always enforce GAC. Do not recreate the model, disable SSO,
change source mode or request tenant/workspace admin changes. If Maps to/create
or source defaults are unavailable, obtain the exact UI options instead of
guessing an endpoint. The creation code has no explicit connection-binding step;
the actual company mappings remain uninspected from this host. The error does
not establish universal OneLake calculated-table incompatibility. Preserve the
created TEST item, production R16.6, candidate ZIP and business code. Keep the
packaged NEXT instructions byte-preserved and put current guidance in the FIX
document/README so the report package remains reproducible.

Later on 22 October the operator supplied TEST refresh Completed with warnings
(data stage 26 seconds, query cache less than one second). Nine inherited FM UI
expressions end in displayFolder: Forecast review\Visual feed, which belongs to
metadata rather than DAX. The earlier explicit-connection error did not recur;
actual cloud mapping and production expressions were not independently inspected.
Use report-native-onelake-r17.1/measure-repair-r01/OPEN FIRST.txt. Its new readable
cell targets only existing TEST 31d00232-ac03-48fe-af39-f2e4bae82443, backs up the
definition privately, moves the exact suffix on nine allowlisted measures and
checks full definition and cloud-mapping preservation. Unknown shapes, backup
failure or concurrent metadata changes refuse writes; purge is disabled and
updates are not retried. Nineteen local synthetic/mock checks pass, including
public feed-template body preservation. Company repair and warning-free refresh
are pending. No source data, native arithmetic, source mode, security, refresh
worker or original model is changed. Do not rerun creation or the old setup;
keep both report ZIPs and packaged NEXT text byte-preserved. Native capability
and calculation parity gaps remain open. Production R16.6 stays in place.

The operator's next R01 repair traceback stopped at fs.head backup comparison,
before updateDefinition. No model write was reached. The returned preview size
and contents were not captured; do not call truncation or corruption confirmed.
Current receiving package is report-native-onelake-r17.1/measure-repair-r02/.
It copies each full new backup to an isolated temporary Fabric-driver directory,
verifies UTF-8 byte length and SHA256, removes the temporary copy and retains the
company cloud backup. Three bounded read attempts accommodate transient reads;
failed verification still refuses model writes. The nine-measure body repair,
TEST-only identity, concurrency/cloud-preservation guards and no-purge option
remain unchanged. Twenty-three local synthetic/mock tests pass, including large
Unicode files, truncated/same-length corrupt copies and cleanup. Actual company
R02 verification, repair and clean refresh remain pending. Preserve all R01
files and partial company backups; run one NEW R02 cell, never Run all or the
old failed cell. Refresh TEST once only after a successful repair result.

The operator subsequently supplied R02 TEST_FEED_REPAIRED with nine measures,
full-file UTF-8 backup hash/length verification, remaining definition preserved
and cloud mapping preserved. They then reported TEST refresh Completed with no
warnings. Company repair and clean TEST processing are now receiving-confirmed;
this host did not independently query that run. Continue with report-native-
onelake-r17.1/OPEN TEST REPORT - STEPS.txt and the existing TEST-bound ZIP.
Do not rerun creation/setup/repair/refresh merely to open the report. Desktop
rendering, filters, native zoom/export, company numerical reconciliation,
refresh propagation, performance and the documented R17 feature/calculation
parity gaps remain open. Keep production R16.6 in place. All existing source,
creation/repair code, local test receipts and both report ZIPs remain unchanged.

The next operator Desktop photo shows Native R17.1 TEST with a resource-exceeded
visual, an otherwise loading chart and blank action buttons. Full See details
text is pending; memory-vs-timeout is unconfirmed. Current package is handoff/
report-native-r17.2/OPEN FIRST - WORK LAPTOP.txt. The old generator stored actions
under visual.objects and omitted native default-state text/show entries. R17.2
corrects these using Microsoft's authoring pattern. Desktop EDIT mode still
requires Ctrl+click; this is distinct from those malformed definitions.

R17.2 batches facts by file/month/component before per-sector missing checks,
preserving available-member, zero, FX and source guards. A cheaper scenario-
visibility attempt failed regression and is not delivered. The revision adds
fm_native_periods/fm_native_headline and one native grouping relationship; all
original source/feed/security/cloud objects remain preserved. Aligned native
filters, linked driver/tier dropdowns, header plan rates and a cycle-year opening
range are configured. H1/H2, cross-year masks, signed benchmark %, multiple
chart trends and S&OP breakdowns have synthetic local engine evidence.

The paired updater/report targets only EXISTING TEST
31d00232-ac03-48fe-af39-f2e4bae82443; its name stays ForecastMaster Native OneLake
R17.1 - TEST. R02's full-file private backup verification, concurrency/cloud
guards, no-purge and no-write-retry rules remain. Run one NEW code cell in
ForecastMaster_GM_Setup, refresh TEST once on success, then open the new R17.2
ZIP. No company action was executed from this host. Preserve all previous
packages/backups and production R16.6. Refresh Demand still targets the original
production worker, not TEST. Native Demand multi-measure, exact ranking/pin/
hover and automatic Hide reflow remain open gaps, with other receiving gates.

R17.2 receipts cover core/FX/export/scenario engine regressions, separate signed/
mixed/overlay/sector cases, a fabricated 10-driver x 50-sector query, mocked
updates and PBIR checks. Query fixtures use explicit UTF-8 reads to preserve
invisible ordering suffixes. No company amount was queried. The UI bridge failed
before selecting a window; a task-owned native engine was tested separately on
fabricated calculated/import sources. Company Direct Lake/UI/export/performance
are unverified. GitNexus Coordination authority remained unavailable; direct
tracing and preservation checks provide bounded fallback, not a zero-impact
graph conclusion.

On 23 October 2026 the operator rejected R17.2's native Desktop layout and
subsequently explicitly prohibited ALL custom visuals while first assessing
native design and any tradeoffs. This supersedes the prior fallback/custom-
control exception for the new preview only. Preserve all frozen older packages
and production R16.6. Current handoff is handoff/report-native-only-r17.3/.
It qualifies Demand Review first: one built-in-only page, no hidden R16.6 or
custom refresh/control pages, no CustomVisual resource registration or pbiviz/JS.
The TEST ZIP preserves the exact existing R17.2 connection and amount measures;
there is no Fabric installer, model update, refresh or publication in this step.
The SAMPLE ZIP uses only the existing fabricated calculated-table fixture and
works without a company connection. Do not commit actual company models/data.

The native-only preview reserves native control chrome/padding, types semantic
numeric literals, uses slicer textSize and real textbox paragraphs, removes the
reproduced duplicate native Label query names and uses native monthly line/zoom
formatting. Automatic ADS/source currency are physical page filters; removing
the redundant source-scanning matrix visual filter does not remove DAX source,
cohort, missing-data or zero guards. Company performance is still unverified.
S&OP, manual saved-version override, FX editing/conversion, custom drag/pin/hover
and Hide reflow are explicitly deferred for native review, not silently treated
as retained parity. Native Desktop rendering/export/interaction and company
execution/reconciliation remain receiving gates. The UI bridge still failed
before selecting a window; structural/schema checks are not a visual pass.

Later 23 October R17.3 screenshots confirm a loading native headline/chart, but
show redundant buttons/sliders, malformed scaled amounts and visual date tokens,
and collapsed executive columns displaying a rounded variance ratio as zero.
The user requested native drill instead of Drivers/Sectors/Both buttons. Current
handoff is handoff/report-native-only-r17.4/. It removes all nine action buttons
and view bookmarks, uses one driver > SectorLabel hierarchy with native drill,
disables both chart sliders, uses a continuous date axis, fixes visual-level
MMM date tokens, and explicitly stores the range slicer's UI start/end dates.
Retain native page zoom, Focus mode and export; no custom visual may be added.

R17.4 has one guarded existing-TEST format/display update, unlike report-only
R17.3. Scaling separators move before the decimal. N Summary Cell returns Plan
for a collapsed period parent and blank for a mixed absolute/percent comparison
parent; its full leaf expression and every other numeric/source expression are
preserved. Only native format expressions and that display guard may change.
Require known native definitions, complete private UTF-8 backup verification,
concurrency/cloud mapping checks, no purge, one update/no retry and full readback.
Do not recreate the model, change a source/connection/security object, query
company amounts, refresh sources or publish. SAMPLE uses fabricated data and
already includes this repair. Older packages/production stay untouched.
Windows formatter and local schema/mock checks are separate from pending native
Desktop drill/rendering and company reconciliation/performance. The WSL UI
bridge still failed before selecting a window. Keep those receiving gates open.

Later 23 October the operator supplied an R17.4 post-write readback failure:
the verified backup and updateDefinition operation ran, then received != fixed
raised. The subsequent cloud mapping check was not reached. Do not rerun the
updater (including its already-installed shortcut), refresh, roll back, recreate
TEST, change its mapping or publish to infer success. Current receiving step is
handoff/report-native-only-r17.4/readback-check-r01/. Run only its new read-only
CHECK cell in ForecastMaster_GM_Setup against the exact reported private backup.
Preserve the frozen R17.4 updater/ZIPs and all older packages. No company model,
connection values or raw differing values may be committed or printed. The
probe covers the entire definition and mapping, permits only identical-text
DAX line representations, and reports all other differences for review.
Local mock evidence does not establish the live mismatch cause or acceptance.

The next operator output on 23 October confirms TEST_R174_READBACK_VERIFIED:
21 identical DAX string/line-array representation differences, zero unexplained
differences, known repaired expression/format fingerprints matching, complete
remaining definition matching, stable snapshots and cloud mapping matching the
private backup. This supersedes the preceding unconfirmed readback state.
Do not rerun any updater/check or refresh to infer installation. Current step:
handoff/report-native-only-r17.4/readback-check-r01/OPEN AFTER VERIFIED READBACK.txt.
Open the unchanged R17.4 TEST ZIP's PBIP on the company laptop and check native
rendering/filter/drill/export plus numerical/performance behavior. These gates
remain unverified; metadata preservation does not establish full R16.6 parity.
Keep every frozen installer/probe/ZIP and production unchanged. Record only the
safe operator diagnostic result, never raw company model or connection values.

Later 23 October R17.4 screenshots show loading numbers/dates, but wasted space,
daily date controls, Section reduced by its selected child and collapsed
comparison columns. Current candidate is handoff/report-native-only-r17.5/.
It remains strictly native, with no custom visual or native-capability bypass.
Preserve all earlier bytes. The report compacts height to 1286, uses a labelled
monthly first/last window selector and a single Section -> Measure hierarchy,
retains 6M/12M/24M table multi-selection, and configures full variance expansion.
Native matrix height/reflow is not dynamic; retain scroll and Focus mode.

R17.5 requires exactly two existing TEST chart expression changes: chart-window
admission follows the graph/headline window independently of table comparisons,
Demand forecast joins at its last actual value, and shared view labels admit
the selected Drivers/Sectors/Both context. No monthly/period/ratio/fit/source
arithmetic or format is rewritten. Full private backup, known-body checks,
concurrency/mapping and complete readback remain; only identical DAX string/line
representations are equivalent. No new model/helper, source refresh or publish.
Three report-level Text measures supply native formatting only. Their line-style
rendering, native slicer hierarchy/column expansion, company runtime/export and
numerical/performance acceptance are unverified until receiving evidence arrives.
The Windows UI tool failed before connecting; schema/mocks are not a UI pass.

Later 23 October the operator reports TEST_R175_UPDATED, native solid/dashed/
dotted line styles, and two 10,240 MB rsQueryMemoryLimitExceeded summaries.
The copied Review Summary DAX shows __ValueFilterConstraintDM0 evaluating the
summary/format, followed by __ValueFilterDM0 on N R175 Measure Selected and
the main __DS0Core calculation. Do not call refresh the missing fix: R17.5 was
measure-only. Current candidate is handoff/report-native-only-r17.6/. It removes
that visual value filter and repeated benchmark-based color formatting, moves
selection/source admission into display bodies and flattens comparison labels.
Preserve all source/monthly/period/ratio/fit/variance expressions and formats.

R17.6 restores separate Section/Measure with Metric -> Section NoFilter. A
changed Section can leave a stale native child selection; require choosing a
valid Measure and show blanks/prompt instead of defaulting to Market. Two new
disconnected monthly dictionaries provide Start/End. Invalid order stays blank.
Single graph/review and multiple table trend selectors sit beside their headings
and have NoFilter interactions with the other summary. Matrix height remains
fixed with native drill/scroll/Focus mode; no automatic height/reflow is claimed.
All visuals remain built in and old buttons/custom fallbacks remain absent.

Run only ONE NEW R17.6 cell in ForecastMaster_GM_Setup; require successful full
readback, then refresh EXISTING R17.1 TEST ONCE to process its new helpers before
opening R17.6 PBIP. This new refresh instruction applies to R17.6, not R17.5.
New helper count is 24, with 49 native measures retained. The update preserves
private full-file backups, cloud/concurrency/no-purge guards and complete model
comparison; identical DAX line representations are tolerated only for measures/
formats and the three allowlisted calculated helpers. No source or security
metadata is ignored. Unknown post-write state must not cause a retry/refresh.
No source ingestion or production replacement. The July unavailable Automatic
ADS example must not silently fall back to historical V18 files. Local schema/
metadata/mock checks do not qualify company memory, calculation or Desktop UI.

Later 23 October R17.6 screenshots show loading summaries/variance columns,
with measured slow DAX: graph 26190ms, Review 17367ms, Executive 4742ms. The
timing reply did not specify view/cache; screenshots show Sectors. Current
package is handoff/report-native-only-r17.7/. The user explicitly authorizes
native usability and speed optimization, including examining Fabric/database
design. Production R16.6 and retention/security/connection contracts remain.

R17.7 uses compact labelled controls, native end-of-line/scope-first labels,
actual import UTC metadata and searchable classic file checkboxes without Ctrl.
Native ApplyAllSlicers buttons defer all page choices until Apply. Desktop edit
mode needs Ctrl+click for the ACTION BUTTON, not file selection. Do not remove
pending-state headers or reintroduce custom visuals/selection-button workarounds.
Manual file IDs intersect the original file/country/cycle context. Automatic ADS
stays default and ignores manual choices. Compare saved scenarios in separate
groups; do not sum alternative versions or bypass tie/coverage guards. Import
time is ingestion time, not modified/approved/published status. Unknown import
timestamps stay unavailable. Reuse the existing scenario-mode relationship.

The performance patch reuses fit coefficients, moves fitting out of benchmark
month loops, skips unused denominators and projects Sector/Amount/MissingCells
without removing duplicates. The exact N Line Visible predicate moves into N
Chart Monthly, eliminating its external visual measure-filter path. Native
measure count becomes 51; helper-table count stays 24, with three new metadata
columns. Source tables/roles/relationships/formats/refresh worker stay preserved.
No unmeasured physical Delta rewrite, aggregation cache, purge or memory-limit
increase is authorized by a local test pass.

R17.7's ONE NEW setup cell performs a mandatory read-only numerical preflight
before any model write: 72 old/candidate values using SemPy virtual DEFINE
MEASURE overrides on one available ADS driver. Compare blanks separately from
zero and require informative benchmark/future-trend observations. No amount
values may be printed or stored. Unavailable access/compile failure/mismatch/
incomplete or uninformative results refuse the write; do not bypass or request
tenant/IT changes. Only after passing, verify private backups/concurrency/cloud
mapping, update once with no purge, then full readback. On success process ONLY
existing TEST once and open R17.7. Keep old packages and private backups.
Local metadata/mock/algebra/schema checks and a synthetic endpoint probe are
not DAX execution, company speed or native UI proof. Receiving numerical checks,
metadata processing, same-selection warm/cold timings and UI/export remain gates.

Later 23 October the R17.7 run failed at the baseline evaluate_dax call with
FabricAdomdException after scope metadata succeeded. It did not reach candidate
overrides, private backups or updateDefinition. Underlying cause is unknown;
do not label the exception type alone a permissions, syntax or memory problem.
Current step is handoff/report-native-only-r17.7/preflight-check-r01/. Run only
its ONE NEW read-only diagnostic cell, returning safe JSON with individual
baseline read status/error categories. Never print/store company amounts or
raw exceptions in this public handoff. Preserve the original R17.7 bytes.
Completed small reads do not replace the mandatory old/candidate parity check.
Keep R17.6; no updater retry, TEST refresh or R17.7 installation claim until the
diagnostic is reviewed. No production change or tenant/admin workaround.
