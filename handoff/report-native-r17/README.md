# ForecastMaster native review R17 — qualification candidate

The user requested rebuilding the published R16.6 review with native Power BI
visuals and retaining every function, allowing custom components only where
necessary. This package creates a **separate candidate**. It does not replace,
publish or modify the working company report from this host.

**Release decision: NO-GO for production replacement until the receiving gates
below pass.** Native schema checks and native-engine synthetic arithmetic are
evidence for those bounded checks, not proof of complete UI or business parity.

## Open the result

For the other laptop, follow **WORK LAPTOP - OPEN PREVIEW.txt**. After pulling
Coordination, the sample ZIP is at
`handoff/report-native-r17/preview/ForecastMaster Native Preview R17 - SYNTHETIC.zip`.
Extract it before opening the PBIP; keep the report and semantic-model folders
beside it. No builder, Python or npm step is required to view this preview.

Both ready-to-extract ZIPs are now synced through Coordination:

- **ForecastMaster Native Preview R17 - SYNTHETIC.zip** (also synced in `preview/`): open the labelled PBIP
  after extraction to inspect native visuals using fabricated data, with no
  company connection or real refresh action. Desktop rendering is unverified.
- **ForecastMaster Native Review R17 - Candidate.zip** (in `candidate/`, explicitly requested by the user): company-connected thin report
  and a default read-only model probe. Do not publish this over production yet.

For the company candidate, follow **WORK LAPTOP - OPEN CANDIDATE.txt**.
For the feature comparison, read **CAPABILITIES-VS-R16.6.md**.

Start with the preview and then the read-only probe. A successful probe does not
install the report or satisfy its receiving checks.

## Readable metadata probe

Use **READABLE PROBE - STEPS.txt** and **PROBE ONLY - READABLE.py** from this
repository. The original ZIP contains a combined installer with a 318,966-character
encoded line; carrying that installer into the read-only probe was unnecessary.
The new probe is 4,021 bytes with a maximum line length of 96 characters. It
contains no installer payload, writer lease or write/refresh/publication route.
A PowerShell command in the instructions copies its exact UTF-8 contents to the
clipboard without executing it locally. Paste into one new cell in
**ForecastMaster_GM_Setup**, the notebook identified in the receiving screenshot.

An optional one-cell **ForecastMaster Native Probe - READ ONLY.ipynb** has the
same source and no saved outputs. Eleven mocked API tests cover synchronous and
asynchronous reads, unsupported sources, existing native objects, failures and
timeout. They do not establish live company success or clipboard/UI acceptance.
The original candidate ZIP, installer and qualified business code remain intact.

API references: [model definition read](https://learn.microsoft.com/en-us/rest/api/fabric/semanticmodel/items/get-semantic-model-definition),
[operation polling](https://learn.microsoft.com/en-us/rest/api/fabric/articles/long-running-operation).

## Receiving source-mode result

**Latest result, 22 October 2026:** the second read-only probe confirmed the
fact partition references an M `AzureStorage.DataLake` expression. The company
model is Direct Lake on OneLake. Both probes are complete; no model was changed.
Do not use this frozen ZIP's SQL PREPARE/APPLY or `NATIVE VIEWS.sql`.
Continue with [OneLake R17.1 OPEN FIRST](../report-native-onelake-r17.1/OPEN%20FIRST%20-%20ONELAKE.txt),
which creates a separate TEST semantic model and retains production R16.6.
Its Direct Lake calculated-table preview processing and company acceptance
remain unverified. It does not close the R17 capability/parity gaps.

The following records the earlier diagnostic sequence, now superseded by the
confirmed OneLake route:

The operator's first probe on 22 October 2026 reported one `directLake` / `entity`
fact partition, 15 model tables, zero native tables and zero model-defined roles,
with no source amounts queried and no model update. The initial expression-only
SQL check was false. This confirms Direct Lake but does not establish the route.
Zero model-defined roles is not a check of workspace/item permissions.

`SOURCE ROUTE - STEPS.txt` and `SOURCE ROUTE - READ ONLY.py` request the missing
metadata shapes and connector hints. The latter reports no connection strings,
endpoint values, credentials or amounts, and changes nothing. Eight mocked
source/privacy tests pass. The original readable probe and installer ZIP remain
unchanged. The installer is not adapted/approved from this incomplete result.

Microsoft's [entity partition reference](https://learn.microsoft.com/en-us/dotnet/api/microsoft.analysisservices.tabular.entitypartitionsource)
exposes both DataSource and ExpressionSource. Its
[Direct Lake connection explanation](https://learn.microsoft.com/en-us/fabric/fundamentals/direct-lake-security-integration)
distinguishes SQL and OneLake connectors. Those references justify inspecting
the actual metadata; they do not establish this company's route.

## Native first

The two main pages use native line charts, native matrices, searchable slicers,
page navigation and display-only bookmarks. Power BI owns the canvas, chart
points, monthly tooltips, matrix rows, focus mode and export. There is no HTML
dashboard viewport scaling or canvas chart embedded around the figures.

The separate **Export data** page contains native tables with clean source
identities and numeric measures. It is reached from either main page. The
original native Refresh Demand page and the complete R16.6 custom workspace are
preserved; the latter is a clearly named, hidden navigation fallback during
qualification. It is not evidence that every function has already moved native.

The only new custom visual is a small **control**, not a figure renderer. It
contains the Channel → Sub-channel → Measure gates, sibling drag ordering, reset
and plan-rate input. It sends filter tokens to the model. It never calculates
sales, shares, forecasts, trends, period totals, run rates or growth, and has no
network privileges. There is no writeback of rates or sales into the source data.

Native what-if parameters use an enumerated numeric domain. The rate control
instead encodes six three-digit chunks plus an exponent into a small preference
table; missing and zero remain separate. Rate testing includes synthetic GBP,
EUR and USD. Only the real known UK → GBP mapping is included in the receiving
adapter. Additional mappings must come from actual source metadata, not guesses.

## Calculations and source selection

All figure arithmetic is model DAX. Each selected Affiliate/cycle/driver cohort
requires an unambiguous source. Automatic preference is Plan ADS, then ADS, then
the highest numbered ADS revision, with retained import time as the next ordering
criterion. A true tie withholds the cohort. Explicit selected-file scenarios are
separate comparisons, never an additive sum of two versions of the same plan.

The DAX retains SUM_AVAILABLE_V1 monthly aggregate display, strict missing leaf
observations, complete required period months, independent available numerator
and denominator populations, weighted period share and aggregate-level linear
6/12/24-month fits. An entirely unreported month is unavailable. The benchmark
retains actuals through the saved cutoff and substitutes the fitted future only.
Separate IMS and EF cutoffs determine YTD/YTG and actual/forecast boundaries.

Named FY periods remain January–December even when chart months are narrower.
Review months constrain available summary years. Run rate is amount / the exact
number of applicable months. Growth shifts that exact current calendar back one
year; it does not recompute last year's cutoff. Share has neither run-rate nor
growth rows. PI and IMS minus PI omit growth. The monthly view suppresses the
redundant run rate and supports eligible same-month-PY growth.

Monetary totals convert each currency before summing, using one current selected
rate per currency across every year. Unknown currency metadata or a missing
required rate remains unavailable. A single known-currency share is neutral to
FX; mixed-currency value shares use a common basis on both sides. No blank is
changed to zero to make a figure appear complete. Native numeric cells can show
blank instead of the HTML dash; zero remains numeric zero. Labels and formats do
not change the exported numeric measure value.

## Model adapter and performance

The existing thin/live connection is retained. The candidate needs additive
`fm_native_*` metadata objects in the same model. It does not create a copied
sales fact, import a private export, change existing source measures, remove
RLS, or modify the refresh worker.

The supplied adapter currently supports an existing **Direct Lake on SQL entity
partition**. The actual company's partition mode cannot be determined from its
thin report alone. `PROBE NATIVE MODEL.py` is therefore read-only by default and
reports compatibility before any write. If the model uses Import, DirectQuery,
Direct Lake on OneLake or another source shape, preserve it and adapt that source
route; **do not convert its storage mode or request tenant-admin changes**.

For a compatible source, one preparation creates small static metadata tables.
Five SQL views expose current source identities, scope, comparison groups,
scenarios and line identities dynamically. New files/sectors therefore do not
need a repeated metadata-generation notebook. These views contain no sales
amounts. The existing fact remains authoritative.

The definition update adds only new tables and helper relationships. Existing
tables, roles, expressions and other settings are preserved. The installer uses
the existing qualified writer lease, keeps private full-definition backups,
rechecks concurrent changes, disables data purging and checks existing-table and
role readback. PROBE does not acquire a lease or change anything. PREPARE/APPLY
are explicit later operator stages, not automatic follow-ons from PROBE.

Native views request scoped aggregates instead of downloading the whole monthly
feed into an HTML visual. State → line, State → presentation rows, Display → line and View → line
relationships prune the line domain before querying. The logical line view can
still be large with many scopes/versions. SQL-view fallback, query plans, cold
capacity and real 500-tier response time need measurement; no 'ultra fast'
company performance claim is made from the small synthetic model.

## Exactness ledger — do not silently waive these

| Function | Candidate | Remaining receiving gate / difference |
| --- | --- | --- |
| Period amounts, shares and aggregate fits | Native DAX | Company bridge reconciliation; local synthetic engine checks are recorded separately |
| Monthly chart points and tooltip buckets | Native line charts | Confirm actual/monthly bucket behavior in Desktop and Service |
| Amount + share right axis | Native Y and secondary-Y fields | Verify the receiving Desktop version supports the configured legend/secondary-axis combination |
| Actual / forecast / trend separation | Native separate line identities | Verify native line styling and make forecast/trend distinctions clear; exact dynamic HTML dash styling is not yet qualified |
| Driver and sector comparison, total and both | Native line groups; independent matrix layouts | Verify all four graph modes and all three table modes with retained selections |
| Growth driver / tier selection | Compact native hierarchical dropdown | Explicit native Select all / Clear all bookmarks request all/empty without inventing a data row. Native eraser still means Reset to All. Verify empty-state filtering, recovery and cross-page sync before calling parity complete |
| Review-period selection | Native multi-select slicer plus all/empty bookmarks | Verify explicit empty-state and recovery; year availability and named-period arithmetic are separate checks |
| Channel / sub-channel / measure gates | Small custom control, native data visuals | Verify enabling without auto-selecting descendants and all actual 18 identities |
| Drag/reset order | Custom preference tokens; native row/line sorting | Verify native host filter application, sibling-only drag, keyboard movement, reset and cross-page sync |
| Clean exports | Dedicated native export tables | Presentation rank labels include invisible ordering suffixes. Use Export data for clean join keys; verify XLSX/CSV values, blanks and identities before release |
| Local/USD, per-currency plan rates | Small custom editor, native DAX | Verify native filter/slicer sync and actual multi-affiliate mapping before claiming generic deployment |
| Source versions and automatic ADS | Dynamic metadata views + native selection | Verify the SQL view rank/parser against actual file labels; do not rely solely on synthetic DAX |
| Run-rate / PY switches | Native slicers and numeric measures | Verify automatic removal of entirely blank measure columns in both matrix modes; preserve Share/PI/net eligibility |
| Multiple Demand measures / simultaneous chart trends | Single-select metric and chart trend | R16.6 supports several; native parity is unfinished. Multi-trend table comparisons remain |
| Half-year periods / S&OP summary scope breakdown | Missing in the native pages | H1/H2 and S&OP per-driver/per-sector summary rows need implementation |
| Tooltip pin and exact hover emphasis | Standard native interaction only | Custom click-to-pin and linked hover treatment are not reproduced |
| Gap ranking and row sorting | Native matrix sorting | Exact saved largest-absolute-gap shortcut and its rank-period control are not yet reproduced; retain Advanced workspace until this passes |
| Hide/Show | Native display-only bookmarks | Verify slicers and monthly/period table view survive hiding; native Focus mode provides full-size viewing. Automatic HTML reflow is not reproduced |
| Personal bookmarks and personalization | Native report visuals/settings | Verify saved native selections, custom filter restoration and header actions in Service |
| Native zoom/Fit/focus/export | Actual native visuals | Native engine tests do not verify UI. Receiving Desktop/Service checks remain mandatory |
| Refresh Demand and published access | Existing page/connection preserved | Do not replace the Service report until the candidate is accepted |

The additional source comparison also found cross-year YTD/YTG, mixed-cutoff
and negative-benchmark percentage differences. See the comparison document;
the existing synthetic checks do not qualify those cases.

The full R16.6 fallback protects current functionality while these gaps are
resolved. It is **not** a reason to mark native parity achieved.

## Reproduce and deliver

`native_model.py` owns source-free model additions, rules and SQL-view text.
`installation.py` renders a private default-PROBE notebook cell from the existing
connection identifiers. `prepare_project.py` creates a new PBIP and checks input
and Refresh Demand preservation. `build_delivery.py` assembles the private ZIP.

The standard-library fixture/oracle scripts create only fabricated identities
and observations. `tests/native_fixture.py` generates a model that can be loaded
into a **task-owned local Power BI Analysis Services engine**, then checks its
query results against independent arithmetic. `tests/fx_cases.py` covers common
currency bases, missing rates, zero rates and numeric export values. The engine
scripts must not connect to an arbitrary user model. `tests/run_native_engine.ps1`
requires an explicit task-owned engine port, refuses non-calculated partitions,
creates a fresh synthetic database and preserves each query result in a new
run directory. It does not edit an existing company or user database. Controller tests mock host
filters and never replace actual receiving UI checks.

Local qualification on 22 October 2026 passed 2,593 primary calculation checks,
3,888 currency checks and 16 scenario/export/plot checks in the local native
Power BI Analysis Services engine. Twelve controller checks passed in Edge with
a mocked host. PBIR schema checks are recorded separately; two unchanged legacy
visual schema URLs returned 404. The Computer Use runtime could not initialize
for this WSL chat, so no Desktop rendering or native interaction gate is claimed.

Row labels are in a separate helper table from preference filters. This avoids
DAX auto-exist removing currency tokens while a matrix evaluates one row. The
actual engine checks cover the USD amount after that row filter.

The user subsequently explicitly requested syncing the connected thin-report
candidate here. Its original ZIP is now in `candidate/`, with connection
identifiers preserved and an archive/credential/cache audit receipt. Coordination
is public. Keep credentials, exported company figures, cached/full data models
and private execution/backup definitions outside it. The original R16.6 package is
unchanged. GitNexus coverage is partial and is not proof of zero impact.

Official feasibility references:

- [Native line charts, axes, legends and limitations](https://learn.microsoft.com/en-gb/power-bi/visuals/power-bi-line-chart)
- [Field parameter limitations and local models](https://learn.microsoft.com/en-us/power-bi/create-reports/power-bi-field-parameters)
- [Numeric what-if parameters](https://learn.microsoft.com/en-us/power-bi/transform-model/desktop-what-if)
- [Direct Lake source modes and SQL-view fallback](https://learn.microsoft.com/en-us/fabric/fundamentals/direct-lake-develop)
- [Get model definition](https://learn.microsoft.com/en-us/rest/api/fabric/semanticmodel/items/get-semantic-model-definition)
- [Update definition and purge protection](https://learn.microsoft.com/en-us/rest/api/fabric/semanticmodel/items/update-semantic-model-definition)
