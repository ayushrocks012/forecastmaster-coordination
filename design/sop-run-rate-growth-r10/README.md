# Second page R10 — Spacing, monthly run rate and prior-year growth

Open [index.html](index.html). This separately saved proposal adds blank spacing
and two independent summary switches to R09. The approved first page and every
earlier saved design remain preserved. Power BI implementation is still paused.

## Confirmed bridge design

The current bridge reporting oracle, V18 template, BR-005 period rules and S&OP
Summary reference analysis were inspected read-only. `summary-rules.json` binds
those four source files by SHA256 and records the eligible executive measures.
No workbook was opened, generated or changed, and no company values were copied.

- **Monthly run rate:** complete period amount divided by its month count.
  FY has 12 months; YTD runs through the measure's cutoff; YTG uses the remaining
  months. IMS and Ex-factory retain their separate cutoffs. Numeric zero is valid.
- **Growth vs PY:** complete current amount divided by the complete amount for
  the exact same months one year earlier, minus one. A missing or zero prior-year
  denominator stays unavailable. Growth is calculated from period totals, not
  an average of monthly growth percentages.
- **Share:** percentage only, with neither a run-rate nor a growth detail row.
- **PI and IMS minus PI:** monthly run rate, without growth, following the
  reporting oracle's S&OP block choices.
- **Abbott IMS, Market and all displayed ADS contexts:** both detail rows.

The legacy template's shared-cutoff example does not override the current
measure-specific IMS/Ex-factory calendar rule. This is code/rule confirmation,
not a fresh native Excel qualification or live Fabric binding.

## Table behavior

Both switches start off and affect only the summary. Enabling them inserts
labelled detail rows beneath each eligible selected amount. Source selections,
graph lines and the existing amount figures remain unchanged. Units/Value also
applies to run rate; growth always displays as a percentage.

An 8px blank spacer, equivalent to the reference sheet's 6pt spacing, separates
neighboring business blocks. Share stays with Abbott IMS. Merged Channel,
Sub-channel and optional Review scope labels span the amount, detail and spacer
rows correctly. There is still one column-header row, with no repeated
full-width group-heading records.

In Monthly table mode, run rate is disabled and its redundant rows are hidden:
each column already represents one month. The switch choice is remembered for
returning to FY/YTD/YTG. Growth compares each month with the same month last year.
Unsupported history remains blank rather than being invented.

R09's catalogue, audit script and audit receipt are byte-identical copies. All
18 executive source identities, 13 contexts, source order and selection gates
are retained. Homecare/Hospital continue to expose ADS Units/Value only. No
additional business measure or Channel is introduced by the summary switches.

## Checks and review

`validation.json` records 16 browser integration groups:

- 384 independent fixture comparisons for both derived calculations, dimensions,
  cycles and cutoff bases, including missing/zero history behavior;
- 216 amount values matching R09 exactly and 64 retained reconciliations;
- switch independence, graph stability, monthly-mode behavior, source order,
  correct merged-cell geometry and blank spacing;
- responsive light/dark layouts, hover, no script errors and no warm network
  requests.

`summary-stats.png` shows the table with both switches enabled; `derived.png`
shows the full selected page. Initial results remain empty until a Channel,
its real context and a Measure are selected. `preservation.json` verifies all
preceding saved design files against their prior manifest hashes.

All numeric observations are synthetic. These checks do not establish live
Power BI speed, source binding or report deployment. To edit, change the literal
`page.fragment.html`, build with `build.py`, render the standalone wrapper with
the installed visualization renderer and run `check-sop.cjs` in Playwright.
