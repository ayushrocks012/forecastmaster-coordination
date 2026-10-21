# Second page R07 — Source-only selections and broad filters

Open [index.html](index.html). This separately saved revision supersedes R06
after the user prohibited invented Channels, Sub-channels and Measures and
requested the missing broad filters, including Affiliate. Power BI remains
unchanged. The approved first page R11 and every preceding design are preserved.

## Selection behavior

The graph and table start empty. Choosing a Channel enables its source
Sub-channels but selects nothing else. Choose an actual source Sub-channel
(or the real blank context), then its Measure. Only these explicitly chosen
combinations appear in both results. A channel has no standalone measure or
inferred total. Turning a channel off disables and removes its descendants;
re-enabling it restores the user's valid prior choices. Clear all clears them.
Select all/Select matches is an explicit bulk selection, limited to available
direct source identities.

Community has a real blank Sub-channel plus Wholesaler and Northern Ireland.
IMS measures belong only to that blank context. Wholesaler alone exposes its
own Ex-factory measures, without allocating IMS into it. Contracts has its
seven actual Sub-channels; there is no invented Contracts blank total. Out of
Pocket → Retail, Unassigned → Unassigned and Sector total → blank retain the
source classification. Rows retain the requested Abbott IMS → Market → PI →
Ex-factory order, then the source context order, regardless of click order.

R06's derived Contracts combined rows, effective uplift and matched-calendar
diagnostic have been removed from this revision's selectable catalogue. Only
the 44 direct identities in `bridge-catalog.json` are exposed. This is the
verified executive subset, not a claim that every workbook input or measure
has been modeled. The descriptor hashes and original source row positions
remain in the catalogue; it contains no workbook values, products or customers.

## Shared filters and presentation

- Top: searchable multi-select **Affiliate**, **Demand cycle**, **Section**,
  plus Units/Value and combined/driver/sector presentation.
- Visible From/To calendars: graph months and Monthly summary columns.
- Shared searchable Growth-driver/sector selection with Select all/Clear all.
- Left: Channel, Sub-channel and Measure, without duplicate top selectors.
- Summary: independent FY/YTD/YTG period selection or Monthly columns.

Only the confirmed United Kingdom sample Affiliate is offered; other countries
have not been invented. Clearing Affiliate clears both results. Production
option lists must come from the actual data. Source Section gates the available
measures without changing their IMS/EF cutoff basis. Units/Value changes the
selector, legend, tooltip and summary labels, including unit/value share on the
same graph's right percentage axis. No channel or measure is preselected.

## Evidence and limits

`validation.json` records 11 integration groups, 66 reconciliation comparisons
and 264 retained measure/period/dimension values matching R06's synthetic
fixtures. It checks empty defaults, explicit selection gates, source-only
identity coverage, cascading controls, Affiliate and Section, dynamic labels,
bridge ordering, independent dates/periods, hover, responsive light/dark
layouts, and no warm network requests or script errors.

All numeric observations remain synthetic design data. Retained source metadata
does not establish live data binding, full source-measure coverage, deployment
acceptance or Power BI speed. The bounded source inspection and stale GitNexus
limitations described in R06 still apply. No application checkout, workbook,
Fabric item or report was changed.

Edit `page.fragment.html` and `bridge-catalog.json`, run `python3 build.py`, then
render the fragment with the installed visualization wrapper. `check-sop.cjs`
runs in Playwright (Microsoft Edge on Windows). `preservation.json` verifies
all preceding saved design files against their previous manifest hashes.
