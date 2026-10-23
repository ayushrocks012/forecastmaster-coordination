# Native-only drill revision R17.4

The 23 October receiving screenshots show R17.3 opening and returning a native
headline and chart. They also show malformed number/date formats, a collapsed
executive summary displaying rounded zeros, and redundant external selection
and view buttons. The operator requested native drill and no chart axis sliders.

Start with [OPEN FIRST - NATIVE DRILL.txt](OPEN%20FIRST%20-%20NATIVE%20DRILL.txt).

This revision remains **Demand Review first, built-in Power BI visuals only**.
No custom visual, JavaScript, hidden fallback, action button or view bookmark
is included. Production R16.6 and all frozen earlier packages are unchanged.

## Report changes

- Remove six Select all/Clear all buttons. Use native slicer selection controls.
- Replace the Drivers/Sectors/Both buttons and three overlaid matrices with one
  Growth driver → Sector hierarchy. Its native drill up, drill mode, next level,
  expand and +/- controls are enabled. The driver level opens collapsed.
- Use `SectorLabel` at the lower level to retain driver identity when displaying
  all sectors without their parent level. Drilling the table does not silently
  filter the chart or page selections.
- Disable both native chart zoom sliders. Use a continuous date axis to fit
  reviewed months to the available width; underlying categories remain monthly.
  Native page zoom, Focus mode and visual-menu export remain available to test.
- Use the recovered space: remove the empty monthly readout table, compact the
  headline band, grow matrix/file columns to fit their width, and reduce page
  height from 2024 to 1860. Exact monthly values remain in native chart tooltips.
- Replace the clipped source-status table with a native value-only card. Remove
  vertical padding from native paragraph headings to prevent inner scrollbars.
- Store native date slicer `data.startDate/endDate` alongside its filter. The
  installed native range renderer reads these separately; R17.3 displayed the
  full source date domain while its saved predicate queried the cycle year.
- Change visual date formats to `MMM yyyy`. Visual formatting currently uses
  case-sensitive .NET month tokens, unlike model-level VBA-style `mmm`.

## Narrow TEST metadata repair

The new report uses the existing isolated TEST model. Correcting its number
format definitions and undefined collapsed-summary context needs **one new
TEST-only setup cell**, not a new model or a source-data refresh:

`UPDATE EXISTING TEST TO R17.4.py`

It changes only native measure dynamic-format expressions and the display
guard on `N Summary Cell`. Number scaling changes from the unsupported
`#,0.00,,"m"` / `#,0.0,"k"` placement to `#,0,,.00"m"` / `#,0,.0"k"`.
Currency, percentages, true zero and blank behavior remain intact.

The old summary selected one `ColumnKey` only at its leaf. A collapsed period
left that key blank, entered the variance-percent branch, and formatted that
small ratio as a whole number. A period parent now shows Plan; a parent that
mixes absolute variance and percentage shows blank. The full original leaf
expression is retained unchanged. All other amount, trend, ratio, source,
cohort, cutoff and missing-member expressions are byte-preserved.

The cell verifies the known native definitions, privately backs up the complete
TEST definition and connection mapping with full UTF-8 SHA-256/length checks,
checks for concurrent changes, makes at most one no-purge update, then verifies
the entire definition and cloud mapping. Unknown definitions fail closed.
It neither changes original tables/security/connection nor queries source
amounts, creates helpers, refreshes sources, publishes or writes production.
An already-installed result makes no update. Keep the private backup.

The SAMPLE ZIP contains fabricated local tables with the same repair applied.
It requires no company access or setup cell. The thin TEST ZIP contains no
model or company amounts and preserves the exact existing TEST connection.

## Evidence and limits

`VALIDATION.json` separates report/schema regressions, mocked updater guards,
and Windows formatter checks from **pending Desktop rendering/drill and company
numeric/performance acceptance**. The new subtotal wrapper has not been run
against the company model from this host. Windows formatter checks are not
Power BI UI acceptance. No company operation was executed here.

The native-only preview still uses Automatic ADS, source currency and one
Affiliate/cycle/measure at a time. S&OP, rate editing/conversion, manual saved
versions and custom drag/pin/linked-hover/reflow remain deferred. None is
silently restored with a custom visual.

Authoring references: Microsoft's [matrix drill](https://learn.microsoft.com/en-us/power-bi/consumer/end-user-drill)
and [format-string rules](https://learn.microsoft.com/en-us/power-bi/create-reports/desktop-custom-format-strings).
The latter specifies scaling commas before the decimal and distinguishes
visual-level .NET date tokens from model-level VBA tokens.

Regeneration: run `build_cell.py`; generate a fresh TEST folder from the frozen
R17.3 ZIP with `prepare_project.py`; call `create_sample()` for the local-data
copy. Run `tests/check_report.py`, `tests/check_update.py`, the Microsoft schema
checker on both folders, and `tests/format_probe.ps1` for Windows formatting.
These developer checks need no company data or authentication.
