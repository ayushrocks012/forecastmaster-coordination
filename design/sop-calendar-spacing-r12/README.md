# Second page R12 — Calendar-linked periods and consistent spacing

Open [index.html](index.html). This revision connects the S&OP summary's available
years to the top From/To selection and makes spacing visible at every measure,
Sub-channel and Channel boundary. R11 and all earlier designs remain saved.
Power BI implementation is still paused.

## Calendar behavior

The top calendars are now labelled **Review months**. January–December 2026
offers 2026 FY/YTD/YTG only. Extending into 2027 adds that year's choices; it
does not automatically select additional columns. Narrowing the range removes
selected out-of-range columns and choices, including from a hidden summary or
an already-open period picker.

When the range moves entirely to other years, the selected period kinds move
with it (for example, FY becomes FY for the new year). Explicitly clearing the
period selection stays empty across calendar changes. Existing valid choices
are retained when the ranges overlap.

FY still means January–December, and YTD/YTG retain the measure's IMS/Ex-factory
cutoff month. They are not silently clipped into partial periods by graph dates.
The summary states this distinction beside its controls. Monthly mode uses
exactly the selected From/To months. The candidate years follow the synthetic
data horizon, 2024–2029, with the existing FY/YTD/YTG calculation kinds.

## Spacing

Every selected measure block now has a small, visibly contrasting **6px gap**
before the next block, including Share and Abbott IMS. The same spacing separates
Sub-channels, Channels and review groups. Optional run-rate/growth detail rows
remain together with their amount row rather than receiving separate gaps.

Merged hierarchy cells continue across related rows. A measure gap spans Measure
and the numeric columns; a Sub-channel gap also spans Sub-channel, and a Channel
gap spans that hierarchy too. Blank gaps contain no values and are excluded from
screen-reader narration. The bridge's reference analysis confirms blank spacer
rows between business blocks; the tighter 6px treatment follows this user's
request rather than changing the source workbook.

## Preservation and verification

Source catalogue and audit files are byte-identical to R11. `summary-rules.json`
updates only its revision and presentation/calendar-scope metadata; eligibility,
run-rate, growth and month-window calculation rules remain unchanged. All
existing source amounts, Share semantics and independent Hide/Show behavior are
retained. The approved first page, application checkout and workbooks are untouched.

`validation.json` records 18 browser integration groups, including live picker
refresh, one-/multi-year selection, stale-column removal, year remapping,
explicit clearing, hidden-summary refresh and exact monthly columns. Spacing
checks cover all 17 boundaries for all 18 selected source measures, including
five Channel, seven Sub-channel and five measure boundaries. Merged-cell
geometry and the same small, contrasting spacer height are checked.

The checks also retain 216 amount comparisons with R11, 384 derived comparisons,
64 reconciliations, all eight visibility combinations, responsive light/dark
layouts, hover and zero warm requests/script errors. `preservation.json` verifies
all preceding saved design hashes. `summary-stats.png`, `single-year.png` and
`two-years.png` show representative states. All observations remain synthetic;
these checks do not establish live Power BI source binding or performance.
