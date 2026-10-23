# R17.5 native Demand Review candidate

The receiving R17.4 screenshots show correctly scaled numbers and month-name
cutoffs, but excessive vertical spacing, a daily calendar, a self-filtered
Section list, uniform chart strokes/point markers and collapsed variance columns.
R17.4 model readback was separately verified. These are new presentation and
chart-selection corrections; production remains unchanged.

Follow [OPEN FIRST - R17.5.txt](OPEN%20FIRST%20-%20R17.5.txt). The TEST update
changes exactly **N Chart Monthly** and **N Line Visible**, then the new thin
PBIP uses that same existing TEST. No new model/helper, connection edit, source
refresh or publication is requested. Keep the R17.4 readback backup and package.

The chart previously followed `fm_native_trend` (table comparisons), even when
Headline trend selected another window. Both chart admissions now use the
independent chart-window table; the fit calculation is unchanged. Forecast gets
one connecting point at the last actual month, using that month's existing
actual value. It is a drawing anchor, not a newly reported forecast observation;
published/source figures remain unchanged. This anchor applies only to Demand.
Driver/sector labels appear in both Drivers/Sectors and Both views, so chart
admission now checks whether the selected view belongs to the label's view set,
instead of requiring a unique view type. All scope/cohort/missing/FX guards and
monthly/period/ratio/fit arithmetic are retained. All dynamic formats remain
unchanged. A restore comparison proves no unrelated definition properties move.

The updater verifies known native expressions/formats, 22 helpers, exact TEST
identity, full private backups, concurrency and cloud mapping. It makes at most
one no-purge update. Full-definition readback uses the same narrow identical-DAX
line-representation comparison qualified by the R17.4 receiving result; source,
security, ordering and all other unexplained differences still block success.
Unknown inputs fail closed. There is no production write or amount query.

The report compacts the page from 1860 to 1286 units, retaining native zoom,
Focus mode, export, source metadata and driver/sector drill. A single native
Section -> Measure hierarchy keeps all six existing choices while preventing
incompatible filters from separate slicers. A chronological month dropdown
formats the existing month-start dictionary as `MMM yyyy`; the first and last
selected month define an inclusive window. This matches existing MIN/MAX DAX;
it is explicitly labelled as bounds, not a sparse set. Default bounds are
Jan 2025-Dec 2027, with 2026 FY/YTD/YTG and 2027 FY summary periods selected.
Table comparison multi-selection remains independent of the chart window.
Choosing only a broad multi-measure parent or clearing Measure suppresses the
numeric visuals and prompts for a leaf measure. Two report-local metadata-only
guard/caption measures enforce this, preventing a silent fallback to Market.

The executive column fields are active and explicitly expanded through known
period/comparison nodes, retaining existing plan/absolute/% arithmetic and
actual-only suppression. Rows still drill from driver to sector. Columns use
fit-to-content widths to avoid stretching small tables across the whole page.
Three report-level **Text** measures provide scope colors, solid/dashed/dotted
strokes, and variance-cell colors. These are native DAX formatting definitions,
not custom visuals or amount calculations. Monthly observations, dates and
missing gaps are not smoothed/interpolated. Small point markers are removed.

The matrix retains a fixed 300-unit canvas viewport. No supported content-driven
height/reflow is implemented; use native scroll and Focus mode. Microsoft's
[matrix settings](https://learn.microsoft.com/en-us/power-bi/visuals/power-bi-visualization-matrix-visual-format-settings)
document compact layouts, padding and column sizing; the native
[visual container schema](https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.7.0/schema.json)
stores numeric canvas geometry. These do not establish automatic row-driven
resizing/reflow. No custom workaround is included.

`VALIDATION.json` distinguishes local contracts/API mocks and Microsoft JSON
schemas from **pending Desktop rendering, line-style expression evaluation,
hierarchy selection/column expansion, export, Direct Lake runtime and company
numerical/performance acceptance**. The local UI bridge failed before selecting
a window; it did not test this candidate. Schema-valid formatting expressions
are not proof that Desktop renders the requested styles. The SAMPLE model is
fabricated; it preserves the R17.4 fixture except the same two chart expressions.
S&OP, FX editing, manual source overrides and other previously deferred parity
items remain deferred. Full R16.6 parity is not claimed.

Developer entrypoints: `build_cell.py`, `prepare_project.py`, `test_revision.py`.
Generate from the frozen R17.4 TEST ZIP; call `sample_from_frozen` for SAMPLE.
Run the focused tests and the existing Microsoft schema checker on both folders.
The report binding must remain byte-identical and TEST must contain no model.
All earlier installer, diagnostic and ZIP bytes are preserved.

Native authoring sources: Microsoft's
[cartesian formatting reference](https://raw.githubusercontent.com/microsoft/skills-for-fabric/main/skills/powerbi-report-cli/references/authoring/cartesian-part-02.md),
[table/matrix reference](https://raw.githubusercontent.com/microsoft/skills-for-fabric/main/skills/powerbi-report-cli/references/authoring/table.md),
and [report-extension schema](https://developer.microsoft.com/json-schemas/fabric/item/report/definition/reportExtension/1.0.0/schema.json).
