# R17 native candidate versus R16.6

This is a code-based comparison of the prepared R17 candidate ZIP with the
retained R16.6 runtime, checked on 22 October 2026. It is not Desktop/Service
acceptance or an exhaustive workbook audit. R16.6 remains the published version.

**R17 is not yet a functionally equivalent native replacement.** The earlier
short handoff understated several gaps. These are unfinished implementation
items; they have not been established as unavoidable native Power BI limits.
The complete R16.6 Advanced workspace remains in the connected candidate, but
fallback access does not count as native parity.

## Definite gaps in the native pages

| R16.6 capability | Native R17 candidate | Effect on the reviewer |
| --- | --- | --- |
| Select several Demand measures | Demand metric slicer is single-select | One Demand measure at a time. S&OP still supports multiple measures through its control. |
| Overlay 6M, 12M and 24M trends together on the Demand chart | Chart/headline trend is single-select | One trend line/window at a time. The executive table can still request several trend comparisons. |
| H1 and H2 review summary periods | Not supplied by the current native period feed; native DAX also lacks half-year window handling | Half-year summaries are missing. FY/YTD/YTG are the implemented native period families. |
| S&OP summary broken out by selected growth drivers or sectors | Native S&OP matrix rows contain cycle/scenario and Channel/Sub-channel/Measure only | Its current table aggregates the selected driver/sector scope. Changing Chart view does not add a driver/sector breakdown to that table. |
| Largest absolute gaps first, with an explicit ranking period/trend | Exact shortcut and ranking controls not reproduced | Native ordinary sorting is available; the previous GM shortcut is missing. |
| Pin the chart's monthly tooltip/readout by clicking | Custom click-to-pin is not reproduced in the native chart | Standard native tooltips replace the pinned custom readout. Native point selection/focus is a different interaction. |
| Exact hover emphasis linking the custom legend/table/lines | No corresponding custom linkage is installed around the native visuals | Native selections/interactions require host testing; the previous hover treatment is not reproduced. |
| Hiding a selector/graph/table makes the remaining HTML content flow into the space | Native bookmarks hide fixed canvas objects; they do not reflow the layout | Hide/Show remains, but blank canvas space may remain. Native Focus mode is the current full-size alternative. |

## Calculation cases that are not yet equivalent

These are reasons to keep the candidate out of production, rather than hide the
difference with formatting or infer parity from the 6,497 synthetic checks.

- **YTD/YTG for years other than the saved cutoff year:** R16.6 derives the month
  number of the saved cutoff and applies it to the chosen review year. R17 uses
  full-date clipping against the saved cutoff. For example, a 2026 cutoff can
  produce different 2024 or 2027 YTD/YTG windows. The native fixture's YTD/YTG
  checks cover 2026, not that cross-year parity. Reconcile and agree this before
  adding historical/future YTD/YTG to an accepted report.
- **Sources with different actual cutoffs:** R16.6 has earliest-cutoff paths;
  R17's cutoff measure requires one shared cutoff and otherwise withholds
  results. Combining such sources is not currently equivalent.
- **Negative trend/benchmark percentages:** the R16.6 variance percentage uses
  the absolute benchmark as its denominator; native `N Variance %` divides by
  the signed benchmark. A negative benchmark can therefore reverse the displayed
  percentage sign. Positive-benchmark test results do not settle this case.

The source comparison identifies these differences. It does not decide a new
business rule or change either implementation in this handoff.

## Implemented, but still requiring receiving verification

- Native monthly points/tooltips, zoom/Fit/focus and native numeric exports.
- Actual/forecast/trend line styling and Amount plus Share on the right axis.
- Compact hierarchical growth-driver/tier selection, native all/empty bookmarks,
  year availability and synced selections across the two native pages.
- Channel/context/measure gates, sibling drag/reset order and rates. These remain
  in one small custom control; their host filter/bookmark behavior is unverified.
- Automatic ADS source preference and separate saved-version scenarios. The SQL
  source parser and rankings still need comparison with the real company files.
- Run-rate/PY eligibility and values. Entirely empty measure columns may remain
  visible; removal/retention behavior has not been checked in the native host.
- Company model compatibility, RLS behavior, real business reconciliation and
  performance at the intended growth-driver/sector scale.

The local native engine checks tested implemented positive and missing-value
cases, weighted shares, period sums, aggregate trends, rates and selected
exports. They did not render the report or prove complete parity with R16.6.

## Deliberate presentation/architecture changes

- Two actual native report pages replace the custom workspace's internal view
  switch. Native navigation and synced slicers are configured; their state
  retention must be verified on the receiving laptop.
- Unavailable numeric cells are native blanks rather than the HTML dash. A real
  zero remains numeric zero; this is a presentation difference, not permission
  to turn missing data into zero.
- Native visuals issue model queries rather than retain R16.6's full monthly
  cycle cache in one HTML runtime. Real responsiveness must be measured.
- A clean Export data page avoids invisible ordering suffixes in presentation
  labels. Export from that page is the intended clean-identity route; native
  XLSX/CSV output still needs verification.
- Native support requires additive model tables, relationships and measures.
  Opening the company PBIP before those are installed can show missing-field
  errors. The read-only probe must identify the actual source mode first.

## Receiving files

The original connected candidate ZIP is now at:
`handoff/report-native-r17/candidate/ForecastMaster Native Review R17 - Candidate.zip`

It is byte-identical to the prepared candidate, with company connection
identifiers preserved. The user explicitly requested placing it in Coordination.
The repository is public; the package audit found no stored credential patterns,
cached sales model, PBIX/PBIT or local model cache. Company model access still
requires normal authentication and existing permissions. Do not add exported
company figures, tokens, full data models or private execution backups here.

Follow **WORK LAPTOP - OPEN CANDIDATE.txt**. Start with PROBE only; do not replace
production until the definite gaps and receiving checks are resolved.
