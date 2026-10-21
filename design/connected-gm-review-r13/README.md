# Connected GM review R13 — Demand review and S&OP

Open [index.html](index.html). Use **Explore in S&OP** and **Back to Demand
review** above the pages. Both pages are included in one offline preview, with
their own literal editable fragments. No Power BI or Fabric content is changed.

## Saved checkpoint

**Before connected GM review — Demand R11 + S&OP R12** is recorded at
`../checkpoints/before-connected-gm-review-r13.json`. The checkpoint binds the
unchanged preceding page packages and the parent commit. To compare or return
to either design, open the saved Demand R11 or S&OP R12 links in `design/index.html`.
No Git reset or live-report replacement is needed. `preservation.json` verifies
all earlier saved design files against their existing manifest hashes.

## Connected review behavior

- Navigation carries Affiliate, cycle, selected sectors, review months and
  Units/Value in both directions. Driver selection is derived from those sectors.
  Each page retains its own explicit measures, Channel/Sub-channel context,
  summary periods, grouping, trend choices and Hide/Show state. Navigation does
  not invent S&OP measures or map incompatible Channel taxonomies.
- Demand review now offers the same calendar-year restriction as S&OP. Only
  years covered by Review months appear in its summary options and columns.
  FY/YTD/YTG retain their named business windows; FY is not a partial-year sum.
  Existing H1/H2 choices remain available for the eligible years. Its FY/YTG
  shortcut follows the selected year. Explicit clearing remains empty.
- Demand review adds Affiliate and a separate Units/Value control. Dimension
  changes carry equivalent measures across rather than silently substituting
  Market for Ex-factory. Abbott IMS Value completes the existing unit/value
  pairing using the already retained direct source measure identity.
- Both source-status lines display the same resolved source IDs and ADS
  precedence, IMS/Ex-factory cutoffs and explicitly labelled sample refresh.
  Source versions can be expanded separately on either page. Custom first-page
  file selections remain explicit and are reflected in the shared source status.
- Both pages offer local Hide/Show. Demand review starts with Total in the
  graph, driver rows, the 12M comparison and Matching files collapsed. Other
  comparisons, sector views and source details remain available.
- Hovering/focusing legend items or corresponding rows emphasizes their chart
  lines while preserving selected data. S&OP measure labels are native focusable
  buttons; its existing legend click still turns off that selected measure.
  Share remains on the right axis. A real blank Sub-channel displays as **—**
  with a **No sub-channel** tooltip; source metadata remains null.
- The paired preview persists one combined host-state snapshot containing both
  page states and the active page. Initial rendering does not save state.

## Qualification and limits

`check-connected.cjs` checks navigation in both directions, remembered local
choices, Units/Value equivalents, year restrictions, source precedence/status,
non-filtering line emphasis, keyboard focus, independent Hide/Show and combined
host-state restoration. It verifies responsive light/dark layouts at
1080/1024/736/390/320px and no script errors or warm network requests.

It also compares **672 Demand review observations with Demand R11** and **648
S&OP amount/run-rate/growth observations with S&OP R12**. Calculation-function
hashes and source catalogue/rule bytes are checked in `preservation.json`.
The old prototypes' independent illustrative number models are deliberately
preserved. Sharing source-selection metadata does not establish that those
independent synthetic figures reconcile across the pages.

Before a live migration, both pages still need binding to the same actual
resolved source revisions, numerical reconciliation for identical business
scope/periods, refresh/cache invalidation checks and measured Power BI response
times. Those are unexecuted implementation gates, not passes inferred from this
preview. No application source, company data or workbook was changed.

Build with `python3 build.py`, render `review.fragment.html` with the installed
visualization renderer, then run `check-connected.cjs` using Playwright. The
fragment bundles the existing pinned D3 asset and remains below 1 MB.
