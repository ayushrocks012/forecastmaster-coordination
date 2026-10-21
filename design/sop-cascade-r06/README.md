# Second page R06 — Bridge-based cascading selection

Open [index.html](index.html). This separately saved HTML proposal corrects R05's
independent buttons. It follows Channel → Sub-channel/total → Measure, with
one selection driving the graph and S&OP summary.

Choose Community to enable Total Community, Wholesaler and Northern Ireland.
Community starts with its total selected. Other channels reveal their choices
when enabled. Turning a channel off disables its descendants and removes their
series, retaining choices for a later re-enable. Removing every target disables
that channel's Ex-factory measure controls. Clear all clears the hierarchy.

IMS belongs to **Community with a blank sub-channel**. Selecting Wholesaler
alone does not select Community IMS. Select Total Community alongside Wholesaler
to compare those views. Contracts offers its own seven source members; it does
not receive a fabricated IMS allocation. Source identities include
**Out of Pocket → Retail** and **Sector total**. The Contracts combined target is
an explicitly derived review total, not a fictional blank source sub-channel.

## Source basis and order

After the user's correction, the retained V18 neutral bindings for Core Oral
and Paed SIP were read directly. `bridge-catalog.json` whitelists 44 relevant
Channel/Sub Channel/Section/Measure identities, source positions and the two
descriptor hashes. It contains no workbook values, formulas, products or
customers. The build embeds this catalogue and uses its display order.

The requested executive order is Abbott IMS → Market → PI → Ex-factory for
Community total, then Wholesaler Ex-factory, Northern Ireland Ex-factory and
later source contexts. Community Ex-factory offers **Cur, Pub, IMS minus PI,
ADS**; other applicable contexts offer **Cur, Pub, ADS**. The net row retains
its IMS cutoff even though its source Section is Ex-Factory. Share and the
explicit matched-calendar diagnostics remain supplementary choices. The latter
are not relabelled as the editable IMS Factor input. Within the source context
sequence, Retail precedes Private Order/Internal Account, as in the retained
descriptor. Each context is labelled in the summary.

The current common-layout compiler preserves donor reporting order. Its
`common_layout.reporting_rows`, `_summary_sources` and `v18_bindings.model_bindings`
were inspected read-only. The GitNexus query reported a stale index and authority
drift; it was used for orientation only. Exact current source and retained
neutral identities supplied the bounded evidence. No index was refreshed and
no application checkout files or workbooks were changed.

## Measures and display

**Current plan (Cur)**, **Published plan (Pub)** and **ADS forecast** are distinct
choices. The family measure buttons apply to the selected total/subchannels of
that family. Cur is not a new caption for ADS. These new Cur/Pub observations
are explicitly synthetic fixtures: completed Cur agrees with ADS; future Cur
carries its illustrative prior publication. Pub can differ for the newly
actualised month. Production must bind the separate real source observations;
these sample numbers are not a receiving-data qualification.

Changing the top Units/Value selector changes every relevant caption in the
selector, graph legend, tooltip and summary: Market units/value, Abbott IMS
units/value, PI units/value and Cur/Pub/ADS Selling units or Value (£). Share
remains a percentage, labelled unit share or value share, on the same graph's
right axis. Amounts use the left axis. Summary periods remain beside the table;
monthly columns follow the visible calendars without redefining FY/YTD/YTG.
Parent totals include their children and are never added again as an extra total.

## Validation and preservation

Run `node check-sop.cjs` with Playwright installed (Windows uses Microsoft Edge).
`validation.json` records 12 behavior groups, 102 numerical comparisons and
372 existing ADS/IMS raw/formatted cells matching saved R05 across five
scenarios. It checks cascading enable/disable, remembered choices, fresh
Wholesaler-only selection, Cur/Pub/ADS distinctions, context and measure order,
dynamic Units/Value labels, weighted share, independent calendars, hover/touch,
responsive light/dark layouts and no warm network requests.

All observations are illustrative. Local browser timings are not Power BI
performance evidence. `preservation.json` binds the earlier saved packages and
unchanged original fixtures. The first-page R11 and every earlier second-page
version remain preserved. Power BI implementation, source binding and production
performance remain pending separate approval and qualification.

Edit `page.fragment.html` and `bridge-catalog.json`; `build.py` inserts that
catalogue and R01's preserved MIT-licensed D3 into `review.fragment.html`.
`index.html` is its standalone preview. No live report or model was changed.
