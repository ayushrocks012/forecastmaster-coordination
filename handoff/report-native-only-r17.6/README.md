# Native-only R17.6 TEST

Open [OPEN FIRST - R17.6.txt](OPEN%20FIRST%20-%20R17.6.txt) on the company laptop.
R17.5's measure-only update did not need a refresh. R17.6 adds monthly helper
tables, so after its successful update the existing TEST needs one refresh.

The operator's R17.5 screenshots confirm native solid/dashed/dotted line
formatting. Both summary queries instead hit their 10,240 MB memory limit.
The copied Review Summary query explicitly computes the summary and dynamic
format in `__ValueFilterConstraintDM0`, feeds that into `__ValueFilterDM0` for
`N R175 Measure Selected = 1`, and then references the summary again in
`__DS0Core`. This is evidence of redundant query work, not a measured allocation
breakdown or proof that it is the only memory cause. The selected July source
is also unavailable under Automatic ADS; refreshing cannot create that source.

R17.6 removes the report-level selection measure and its visual value filters.
It gates the existing displayed measures by one selected metric and the existing
metadata-only source check, before period/fit work. It removes the Executive
Summary color helper that re-evaluated its numeric calculation for formatting.
Executive columns use period > flat comparison label, with amount and percent
as distinct labels. This avoids the extra comparison > variance-unit level;
all seven existing leaf identities/calculations remain. Row drill is still
growth driver > sector. This is a query repair candidate; the company query's
memory/latency and Desktop expansion remain receiving gates.

Section and Measure return to separate native dropdowns. Measure cannot filter
the Section dropdown's available choices. After switching Section, select its
valid Measure; an incompatible old selection does not silently become Market.
One graph/review trend selector sits beside Review Summary; the independent
multi-select table trend selector sits beside Executive Summary. Neither
control filters the other summary's query. Two monthly dictionaries from the
existing month list provide explicit Start month and End month dropdowns, sorted
by date. They include every intervening month and reject inverted bounds.
No daily picker or custom calendar is used. Source-caption padding/gap is fixed.

Native matrix geometry has a fixed height. R17.6 retains a compact 300px viewport,
scrolling and Focus mode; it does not claim dynamic page reflow. It preserves
native chart styling, zoom/export/Focus/drill capabilities and saved-file dates.
All preview visuals are built in. There is no custom visual, script visual,
HTML visual, pbiviz resource, custom control, JS payload or R16.6 fallback page.

## Scope of the TEST update

Five existing display expressions change: `N Chart Monthly` (bounds/metric
admission only), `N Period Available`, `N Headline Cell`, `N Summary Cell`,
`N Measure Caption`. All 44 other native expressions and all dynamic formats
are preserved. The monthly numerator/denominator, trend fit, plan, benchmark,
variance, ratios, cutoffs, FX, source/cohort and missing/zero rules are unchanged.
The original seven-row `fm_native_columns` gains only `ColumnLabel`. Two small
disconnected calculated metadata tables are added, for 24 native tables total.
Original tables/roles/relationships/connection mapping are preserved.

The updater requires the verified R17.5 bodies. It has full-file private UTF-8
length/SHA256 backups, exact identity, known expression/format fingerprints,
concurrency/cloud checks, no purge and no update retry. Full readback permits
identical DAX string/line-array representations only for measure expressions,
formats and the three allowlisted calculated helpers. Other source/security/
definition changes remain failures. The cell requests no refresh/publication;
the receiving operator processes TEST once after confirmed success.

Do not rerun an updater after an ambiguous result. Keep its private before/
candidate/connection backup and send its bounded result. Restoring an older
PBIP alone does not revert a semantic-model update; any rollback must use the
exact verified private TEST backup and preserve its connection mapping.

## Verification and limits

`test_revision.py` checks geometry, aliases, native roles/control interactions,
leaf/source arithmetic preservation, known static helper definitions, generated
Python 3.10 grammar and mocked backup/update/readback/refusal behavior. Microsoft
PBIR schemas validate both new projects. These checks do not execute DAX or
prove Desktop rendering or company Direct Lake memory/numerical performance.
The local UI bridge failed before connecting in the preceding attempts, and
company access remains solely on the other laptop. The SAMPLE is fabricated.
No company model, amount result, credentials or raw screenshot is committed.
Production R16.6 and all frozen packages remain unchanged.

Primary references:

- [Microsoft Performance Analyzer](https://learn.microsoft.com/en-us/power-bi/create-reports/performance-analyzer)
  describes copying a visual's DAX through Optimize > Performance Analyzer.
- [Microsoft date slicers](https://learn.microsoft.com/en-us/power-bi/visuals/desktop-slicer-filter-date-range)
  document day/date calendars and relative month ranges. R17.6 uses explicit
  month dropdowns without claiming an arbitrary month-only native calendar.
- [Microsoft matrix formatting](https://learn.microsoft.com/en-us/power-bi/visuals/power-bi-visualization-matrix-visual-format-settings)
  and the [visual geometry schema](https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.7.0/schema.json)
  describe native matrix controls and a fixed visual rectangle.
