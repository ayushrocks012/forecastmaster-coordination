# ForecastMaster executive review — R07 design preview

**Open [index.html](index.html) in Edge or Chrome.** In a local clone, double-click
the file in File Explorer; GitHub's file viewer displays its source rather than
running it. No server, sign-in, installation or company connection is needed.
All names, source files and values in the preview are illustrative.

This is a reviewable HTML prototype. It is **awaiting the user's design approval**.
It does not update the Power BI report, semantic model, custom visual, Functions,
Activator rules, notebooks, pipelines or schedules. The prepared R04.2 performance
package remains a separate implementation with company installation unverified.

## Try the new Both view

1. The selection area initially shows **Both · driver → tier**. Core Oral and
   Paed SIP appear with sector checkboxes underneath. Uncheck Juce: Core Oral
   becomes partially selected and its total includes only Compact.
2. Choose **Both · driver + tiers** above the graph. Each driver has a monthly
   chart containing its selected total and its individual sector lines. Actuals,
   forecast and the selected trend benchmark follow the same scope. These charts
   have independently labelled vertical scales; choose **By growth driver** for
   a shared-scale comparison of driver totals.
3. The table initially shows **Both · driver → tier**: Total, driver subtotal,
   then indented sector rows. Subtotals are recomputed from the selected source
   components; they are not added a second time to the grand total.
4. Try **Growth drivers** or **Forecast tiers (sectors)** in the table. These
   change the row layout and preserve the selection and grand total.
5. Add **2026 YTG** using the summary period dropdown. It adds another group of
   columns beside 2026 FY. Choose 6M, 12M and/or 24M variance columns.

The existing driver-only, sector-only and combined graph options remain.
Graph grouping and table row layout can differ; both use the same selected data.
Selecting a driver includes all its child tiers. Selecting individual tiers can
span multiple drivers. Search changes the choices displayed, not the selected
data. Select all and Clear all apply to the whole review scope.

## Design decisions carried forward

- Top filters set cycle, channel, subchannel, section and measure. The adjacent
  review selection sets growth drivers and tiers. These are shared data filters;
  the graph/table view buttons control presentation only. The user liked the
  current layout after its purpose was explained; R07 adds Both without merging
  or replacing those controls.
- Default graph: combined selected total, 12M trend. Default table: driver and
  sector hierarchy, 2026 FY, all three trend windows. Monthly graph retained;
  monthly detail table and unrequested ADS decision controls remain absent.
- Table: Total Plan, then signed absolute and percentage variance for each chosen
  6M/12M/24M trend. Positive plan minus trend means overcall; negative means
  undercall. Trend totals are not displayed. Share totals are ratios of summed
  components rather than sums of percentages.
- Matching files stays below the summary. The executive can use the default ADS
  plan without selecting files. Source preference per cycle and driver is
  **Plan ADS → ADS → highest numeric ADS suffix**. Mixed numbered ADS versions
  for different drivers form one plan. Missing or tied ambiguous ADS sources
  are reported; no other planner is silently substituted and no complete total
  is invented. Manual comparisons and restoring the ADS default remain available.
- Largest gaps first sorts drivers and their child tiers within each driver in
  Both mode. Flat sector mode ranks sectors across the selected drivers.

## Performance and implementation boundary

Interactions here run against a small in-memory synthetic dataset. That shows
the intended behaviour; it is not evidence of live Power BI speed or company
data correctness. The proposed production direction is demand-cycle aggregate
loading followed by local driver, tier, measure and view changes. The final
production data mapping, complete segment loading, refreshed-data replacement,
unchanged arithmetic and company response times still need qualification after
design approval. Nothing in this folder should be imported into Fabric.

## Files and validation

- [index.html](index.html): standalone preview, open this first.
- [review.fragment.html](review.fragment.html): editable inline source.
- [overview.png](overview.png): default combined graph and hierarchy table.
- [both-views.png](both-views.png): Both graph and Both table together.
- [previous-r06.html](previous-r06.html): preserved preceding design for comparison.
- [validation-hierarchy.json](validation-hierarchy.json): hierarchy interactions,
  subtotal arithmetic, ratio aggregation, period columns and responsive checks.
- [validation-ads.json](validation-ads.json): retained source-selection regression
  checks, including missing and ambiguous ADS candidates.

Browser checks use Node.js and Playwright. With Playwright installed and its
Chromium browser available, run from this directory:

```bash
node check-ads-default.cjs
node check-hierarchy.cjs
```

`PLAYWRIGHT_MODULE` may name an already installed Playwright module. Normal
Playwright browser-path environment variables are supported. Both scripts write
their JSON receipt and screenshots into this folder. These are optional developer
checks, not prerequisites for viewing the preview.
