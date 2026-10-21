# S&OP build-up — second page R01

Open [index.html](index.html), or choose **Second page — S&OP build-up** from
the parent design chooser. This is a separate, interactive proposal using
entirely synthetic figures. The approved R11 first page is preserved.

## Try the review

1. Choose a demand cycle and Community in Channel. Select one or more growth
   drivers or sectors. Combined total, By growth driver and By sector change
   how that same scope is presented in both graph and table.
2. Expand **Choose S&OP measures**. Clear all, check IMS Market, then add Abbott
   IMS, PI, Community ADS, Wholesaler or Northern Ireland. Each choice adds its
   line and table row immediately. The subchannels remain indented beneath
   Community; choosing a child alone retains a label-only parent for context.
3. Add Contracts in Channel. Select Total Contracts ADS and any of its seven
   source subchannels, including Homecare and Hospital. Total ADS — all channels
   explicitly includes the eleven publishing leaves for the selected sectors.
4. Switch Display between Selling units and Value in GBP. Share and effective
   uplift remain percentages and use a separate graph, without a mixed-unit axis.
5. Choose FY/YTD/YTG columns or Monthly. Monthly follows the visible From/To
   calendars; those calendars do not redefine the summary-period totals.

Compare lines shows the selected measures including parent totals. Ex-factory
build-up shows non-overlapping parts: a selected child takes precedence over its
parent, and the parent's unselected remainder is labelled **remaining**. A fully
decomposed parent remains a subtotal in the table rather than another stacked
amount. IMS measures, parent totals and child channels must never be blindly
summed together.

## Business meaning retained

Current Smart Demand Manager S&OP and channel-bridge contracts were read to
check the hierarchy and calendars; no source workbook was read or copied.

- Market × share gives Abbott IMS; Abbott IMS minus PI gives net IMS.
- Matched Community ADS minus net IMS is a reconciliation amount; effective
  uplift is that difference divided by net IMS. It is not another demand channel.
- Community Ex-factory ADS = Wholesaler + Northern Ireland.
- Contracts ADS = Homecare + Hospital + Healthcare Logistics + Competitor +
  Nursing Home + Private Order + Internal Account. Contracts stay within the
  relevant source channels; no new cross-channel Contracts bucket is added.
- Total ADS counts those seven leaves, Wholesaler, Northern Ireland, Retail /
  Out of Pocket and Unassigned exactly once.
- IMS rows and matched diagnostics use the IMS calendar. Published channels use
  the Ex-factory calendar. The two Community calendar observations are views of
  the same demand and must not be added together.
- Percentages are ratios of aggregate amounts. Unavailable values remain blank;
  numeric zero remains valid. Source units and GBP are only scaled for display.

The synthetic fixture illustrates these relationships; it is not a replacement
for the bridge engine. A later implementation must bind reviewed ADS using
the approved source precedence and verify the actual workbook calculations,
calendar boundaries, freshness and model feeds. Missing/ambiguous ADS gates and
manual source overrides belong to that binding, not a fake production connection.

## Validation and source

`check-sop.cjs` exercises progressive selection, shared graph/table scope,
parent context, Units/Value, ratio facets, FY/YTD/YTG and Monthly, driver/sector
aggregation, separate cycles, leaf allocation, tooltips and empty states. It
checks 58 reconciliation comparisons and widths 1080, 736, 390 and 320, plus
light/dark rendering. `validation.json` records the result and synthetic warm
render timings. Those timings are not company Power BI performance evidence.

Run with Node.js and Playwright (Windows uses installed Microsoft Edge):

```bash
node check-sop.cjs
```

`page.fragment.html` is the literal editable source. `build.py` inserts the
version-pinned, MIT-licensed D3 7.9.0 from `vendor/` into `review.fragment.html`.
The standalone `index.html` is already prepared for the receiving laptop.
There are no API or network data requests. D3 was obtained from
`https://cdn.jsdelivr.net/npm/d3@7.9.0/dist/d3.min.js`; its licence is retained.

`preservation.json` verifies R07–R11 against their recorded bytes. The prior
GitNexus HTML coverage limitation remains; no complete graph gate is claimed.
All application sources and live Power BI items remain outside this proposal.
Second-page design approval and production qualification are pending.
