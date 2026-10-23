# Compact native R17.8 — prepared for review; company TEST installation held

The operator rejected R17.7 after reporting a Completed TEST refresh. Its
screenshots show blank summaries/chart, Dec 1899 cutoff metadata, duplicated
file presentation, full revision hashes, oversized trend headers and unwanted
Apply/Source selection controls. Applying once did not restore the visuals.
No screenshot or company amount is copied into this public package.

## Current receiving step

The returned R01 diagnostic confirms all three original `fm_review_files` rows
**inside TEST** have invalid IMS/EF cutoffs; the native helper matches them,
including both selected ADS sources. IDs match. SourceOK passes but cutoff,
fit-cutoff and period availability fail. This does not establish that physical
Lakehouse or Excel metadata is wrong.

Run the [R02 date-boundary check](read-only-check/OPEN%20DATE%20BOUNDARY%20R02.txt)
once and return JSON. It reads TEST date bindings/month-key counts and the
existing physical Lakehouse date columns/types/cardinalities. No amounts,
source/model writes, refresh or publication. Missing physical paths remain
partial evidence. Its result separates physical storage from semantic date
binding/loading and month-bound problems. A Completed refresh does not establish
that date values or visuals are correct. No date is guessed from a filename.

There is deliberately no R17.8 company updater yet. Do not run an older updater,
refresh again, install R17.8 on TEST or publish. The date/blank-state
cause remains unconfirmed until company evidence returns.

## Native layout prepared

- One searchable native checkbox file list. Filename and imported UTC time
  share a readable label; the duplicate audit table is removed. Full revision
  IDs remain internal. Same-name/second collisions receive a short v1/v2 suffix.
- No Apply filters action, source-mode dropdown or whole instruction band.
  The draft metadata adapter infers manual mode from actual file selection;
  clearing that selection restores Automatic ADS. Explicit uniqueness/coverage
  guards remain; alternative forecasts are never silently added together.
- File availability is a metadata-only measure scoped by current Affiliate,
  demand cycle and selected drivers. This corrects the disconnected list that
  showed July files in the October review.
- Chart title uses the existing dynamic measure caption in the heading band.
  There is no in-plot title, repeated static chart heading or separate key row.
  Existing native line styles/end labels and numeric formats are preserved.
- Review trend, graph view and table trends use 44px headless dropdowns with
  short labels alongside, at the right of their respective heading bands.
  Graph/review remains single-select, table comparisons remain multi-select.
- Separate Section/Measure, monthly Start/End, driver/sector controls and native
  matrix drill/expand remain. Textboxes have zero vertical padding; controls
  and titles have nonoverlapping reserved rectangles. Page height is 1330px,
  versus R17.7's 1884px (29.4% reduction). This is authored geometry, not proof
  of native Desktop text rendering at all zoom/DPI settings.

## Date correctness and preservation

The draft refuses missing/epoch/out-of-range cutoff metadata and labels the
status unavailable. It preserves all original cutoff inputs rather than
replacing them with guessed values. This guard does not repair the underlying
source issue or prove why the R17.7 plots are blank.

The draft changes selection/context/admission metadata only. R17.7 Plan,
Benchmark, Variance, Variance %, regression fits/trend arithmetic, all existing
dynamic numeric formats and original source tables/roles/relationships remain
unchanged. Thirteen existing expressions adapt source mode, metadata display
or row admission; one metadata-only availability measure and the readable
file-label expression are added/changed. There are no new tables/columns.
This is locally prepared source, not installed company evidence. A future
guarded TEST updater must qualify the actual receiving state and numerical
contexts before writing; the R17.7 preflight does not qualify these new changes.

## Packages and evidence

[R17.8 SAMPLE](candidate/ForecastMaster%20Compact%20Native%20R17.8%20SAMPLE.zip)
contains fabricated data only and no Fabric connection. It may be extracted
into a new folder and opened in Desktop to review native layout, preserving
its Report/SemanticModel folders. Its title explicitly says FABRICATED DATA.
This is optional while the diagnostic runs; do not use it for company totals
or speed. No HTML/custom-visual substitute is included.

No R17.8 TEST ZIP is published in this package. A preserved-binding TEST draft
was built and schema-checked locally, but it requires the uninstalled adapter
and is held outside the receiving package. The builder exposes SAMPLE only.

Seven local report/adapter guard tests and seven diagnostic guard tests pass.
Microsoft schemas validate 34 TEST and 33 SAMPLE JSON documents. Python 3.10
syntax parses. These checks do not execute DAX, Desktop, company interaction,
numerical reconciliation, export or performance. Matrix container height is
fixed; native drill, scrolling and Focus mode remain available. GitNexus cannot
resolve Coordination; exact source/geometry/preservation checks are bounded
fallback, with no complete graph-impact conclusion.

References: [native slicer selection/interaction](https://learn.microsoft.com/en-us/power-bi/visuals/power-bi-visualization-slicer-visual),
[Apply controls and immediate filtering](https://learn.microsoft.com/en-us/power-bi/create-reports/buttons-apply-all-clear-all-slicers),
[calculated-table refresh behavior](https://learn.microsoft.com/en-us/power-bi/transform-model/desktop-calculations-options).
